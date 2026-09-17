"""Single-linkage clustering of WGS84 points by geodesic distance.

Two points are linked when their geodesic (WGS84 ellipsoid) distance is at
most ``max_distance_m`` meters; clusters are the connected components of
that link graph. Cluster labels are assigned 0, 1, 2, ... in order of first
appearance in the input.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

try:  # pyproj gives exact ellipsoidal distances; fall back to haversine if absent.
    from pyproj import Geod as _Geod
except ImportError:  # pragma: no cover - exercised only without pyproj
    _Geod = None

_EARTH_RADIUS_M = 6_371_008.8  # mean Earth radius, used only by the fallback


def _pairwise_distances_m(points: Sequence[Tuple[float, float]]) -> List[List[float]]:
    """Return a full n x n matrix of geodesic distances in meters."""
    n = len(points)
    dist = [[0.0] * n for _ in range(n)]
    if n < 2:
        return dist

    lons = [float(p[0]) for p in points]
    lats = [float(p[1]) for p in points]

    if _Geod is not None:
        geod = _Geod(ellps="WGS84")
        for i in range(n - 1):
            m = n - i - 1
            _, _, d = geod.inv(
                [lons[i]] * m, [lats[i]] * m, lons[i + 1 :], lats[i + 1 :]
            )
            for k, j in enumerate(range(i + 1, n)):
                dist[i][j] = dist[j][i] = float(d[k])
        return dist

    # Haversine fallback (spherical approximation).
    rlons = [math.radians(x) for x in lons]
    rlats = [math.radians(y) for y in lats]
    for i in range(n - 1):
        for j in range(i + 1, n):
            dlat = rlats[j] - rlats[i]
            dlon = rlons[j] - rlons[i]
            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(rlats[i]) * math.cos(rlats[j]) * math.sin(dlon / 2) ** 2
            )
            d = 2.0 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))
            dist[i][j] = dist[j][i] = d
    return dist


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:  # path compression
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def cluster_points_m(
    points: Sequence[Tuple[float, float]], max_distance_m: float
) -> List[int]:
    """Cluster ``(lon, lat)`` WGS84 points by single linkage.

    Parameters
    ----------
    points:
        Sequence of ``(lon, lat)`` tuples in decimal degrees (WGS84).
    max_distance_m:
        Non-negative distance threshold in meters. Two points are directly
        linked when their geodesic distance is ``<= max_distance_m``.

    Returns
    -------
    list[int]
        One integer label per input point. Labels are 0, 1, 2, ... in order
        of the first point of each cluster in the input. Isolated points form
        their own cluster.
    """
    if max_distance_m < 0 or math.isnan(max_distance_m):
        raise ValueError("max_distance_m must be a non-negative number")

    pts = list(points)
    n = len(pts)
    if n == 0:
        return []

    for p in pts:
        lon, lat = float(p[0]), float(p[1])
        if not (-180.0 <= lon <= 180.0) or not (-90.0 <= lat <= 90.0):
            raise ValueError(f"point {p!r} is outside valid WGS84 lon/lat range")

    dist = _pairwise_distances_m(pts)
    uf = _UnionFind(n)
    for i in range(n - 1):
        row = dist[i]
        for j in range(i + 1, n):
            if row[j] <= max_distance_m:
                uf.union(i, j)

    labels: List[int] = []
    root_to_label = {}
    for i in range(n):
        root = uf.find(i)
        if root not in root_to_label:
            root_to_label[root] = len(root_to_label)
        labels.append(root_to_label[root])
    return labels


__all__ = ["cluster_points_m"]