```python
"""Single-linkage clustering of WGS84 (lon, lat) points by geodesic distance in meters."""

from math import asin, cos, radians, sin, sqrt

_EARTH_RADIUS_M = 6_371_008.8


def _haversine_m(lon1, lat1, lon2, lat2):
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = phi2 - phi1
    dlmb = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlmb / 2) ** 2
    return 2 * _EARTH_RADIUS_M * asin(min(1.0, sqrt(a)))


def cluster_points_m(points, max_distance_m):
    """Return cluster labels (0, 1, 2, ... by first appearance) for single-linkage clusters.

    Two points are linked when their geodesic distance is <= max_distance_m; clusters are
    the connected components of that link graph. Isolated points form their own cluster.
    """
    pts = [(float(lon), float(lat)) for lon, lat in points]
    n = len(pts)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)

    if n > 1 and max_distance_m >= 0:
        # Coarse latitude-band prefilter before the exact distance check.
        max_dlat = max_distance_m / _EARTH_RADIUS_M * (180.0 / 3.141592653589793)
        order = sorted(range(n), key=lambda i: pts[i][1])
        for a in range(n):
            i = order[a]
            lon_i, lat_i = pts[i]
            for b in range(a + 1, n):
                j = order[b]
                lon_j, lat_j = pts[j]
                if lat_j - lat_i > max_dlat + 1e-9:
                    break
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