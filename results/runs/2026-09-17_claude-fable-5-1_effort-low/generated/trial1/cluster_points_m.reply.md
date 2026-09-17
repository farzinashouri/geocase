```python
"""Single-linkage clustering of WGS84 points by great-circle distance in meters."""

import math

_EARTH_RADIUS_M = 6371008.8


def _haversine_m(lon1, lat1, lon2, lat2):
    """Great-circle distance in meters between two WGS84 lon/lat points."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = phi2 - phi1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    a = min(1.0, max(0.0, a))
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


def cluster_points_m(points, max_distance_m):
    """Label points with single-linkage clusters using a meter threshold.

    points: list of (lon, lat) tuples in WGS84.
    max_distance_m: two points are linked when their distance is <= this value.
    Returns a list of integer labels, one per point, numbered 0, 1, 2, ...
    in order of first appearance.
    """
    n = len(points)
    if n == 0:
        return []

    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    # Quick bounding-box rejection in degrees before the exact haversine test.
    lat_margin = math.degrees(max_distance_m / _EARTH_RADIUS_M) + 1e-9

    for i in range(n):
        lon_i, lat_i = points[i]
        for j in range(i + 1, n):
            lon_j, lat_j = points[j]
            if abs(lat_i - lat_j) > lat_margin:
                continue
            if _haversine_m(lon_i, lat_i, lon_j, lat_j) <= max_distance_m:
                union(i, j)

    labels = []
    root_to_label = {}
    for i in range(n):
        r = find(i)
        if r not in root_to_label:
            root_to_label[r] = len(root_to_label)
        labels.append(root_to_label[r])
    return labels
```