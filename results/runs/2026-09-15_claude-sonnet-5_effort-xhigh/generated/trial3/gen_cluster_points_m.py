"""Single-linkage clustering of WGS84 points by geodesic distance threshold."""
from __future__ import annotations

from typing import List, Tuple

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def cluster_points_m(
    points: List[Tuple[float, float]], max_distance_m: float
) -> List[int]:
    n = len(points)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        lon1, lat1 = points[i]
        for j in range(i + 1, n):
            lon2, lat2 = points[j]
            _, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
            if dist <= max_distance_m:
                union(i, j)

    labels = [-1] * n
    root_to_label = {}
    next_label = 0
    for i in range(n):
        root = find(i)
        if root not in root_to_label:
            root_to_label[root] = next_label
            next_label += 1
        labels[i] = root_to_label[root]

    return labels