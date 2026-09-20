"""Single-linkage clustering of WGS84 longitude/latitude points.

``cluster_points_m`` groups points so that any two points within a given
geodesic distance (in metres) share a cluster, either directly or through a
chain of intermediate points -- the clusters are the connected components of
the graph whose edges join points closer than the threshold.

Distances are true WGS84 geodesic distances (via pyproj/GeographicLib), so the
result is correct across the antimeridian and at the poles.  Candidate pairs
come from a KD-tree over earth-centred, earth-fixed (ECEF) coordinates, which
keeps the neighbour search out of the O(n^2) regime.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

import numpy as np
from pyproj import Geod
from sklearn.neighbors import KDTree

__all__ = ["cluster_points_m"]

# WGS84 defining parameters.
_A = 6378137.0                    # semi-major axis (m)
_F = 1.0 / 298.257223563          # flattening
_B = _A * (1.0 - _F)              # semi-minor axis (m)
_E2 = _F * (2.0 - _F)             # first eccentricity squared

# Smallest radius of normal curvature anywhere on the ellipsoid: the meridional
# radius at the equator, a(1 - e^2) = b^2 / a.  See _certain_chord().
_RHO_MIN = _B * _B / _A

# No geodesic on the ellipsoid is longer than half the equatorial circumference
# (the true maximum, a polar half-meridian, is shorter still).
_MAX_GEODESIC_M = math.pi * _A

# Query points per neighbour-search block, to bound peak memory.
_BLOCK = 4096


def cluster_points_m(
    points: Sequence[Tuple[float, float]],
    max_distance_m: float,
) -> List[int]:
    """Cluster WGS84 ``(lon, lat)`` points by single linkage.

    Parameters
    ----------
    points:
        Sequence of ``(longitude, latitude)`` pairs in degrees (WGS84).
    max_distance_m:
        Linkage threshold in metres.  Two points are linked when the geodesic
        distance between them is at most this value.

    Returns
    -------
    list of int
        One cluster label per input point, numbered ``0, 1, 2, ...`` in order
        of first appearance.  An isolated point forms its own cluster.
    """
    threshold = float(max_distance_m)
    if not math.isfinite(threshold) or threshold < 0.0:
        raise ValueError("max_distance_m must be a finite, non-negative number of metres")

    lon, lat = _as_lon_lat(points)
    n = lon.size
    if n == 0:
        return []
    if n == 1:
        return [0]
    if threshold >= _MAX_GEODESIC_M:
        # Longer than any geodesic on the ellipsoid: everything links up.
        return [0] * n

    xyz = _to_ecef(lon, lat)
    tree = KDTree(xyz)
    geod = Geod(ellps="WGS84")
    components = _UnionFind(n)

    # A chord is never longer than the geodesic joining its endpoints, so a
    # chord-radius search of `threshold` returns a superset of the true edges
    # (the small epsilon just absorbs round-off at the boundary).
    search_radius = threshold * (1.0 + 1e-9) + 1e-6
    # Chords at or below this length provably span no more than `threshold`
    # metres, so those pairs can be linked without measuring them exactly.
    certain_radius = _certain_chord(threshold)

    for start in range(0, n, _BLOCK):
        stop = min(start + _BLOCK, n)
        neighbours = tree.query_radius(xyz[start:stop], r=search_radius)

        counts = np.array([nb.size for nb in neighbours], dtype=np.intp)
        src = np.repeat(np.arange(start, stop, dtype=np.intp), counts)
        dst = np.concatenate(neighbours).astype(np.intp, copy=False)

        upper = src < dst  # keep each pair once, and drop self-matches
        src, dst = src[upper], dst[upper]
        if src.size == 0:
            continue

        chord = np.linalg.norm(xyz[src] - xyz[dst], axis=1)
        certain = chord <= certain_radius
        _union_all(components, src[certain], dst[certain])

        src, dst = src[~certain], dst[~certain]
        if src.size:
            # Only the thin annulus of ambiguous pairs needs exact geodesics.
            *_, distance = geod.inv(lon[src], lat[src], lon[dst], lat[dst])
            within = np.asarray(distance) <= threshold
            _union_all(components, src[within], dst[within])

    return _labels_in_first_appearance_order(components, n)


def _as_lon_lat(points: Sequence[Tuple[float, float]]) -> Tuple[np.ndarray, np.ndarray]:
    """Validate the input and split it into contiguous lon/lat arrays."""
    try:
        array = np.asarray(points, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("points must be a sequence of (lon, lat) pairs") from exc

    if array.size == 0:
        empty = np.empty(0, dtype=float)
        return empty, empty
    if array.ndim != 2 or array.shape[1] != 2:
        raise ValueError("points must be a sequence of (lon, lat) pairs")
    if not np.isfinite(array).all():
        raise ValueError("points must contain only finite coordinates")

    lon = np.ascontiguousarray(array[:, 0])
    lat = np.ascontiguousarray(array[:, 1])
    if np.abs(lat).max() > 90.0:
        raise ValueError("latitudes must lie within [-90, 90] degrees")
    return lon, lat


def _to_ecef(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Project lon/lat degrees onto the WGS84 ellipsoid surface in ECEF metres."""
    lam = np.radians(lon)
    phi = np.radians(lat)
    sin_phi = np.sin(phi)
    cos_phi = np.cos(phi)
    prime_vertical = _A / np.sqrt(1.0 - _E2 * sin_phi * sin_phi)
    return np.column_stack(
        (
            prime_vertical * cos_phi * np.cos(lam),
            prime_vertical * cos_phi * np.sin(lam),
            prime_vertical * (1.0 - _E2) * sin_phi,
        )
    )


def _certain_chord(threshold: float) -> float:
    """Longest chord that cannot possibly span more than ``threshold`` metres.

    A geodesic on the ellipsoid is a space curve whose curvature is the surface's
    normal curvature, so it never bends more tightly than a circle of radius
    ``_RHO_MIN``.  Schur's comparison theorem then bounds the chord of an arc of
    length ``threshold`` from below by that circle's chord; anything shorter
    belongs to a shorter geodesic.  Returns a negative value when ``threshold``
    falls outside the theorem's range, which simply sends every candidate pair
    to the exact geodesic test.
    """
    if threshold >= math.pi * _RHO_MIN:
        return -1.0
    return 2.0 * _RHO_MIN * math.sin(threshold / (2.0 * _RHO_MIN))


class _UnionFind:
    """Disjoint-set forest with path compression and union by rank."""

    __slots__ = ("_parent", "_rank")

    def __init__(self, size: int) -> None:
        self._parent = list(range(size))
        self._rank = [0] * size

    def find(self, item: int) -> int:
        parent = self._parent
        root = item
        while parent[root] != root:
            root = parent[root]
        while parent[item] != root:
            parent[item], item = root, parent[item]
        return root

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        rank = self._rank
        if rank[left_root] < rank[right_root]:
            left_root, right_root = right_root, left_root
        self._parent[right_root] = left_root
        if rank[left_root] == rank[right_root]:
            rank[left_root] += 1


def _union_all(components: _UnionFind, src: np.ndarray, dst: np.ndarray) -> None:
    for left, right in zip(src.tolist(), dst.tolist()):
        components.union(left, right)


def _labels_in_first_appearance_order(components: _UnionFind, n: int) -> List[int]:
    labels: List[int] = []
    seen: Dict[int, int] = {}
    for index in range(n):
        root = components.find(index)
        labels.append(seen.setdefault(root, len(seen)))
    return labels