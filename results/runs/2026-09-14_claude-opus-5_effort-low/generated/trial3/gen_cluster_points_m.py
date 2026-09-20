"""Single-linkage clustering of WGS84 lon/lat points by metric distance.

Two points join the same cluster when the geodesic distance between them is at
most ``max_distance_m``, directly or through a chain of intermediate points.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import numpy as np
from pyproj import Geod
from sklearn.neighbors import BallTree

# Mean Earth radius (IUGG) used for the spherical candidate search.
_EARTH_RADIUS_M = 6371008.8

# The spherical search radius is inflated before the exact geodesic check so
# that no true neighbour pair is missed: sphere and WGS84 ellipsoid distances
# differ by well under 1% for the same pair.
_SEARCH_MARGIN = 1.01
_SEARCH_PAD_M = 1.0


class _UnionFind:
    def __init__(self, n: int) -> None:
        self._parent = list(range(n))
        self._rank = [0] * n

    def find(self, a: int) -> int:
        parent = self._parent
        root = a
        while parent[root] != root:
            root = parent[root]
        while parent[a] != root:
            parent[a], a = root, parent[a]
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


def cluster_points_m(
    points: Sequence[Tuple[float, float]] | Iterable[Tuple[float, float]],
    max_distance_m: float,
) -> List[int]:
    """Label ``points`` by single-linkage clusters at a metric threshold.

    Args:
        points: iterable of ``(lon, lat)`` tuples in WGS84 decimal degrees.
        max_distance_m: linkage threshold in meters (non-negative).

    Returns:
        A list of integer labels, one per input point, numbered ``0, 1, 2, ...``
        in order of first appearance.
    """
    coords = np.asarray(list(points), dtype=float)
    if coords.size == 0:
        return []
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError("points must be an iterable of (lon, lat) pairs")
    if not np.isfinite(coords).all():
        raise ValueError("points must contain finite coordinates")

    max_distance_m = float(max_distance_m)
    if not np.isfinite(max_distance_m) or max_distance_m < 0:
        raise ValueError("max_distance_m must be a non-negative finite number")

    n = coords.shape[0]
    uf = _UnionFind(n)

    if n > 1 and max_distance_m > 0:
        lon = coords[:, 0]
        lat = coords[:, 1]
        # BallTree's haversine metric expects (lat, lon) in radians.
        radians = np.radians(np.column_stack((lat, lon)))
        tree = BallTree(radians, metric="haversine")

        search_m = max_distance_m * _SEARCH_MARGIN + _SEARCH_PAD_M
        search_rad = min(search_m / _EARTH_RADIUS_M, np.pi)

        neighbors = tree.query_radius(radians, r=search_rad)

        # Keep each candidate pair once (i < j), then verify on the ellipsoid.
        left: List[int] = []
        right: List[int] = []
        for i, idx in enumerate(neighbors):
            for j in idx:
                if i < j:
                    left.append(i)
                    right.append(int(j))

        if left:
            li = np.asarray(left, dtype=int)
            ri = np.asarray(right, dtype=int)
            geod = Geod(ellps="WGS84")
            _, _, dist = geod.inv(lon[li], lat[li], lon[ri], lat[ri])
            dist = np.abs(np.asarray(dist, dtype=float))
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