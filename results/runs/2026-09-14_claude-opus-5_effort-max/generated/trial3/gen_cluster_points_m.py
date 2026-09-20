"""Single-linkage clustering of WGS84 longitude/latitude points by ground distance.

``cluster_points_m`` groups points so that any two points lying within
``max_distance_m`` metres of one another end up in the same cluster, transitively
(a chain of close neighbours keeps a cluster together, and an isolated point
forms a cluster of its own).

Distances are true WGS84 geodesics, so the result is correct near the poles and
across the antimeridian, where a naive planar treatment of degrees would fail.

A KD-tree over geocentric (ECEF) coordinates is used only to *propose* candidate
pairs; every candidate is then confirmed with an exact geodesic distance before
it is merged.  The pre-filter cannot drop an edge: the straight chord between two
surface points is never longer than the geodesic joining them, so searching a
chord radius of ``max_distance_m`` always returns a superset of the true
within-threshold pairs.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

import numpy as np
from pyproj import Geod
from sklearn.neighbors import KDTree

__all__ = ["cluster_points_m"]

# WGS84 defining parameters.
_A = 6378137.0  # semi-major axis (m)
_F = 1.0 / 298.257223563  # flattening
_E2 = _F * (2.0 - _F)  # first eccentricity squared

# Points queried against the tree per batch, and candidate pairs verified per
# batch.  These only bound peak memory; they do not affect the result.
_QUERY_BLOCK = 4096
_PAIR_BLOCK = 262_144


class _DisjointSet:
    """Union-find with union-by-size and path halving."""

    __slots__ = ("_parent", "_size")

    def __init__(self, n: int) -> None:
        self._parent = list(range(n))
        self._size = [1] * n

    def find(self, x: int) -> int:
        parent = self._parent
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self._size[ra] < self._size[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        self._size[ra] += self._size[rb]


def _as_lon_lat(points: Iterable[Sequence[float]]) -> Tuple[np.ndarray, np.ndarray]:
    """Validate the input and split it into contiguous lon/lat arrays."""
    if not isinstance(points, np.ndarray):
        points = list(points)
    arr = np.asarray(points, dtype=float)
    if arr.size == 0:
        return np.empty(0, dtype=float), np.empty(0, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("points must be a sequence of (lon, lat) pairs")
    if not np.isfinite(arr).all():
        raise ValueError("points must contain finite coordinates")
    lon = np.ascontiguousarray(arr[:, 0])
    lat = np.ascontiguousarray(arr[:, 1])
    if np.any(np.abs(lat) > 90.0):
        raise ValueError("latitudes must lie within [-90, 90]")
    return lon, lat


def _ecef(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Convert lon/lat degrees to geocentric XYZ metres on the WGS84 ellipsoid."""
    lam = np.radians(lon)
    phi = np.radians(lat)
    sin_phi = np.sin(phi)
    cos_phi = np.cos(phi)
    prime_vertical = _A / np.sqrt(1.0 - _E2 * sin_phi * sin_phi)
    xyz = np.empty((lon.size, 3), dtype=float)
    xyz[:, 0] = prime_vertical * cos_phi * np.cos(lam)
    xyz[:, 1] = prime_vertical * cos_phi * np.sin(lam)
    xyz[:, 2] = prime_vertical * (1.0 - _E2) * sin_phi
    return xyz


def _merge_close(
    dsu: _DisjointSet,
    geod: Geod,
    lon: np.ndarray,
    lat: np.ndarray,
    left: List[int],
    right: List[int],
    max_distance_m: float,
) -> None:
    """Geodesically verify buffered candidate pairs and union those in range."""
    if not left:
        return
    a = np.asarray(left, dtype=np.intp)
    b = np.asarray(right, dtype=np.intp)
    for start in range(0, a.size, _PAIR_BLOCK):
        chunk_a = a[start : start + _PAIR_BLOCK]
        chunk_b = b[start : start + _PAIR_BLOCK]
        _, _, dist = geod.inv(
            lon[chunk_a], lat[chunk_a], lon[chunk_b], lat[chunk_b]
        )
        within = np.asarray(dist) <= max_distance_m
        for i, j in zip(chunk_a[within].tolist(), chunk_b[within].tolist()):
            dsu.union(i, j)
    left.clear()
    right.clear()


def cluster_points_m(
    points: Iterable[Sequence[float]], max_distance_m: float
) -> List[int]:
    """Single-linkage cluster WGS84 points by geodesic distance.

    Args:
        points: Sequence of ``(lon, lat)`` pairs in degrees (WGS84).
        max_distance_m: Linkage threshold in metres.  Two points are linked when
            the geodesic distance between them is ``<= max_distance_m``; clusters
            are the connected components of those links.

    Returns:
        A list of integer cluster labels, one per input point, numbered
        ``0, 1, 2, ...`` in order of first appearance.

    Raises:
        ValueError: If the coordinates are malformed or non-finite, a latitude
            falls outside ``[-90, 90]``, or ``max_distance_m`` is negative or NaN.

    Example:
        >>> cluster_points_m([(0.0, 0.0), (0.0005, 0.0), (10.0, 10.0)], 100.0)
        [0, 0, 1]
    """
    lon, lat = _as_lon_lat(points)
    n = int(lon.size)
    if n == 0:
        return []

    threshold = float(max_distance_m)
    if math.isnan(threshold) or threshold < 0.0:
        raise ValueError("max_distance_m must be a non-negative number of metres")
    if n == 1:
        return [0]

    dsu = _DisjointSet(n)

    # Chord <= geodesic, so a chord-radius search of `threshold` cannot miss a
    # pair.  The slack absorbs rounding in the ECEF conversion and any
    # strictness in the tree's radius test; false candidates are harmless
    # because each one is checked against the real geodesic below.
    radius = threshold * (1.0 + 1e-12) + 1e-6
    xyz = _ecef(lon, lat)
    tree = KDTree(xyz)
    geod = Geod(ellps="WGS84")

    left: List[int] = []
    right: List[int] = []
    for start in range(0, n, _QUERY_BLOCK):
        stop = min(start + _QUERY_BLOCK, n)
        neighbourhoods = tree.query_radius(xyz[start:stop], r=radius)
        for offset, neighbours in enumerate(neighbourhoods):
            i = start + offset
            for j in neighbours.tolist():
                # Each pair is considered once, and pairs that are already
                # connected need no distance at all.
                if j <= i or dsu.find(i) == dsu.find(j):
                    continue
                left.append(i)
                right.append(j)
            if len(left) >= _PAIR_BLOCK:
                _merge_close(dsu, geod, lon, lat, left, right, threshold)
    _merge_close(dsu, geod, lon, lat, left, right, threshold)

    labels = [0] * n
    seen: dict = {}
    for i in range(n):
        root = dsu.find(i)
        label = seen.get(root)
        if label is None:
            label = len(seen)
            seen[root] = label
        labels[i] = label
    return labels