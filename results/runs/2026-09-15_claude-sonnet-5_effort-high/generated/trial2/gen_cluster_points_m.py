from pyproj import Geod


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
    geod = Geod(ellps="WGS84")

    for i in range(n):
        lon1, lat1 = points[i]
        for j in range(i + 1, n):
            lon2, lat2 = points[j]
            _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
            if dist <= max_distance_m:
                uf.union(i, j)

    labels = [-1] * n
    label_for_root = {}
    next_label = 0
    for i in range(n):
        root = uf.find(i)
        if root not in label_for_root:
            label_for_root[root] = next_label
            next_label += 1
        labels[i] = label_for_root[root]

    return labels