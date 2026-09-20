"""Single-linkage clustering of WGS84 lon/lat points by geodesic distance.

Uses a haversine ball tree to find candidate neighbours cheaply, then confirms
each candidate pair with an exact WGS84 geodesic distance before linking.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

import numpy as np
from pyproj import Geod
from sklearn.neighbors import BallTree

# Smallest earth radius (polar, WGS84). Dividing by the *smallest* radius turns a
# metre threshold into an angle that is never too small, so the haversine query
# stays a conservative superset of the true geodesic neighbours.
_MIN_EARTH_RADIUS_M = 6_356_752.314245

# Slack on the candidate radius: 1% covers the haversine/geodesic discrepancy,
# the extra metre covers round-off at tiny thresholds.
_RADIUS_SCALE = 1.01
_RADIUS_PAD_M = 1.0


class _UnionFind:
    def __init__(self, n: int) -> None:
        self._parent = list(range(n))
        self._rank = [0] * n

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
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1


def cluster_points_m(
    points: Sequence[Tuple[float, float]] | Iterable[Tuple[float, float]],
    max_distance_m: float,
) -> List[int]:
    """Single-linkage cluster ``points`` at a ``max_distance_m`` metre threshold.

    Args:
        points: sequence of ``(lon, lat)`` tuples in WGS84 degrees.
        max_distance_m: linkage threshold in metres; two points are linked when
            the geodesic distance between them is <= this value.

    Returns:
        One integer label per input point, numbered 0, 1, 2, ... in order of
        first appearance. An isolated point forms its own cluster.
    """
    pts = list(points)
    n = len(pts)
    if n == 0:
        return []
    if max_distance_m < 0:
        raise ValueError("max_distance_m must be non-negative")

    coords = np.asarray(pts, dtype=float)
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError("points must be a sequence of (lon, lat) pairs")
    if not np.isfinite(coords).all():
        raise ValueError("points must contain finite lon/lat values")

    uf = _UnionFind(n)

    if n > 1:
        lon = coords[:, 0]
        lat = coords[:, 1]

        # BallTree's haversine metric wants (lat, lon) in radians.
        radians = np.radians(np.column_stack((lat, lon)))
        tree = BallTree(radians, metric="haversine")
        angular_radius = (
            max_distance_m * _RADIUS_SCALE + _RADIUS_PAD_M
        ) / _MIN_EARTH_RADIUS_M
        # Beyond half the globe every point is a candidate anyway.
        angular_radius = min(angular_radius, math.pi)
        candidates = tree.query_radius(radians, r=angular_radius)

        geod = Geod(ellps="WGS84")
        left: List[int] = []
        right: List[int] = []
        for i, neighbours in enumerate(candidates):
            for j in neighbours:
                if j > i:  # each unordered pair once
                    left.append(i)
                    right.append(int(j))

        if left:
            li = np.asarray(left, dtype=np.intp)
            ri = np.asarray(right, dtype=np.intp)
            _, _, dist = geod.inv(lon[li], lat[li], lon[ri], lat[ri])
            for a, b in zip(li[dist <= max_distance_m], ri[dist <= max_distance_m]):
                uf.union(int(a), int(b))

    labels: List[int] = []
    seen: dict[int, int] = {}
    for i in range(n):
        root = uf.find(i)
        label = seen.get(root)
        if label is None:
            label = len(seen)
            seen[root] = label
        labels.append(label)
    return labels