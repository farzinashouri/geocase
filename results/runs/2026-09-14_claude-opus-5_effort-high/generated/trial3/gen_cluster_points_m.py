"""Single-linkage spatial clustering of WGS84 ``(lon, lat)`` points.

Two points join the same cluster when the geodesic (WGS84 ellipsoidal)
distance between them is at most ``max_distance_m``; clusters are the
connected components of that relation, so membership also propagates
through chains of intermediate points.

Importing this module has no side effects: the ``pyproj.Geod`` instance is
created lazily on first use, and the optional scikit-learn spatial index is
imported defensively (a pure-numpy fallback is used when it is absent).
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import List, Sequence, Tuple

import numpy as np
from pyproj import Geod

try:  # optional: only used to prune candidate pairs
    from sklearn.neighbors import BallTree
except ImportError:  # pragma: no cover - exercised only without scikit-learn
    BallTree = None

__all__ = ["cluster_points_m"]

# Semi-minor axis of WGS84. Using the smallest ellipsoid radius makes the
# spherical (haversine) prefilter distance an under-estimate of the true
# geodesic distance, so the candidate search never misses a real neighbour.
_SPHERE_RADIUS_M = 6356752.314245

# Extra slack on the prefilter radius, well above the ~0.34% spread between
# spherical and ellipsoidal distances.
_SEARCH_SCALE = 1.01
_SEARCH_PAD_M = 1.0

# Number of query points handled per BallTree / brute-force batch.
_CHUNK = 1024


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """Return the shared WGS84 geodesic calculator."""
    return Geod(ellps="WGS84")


def _as_coords(points: Sequence[Tuple[float, float]]) -> Tuple[np.ndarray, np.ndarray]:
    """Validate the input and split it into longitude and latitude arrays."""
    arr = np.asarray(points, dtype=float)
    if arr.size == 0:
        return np.empty(0, dtype=float), np.empty(0, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("points must be a sequence of (lon, lat) pairs")
    if not np.isfinite(arr).all():
        raise ValueError("points must contain finite lon/lat values")

    lon = arr[:, 0]
    lat = arr[:, 1]
    if np.any(lat < -90.0) or np.any(lat > 90.0):
        raise ValueError("latitudes must lie within [-90, 90]")
    return lon, lat


class _UnionFind:
    """Disjoint-set forest with path halving and union by size."""

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


def _candidate_neighbors(lon: np.ndarray, lat: np.ndarray, search_m: float):
    """Yield ``(i, candidates)`` pairs with ``candidates`` holding indices > i.

    The candidate set is a superset of the true geodesic neighbours of ``i``;
    exact distances are checked by the caller.
    """
    n = lon.size

    if BallTree is not None:
        radians = np.column_stack((np.radians(lat), np.radians(lon)))
        tree = BallTree(radians, metric="haversine")
        # Clamp to pi: a larger angular radius would simply cover the sphere.
        radius = min(search_m / _SPHERE_RADIUS_M, math.pi)
        for start in range(0, n, _CHUNK):
            stop = min(start + _CHUNK, n)
            for offset, found in enumerate(
                tree.query_radius(radians[start:stop], r=radius)
            ):
                i = start + offset
                yield i, found[found > i]
        return

    # Fallback: every later point is a candidate, checked in batches.
    for i in range(n - 1):
        yield i, np.arange(i + 1, n)


def cluster_points_m(
    points: Sequence[Tuple[float, float]], max_distance_m: float
) -> List[int]:
    """Cluster WGS84 ``(lon, lat)`` points by single linkage.

    Args:
        points: Sequence of ``(lon, lat)`` tuples in decimal degrees.
        max_distance_m: Linkage threshold in meters. Points closer than or
            exactly at this geodesic distance are linked; a point with no
            link forms its own cluster.

    Returns:
        A list of integer cluster labels, one per input point, numbered
        ``0, 1, 2, ...`` in order of first appearance.
    """
    threshold = float(max_distance_m)
    if not math.isfinite(threshold):
        raise ValueError("max_distance_m must be a finite number")

    lon, lat = _as_coords(points)
    n = lon.size
    if n == 0:
        return []

    uf = _UnionFind(n)

    if threshold >= 0.0:
        geod = _geod()
        search_m = threshold * _SEARCH_SCALE + _SEARCH_PAD_M
        for i, candidates in _candidate_neighbors(lon, lat, search_m):
            if candidates.size == 0:
                continue
            for start in range(0, candidates.size, _CHUNK):
                block = candidates[start : start + _CHUNK]
                _, _, dist = geod.inv(
                    np.full(block.size, lon[i]),
                    np.full(block.size, lat[i]),
                    lon[block],
                    lat[block],
                )
                for j in block[np.asarray(dist) <= threshold]:
                    uf.union(i, int(j))

    labels: List[int] = []
    seen: dict = {}
    for i in range(n):
        root = uf.find(i)
        label = seen.get(root)
        if label is None:
            label = len(seen)
            seen[root] = label
        labels.append(label)
    return labels