"""Single-linkage clustering of WGS84 lon/lat points by a metric distance threshold.

Points are linked when the geodesic (WGS84 ellipsoid) distance between them is at
most ``max_distance_m``; clusters are the connected components of that link graph.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

import numpy as np
from pyproj import Geod
from sklearn.neighbors import BallTree

__all__ = ["cluster_points_m"]

# Mean radius used only to turn a metric threshold into a spherical search radius.
_MEAN_RADIUS_M = 6371008.8

# The sphere/ellipsoid disagreement is well under 0.5%; inflate the candidate
# search radius generously, then confirm each candidate pair geodesically.
_SEARCH_SLACK = 1.01


class _UnionFind:
    def __init__(self, n: int) -> None:
        self._parent = list(range(n))
        self._rank = [0] * n

    def find(self, i: int) -> int:
        parent = self._parent
        root = i
        while parent[root] != root:
            root = parent[root]
        while parent[i] != root:
            parent[i], i = root, parent[i]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1


def _as_array(points: Iterable[Sequence[float]]) -> np.ndarray:
    arr = np.asarray(list(points), dtype=float)
    if arr.size == 0:
        return arr.reshape(0, 2)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("points must be an iterable of (lon, lat) pairs")
    if not np.isfinite(arr).all():
        raise ValueError("points must contain finite lon/lat values")
    return arr


def cluster_points_m(
    points: Iterable[Tuple[float, float]], max_distance_m: float
) -> List[int]:
    """Single-linkage cluster ``points`` at a threshold of ``max_distance_m`` meters.

    Args:
        points: iterable of ``(lon, lat)`` tuples in WGS84 degrees.
        max_distance_m: link threshold in meters; must be non-negative.

    Returns:
        One integer label per input point, numbered from 0 in order of first
        appearance. Isolated points get their own label.
    """
    if not math.isfinite(max_distance_m) or max_distance_m < 0:
        raise ValueError("max_distance_m must be a non-negative finite number")

    coords = _as_array(points)
    n = coords.shape[0]
    if n == 0:
        return []
    if n == 1:
        return [0]

    uf = _UnionFind(n)

    # BallTree's haversine metric wants (lat, lon) in radians.
    latlon_rad = np.radians(coords[:, ::-1])
    tree = BallTree(latlon_rad, metric="haversine")
    search_rad = (max_distance_m * _SEARCH_SLACK) / _MEAN_RADIUS_M

    neighbors = tree.query_radius(latlon_rad, r=search_rad)

    geod = Geod(ellps="WGS84")
    left, right = [], []
    for i, idxs in enumerate(neighbors):
        for j in idxs:
            if j > i:
                left.append(i)
                right.append(int(j))

    if left:
        li = np.asarray(left, dtype=int)
        ri = np.asarray(right, dtype=int)
        _, _, dist = geod.inv(
            coords[li, 0], coords[li, 1], coords[ri, 0], coords[ri, 1]
        )
        dist = np.asarray(dist, dtype=float)
        # Guard the inclusive boundary against floating-point noise.
        tol = max(1e-9, max_distance_m * 1e-12)
        for a, b in zip(li[dist <= max_distance_m + tol], ri[dist <= max_distance_m + tol]):
            uf.union(int(a), int(b))

    labels: List[int] = []
    seen: dict = {}
    for i in range(n):
        root = uf.find(i)
        if root not in seen:
            seen[root] = len(seen)
        labels.append(seen[root])
    return labels