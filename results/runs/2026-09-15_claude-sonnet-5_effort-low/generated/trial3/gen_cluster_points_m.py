from math import radians, sin, cos, asin, sqrt


def _haversine_m(p1, p2):
    lon1, lat1 = p1
    lon2, lat2 = p2
    lon1, lat1, lon2, lat2 = map(radians, (lon1, lat1, lon2, lat2))
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371008.8 * asin(sqrt(a))


def cluster_points_m(points, max_distance_m):
    n = len(points)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    for i in range(n):
        for j in range(i + 1, n):
            if _haversine_m(points[i], points[j]) <= max_distance_m:
                union(i, j)

    labels = {}
    result = []
    for i in range(n):
        root = find(i)
        if root not in labels:
            labels[root] = len(labels)
        result.append(labels[root])
    return result