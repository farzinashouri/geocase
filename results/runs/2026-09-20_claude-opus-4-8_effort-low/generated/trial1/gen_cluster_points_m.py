"""Single-linkage clustering of WGS84 points by a metric distance threshold.

Importing this module has no side effects.
"""

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def cluster_points_m(points, max_distance_m):
    """Cluster (lon, lat) points using single linkage.

    Two points are in the same cluster if they lie within ``max_distance_m``
    meters of each other, directly or via a chain of intermediate points.

    Returns a list of integer cluster labels (one per input point), numbered
    0, 1, 2, ... in order of first appearance.
    """
    n = len(points)
    if n == 0:
        return []

    # Union-Find over point indices.
    parent = list(range(n))

    def find(i):
        root = i
        while parent[root] != root:
            root = parent[root]
        while parent[i] != root:
            parent[i], i = root, parent[i]
        return root

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    # Connect every pair within the threshold (geodesic distance on WGS84).
    for i in range(n):
        lon_i, lat_i = points[i]
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            lon_j, lat_j = points[j]
            _, _, dist = _GEOD.inv(lon_i, lat_i, lon_j, lat_j)
            if dist <= max_distance_m:
                union(i, j)

    # Relabel roots by order of first appearance.
    labels = [0] * n
    label_of_root = {}
    next_label = 0
    for i in range(n):
        root = find(i)
        if root not in label_of_root:
            label_of_root[root] = next_label
            next_label += 1
        labels[i] = label_of_root[root]

    return labels