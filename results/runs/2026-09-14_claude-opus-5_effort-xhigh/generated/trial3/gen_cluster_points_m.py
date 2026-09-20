"""Single-linkage clustering of WGS84 lon/lat points by geodesic distance.

Two points fall in the same cluster when the geodesic distance between them on
the WGS84 ellipsoid is at most ``max_distance_m``, either directly or through a
chain of intermediate points.

Candidate pairs are found with a KD-tree over geocentric (ECEF) coordinates.
The straight-line chord between two surface points is never longer than the
geodesic joining them, so a chord-radius query returns a strict superset of the
true neighbour pairs; every candidate is then confirmed with an exact geodesic
inverse solution.  This keeps the result identical to a brute-force O(n^2)
comparison while doing far fewer of them, and it is correct across the
antimeridian and at the poles.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterator, List, Sequence, Tuple

import numpy as np
from pyproj import Geod
from sklearn.neighbors import KDTree

__all__ = ["cluster_points_m"]

# WGS84 defining parameters.
_A = 6378137.0
_F = 1.0 / 298.257223563
_E2 = _F * (2.0 - _F)

# Upper bound on how many candidate pairs go to Geod.inv in one call.
_PAIR_CHUNK = 1 << 20


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """The WGS84 geodesic solver, built on first use so import stays inert."""
    return Geod(ellps="WGS84")


class _DisjointSet:
    """Union-find with path compression and union by size."""

    __slots__ = ("_parent", "_size")

    def __init__(self, n: int) -> None:
        self._parent = list(range(n))
        self._size = [1] * n

    def find(self, x: int) -> int:
        parent = self._parent
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self._size[ra] < self._size[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        self._size[ra] += self._size[rb]


def _as_coords(points) -> np.ndarray:
    arr = np.asarray(points, dtype=float)
    if arr.size == 0:
        return np.empty((0, 2), dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("points must be a sequence of (lon, lat) pairs")
    if not np.isfinite(arr).all():
        raise ValueError("points must contain finite lon/lat values")
    if np.any(np.abs(arr[:, 1]) > 90.0):
        raise ValueError("latitudes must lie within [-90, 90]")
    return arr


def _ecef(coords: np.ndarray) -> np.ndarray:
    """Geocentric XYZ in metres for lon/lat degrees on the WGS84 ellipsoid."""
    lon = np.radians(coords[:, 0])
    lat = np.radians(coords[:, 1])
    sin_lat, cos_lat = np.sin(lat), np.cos(lat)
    prime_vertical = _A / np.sqrt(1.0 - _E2 * sin_lat * sin_lat)
    return np.column_stack(
        (
            prime_vertical * cos_lat * np.cos(lon),
            prime_vertical * cos_lat * np.sin(lon),
            prime_vertical * (1.0 - _E2) * sin_lat,
        )
    )


def _linked_pairs(coords: np.ndarray, threshold: float) -> Iterator[Tuple[int, int]]:
    """Yield index pairs whose geodesic separation is within ``threshold``."""
    tree = KDTree(_ecef(coords))
    neighbours = tree.query_radius(_ecef(coords), r=threshold)

    counts = [len(block) for block in neighbours]
    left = np.repeat(np.arange(len(coords), dtype=np.intp), counts)
    right = np.concatenate(neighbours).astype(np.intp, copy=False)

    # Keep each unordered pair once; this also drops the self-matches.
    keep = right > left
    left, right = left[keep], right[keep]

    geod = _geod()
    for start in range(0, left.size, _PAIR_CHUNK):
        a = left[start : start + _PAIR_CHUNK]
        b = right[start : start + _PAIR_CHUNK]
        _, _, dist = geod.inv(
            coords[a, 0], coords[a, 1], coords[b, 0], coords[b, 1]
        )
        within = np.asarray(dist) <= threshold
        yield from zip(a[within].tolist(), b[within].tolist())


def cluster_points_m(
    points: Sequence[Tuple[float, float]], max_distance_m: float
) -> List[int]:
    """Single-linkage cluster ``points`` at a ``max_distance_m`` metre threshold.

    Args:
        points: Sequence of ``(lon, lat)`` pairs in decimal degrees (WGS84).
        max_distance_m: Linkage threshold in metres; must be finite and >= 0.

    Returns:
        One integer label per input point, in input order, numbered 0, 1, 2, ...
        in order of first appearance.  An isolated point forms its own cluster.
    """
    coords = _as_coords(points)
    n = len(coords)
    if n == 0:
        return []

    threshold = float(max_distance_m)
    if not np.isfinite(threshold) or threshold < 0.0:
        raise ValueError("max_distance_m must be a finite, non-negative distance in metres")

    components = _DisjointSet(n)
    if n > 1:
        for i, j in _linked_pairs(coords, threshold):
            components.union(i, j)

    labels: List[int] = []
    label_of_root: dict = {}
    for i in range(n):
        root = components.find(i)
        label = label_of_root.get(root)
        if label is None:
            label = len(label_of_root)
            label_of_root[root] = label
        labels.append(label)
    return labels