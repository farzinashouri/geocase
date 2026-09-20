from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def cluster_points_m(points, max_distance_m):
    n = len(points)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        lon_i, lat_i = points[i]
        for j in range(i + 1, n):
            lon_j, lat_j = points[j]
            _, _, dist = _GEOD.inv(lon_i, lat_i, lon_j, lat_j)
            if dist <= max_distance_m:
                union(i, j)

    labels = {}
    result = []
    for i in range(n):
        root = find(i)
        if root not in labels:
            labels[root] = len(labels)
        result.append(labels[root])
    return result