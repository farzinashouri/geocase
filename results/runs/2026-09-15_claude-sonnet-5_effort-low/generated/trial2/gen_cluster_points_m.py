import math


def _haversine_m(p1, p2):
    lon1, lat1 = p1
    lon2, lat2 = p2
    r = 6371008.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


class _UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def cluster_points_m(points, max_distance_m):
    n = len(points)
    uf = _UnionFind(n)

    for i in range(n):
        for j in range(i + 1, n):
            if _haversine_m(points[i], points[j]) <= max_distance_m:
                uf.union(i, j)

    labels = [-1] * n
    next_label = 0
    root_to_label = {}
    for i in range(n):
        root = uf.find(i)
        if root not in root_to_label:
            root_to_label[root] = next_label
            next_label += 1
        labels[i] = root_to_label[root]

    return labels