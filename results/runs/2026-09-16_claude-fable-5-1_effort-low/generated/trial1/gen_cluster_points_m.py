"""Single-linkage clustering of WGS84 points by geodesic distance in meters."""

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def cluster_points_m(points, max_distance_m):
    """Group (lon, lat) points into clusters using single linkage.

    Two points are linked when their geodesic distance is <= max_distance_m.
    Clusters are the connected components of that link graph. Returns one
    integer label per input point, numbered 0, 1, 2, ... in order of first
    appearance.
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

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    lons = [float(p[0]) for p in points]
    lats = [float(p[1]) for p in points]

    for i in range(n - 1):
        m = n - i - 1
        _, _, dists = _GEOD.inv(
            [lons[i]] * m, [lats[i]] * m, lons[i + 1 :], lats[i + 1 :]
        )
        for k, d in enumerate(dists):
            if d <= max_distance_m:
                union(i, i + 1 + k)

    labels = []
    root_to_label = {}
    for i in range(n):
        r = find(i)
        if r not in root_to_label:
            root_to_label[r] = len(root_to_label)
        labels.append(root_to_label[r])
    return labels