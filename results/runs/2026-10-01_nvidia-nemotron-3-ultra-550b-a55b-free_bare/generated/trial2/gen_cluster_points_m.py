import numpy as np
from sklearn.neighbors import BallTree

# Mean Earth radius in meters (WGS84 authalic radius ≈ 6371007 m, 6371000 is a common approximation)
EARTH_RADIUS_M = 6371000.0


class UnionFind:
    """Disjoint-set data structure with path compression and union by rank."""
    __slots__ = ("parent", "rank")

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        # Path compression (iterative)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        xroot = self.find(x)
        yroot = self.find(y)
        if xroot == yroot:
            return
        # Union by rank
        if self.rank[xroot] < self.rank[yroot]:
            self.parent[xroot] = yroot
        elif self.rank[xroot] > self.rank[yroot]:
            self.parent[yroot] = xroot
        else:
            self.parent[yroot] = xroot
            self.rank[xroot] += 1


def cluster_points_m(points, max_distance_m):
    """
    Group points into clusters using single-linkage clustering based on a distance threshold.

    Parameters
    ----------
    points : list of tuple (float, float)
        List of (longitude, latitude) coordinates in WGS84 (EPSG:4326).
    max_distance_m : float
        Maximum distance in meters for two points to be considered directly connected.

    Returns
    -------
    list of int
        Cluster label for each input point. Labels are 0, 1, 2, ... assigned in order
        of first appearance of each cluster.
    """
    if not points:
        return []

    n = len(points)
    # BallTree expects (lat, lon) in radians for the haversine metric.
    coords = np.array([(lat, lon) for lon, lat in points], dtype=np.float64)
    coords_rad = np.radians(coords)

    # Build BallTree with haversine metric (distance returned in radians).
    tree = BallTree(coords_rad, metric="haversine")

    # Convert distance threshold from meters to radians.
    radius_rad = max_distance_m / EARTH_RADIUS_M
    # Cap at pi (half the Earth's circumference) to avoid numerical issues.
    if radius_rad > np.pi:
        radius_rad = np.pi

    # Query all points for neighbors within the radius.
    # Returns a list of arrays; each array contains indices of neighbors (including the point itself).
    neighbors = tree.query_radius(coords_rad, r=radius_rad)

    uf = UnionFind(n)
    for i, idxs in enumerate(neighbors):
        for j in idxs:
            if j > i:  # avoid duplicate unions and self-unions
                uf.union(i, j)

    # Assign cluster labels in order of first appearance.
    label_map = {}
    labels = []
    next_label = 0
    for i in range(n):
        root = uf.find(i)
        if root not in label_map:
            label_map[root] = next_label
            next_label += 1
        labels.append(label_map[root])

    return labels