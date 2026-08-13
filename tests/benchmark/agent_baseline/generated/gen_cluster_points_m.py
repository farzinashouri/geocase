"""Single-linkage clustering of WGS84 points by geodesic distance threshold."""

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def cluster_points_m(points, max_distance_m):
    """Cluster (lon, lat) WGS84 points with single-linkage at a meter threshold.

    Two points share a cluster if they are within ``max_distance_m`` meters
    of each other (geodesic distance on the WGS84 ellipsoid), directly or
    through a chain of intermediate points. Returns a list of integer labels,
    one per input point, numbered 0, 1, 2, ... in order of first appearance.
    """
    points = list(points)
    n = len(points)
    if n == 0:
        return []

    # Union-find with path compression and union by size.
    parent = list(range(n))
    size = [1] * n

    def find(i):
        root = i
        while parent[root] != root:
            root = parent[root]
        while parent[i] != root:
            parent[i], i = root, parent[i]
        return root

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri == rj:
            return
        if size[ri] < size[rj]:
            ri, rj = rj, ri
        parent[rj] = ri
        size[ri] += size[rj]

    for i in range(n - 1):
        lon_i, lat_i = points[i]
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            lon_j, lat_j = points[j]
            _, _, dist = _GEOD.inv(lon_i, lat_i, lon_j, lat_j)
            if dist <= max_distance_m:
                union(i, j)

    labels = []
    root_to_label = {}
    for i in range(n):
        root = find(i)
        if root not in root_to_label:
            root_to_label[root] = len(root_to_label)
        labels.append(root_to_label[root])
    return labels
