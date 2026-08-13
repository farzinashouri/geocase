```python
"""
Module for clustering geographic points based on a distance threshold in meters.
"""

import numpy as np
from sklearn.neighbors import BallTree

# Earth's mean radius in meters (WGS84 approximation)
EARTH_RADIUS_M = 6371000.0


class UnionFind:
    """Disjoint Set Union (Union-Find) data structure with path compression and union by rank."""
    __slots__ = ("parent", "rank")

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        # Path compression
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
    Cluster points (lon, lat) in WGS84 using single-linkage clustering with a distance threshold.

    Parameters
    ----------
    points : list[tuple[float, float]]
        List of (longitude, latitude) coordinates in degrees (WGS84).
    max_distance_m : float
        Maximum distance in meters for two points to be considered directly connected.

    Returns
    -------
    list[int]
        Cluster labels for each input point, numbered 0, 1, 2, ... in order of first appearance.
        Points in the same cluster have the same label.
    """
    if not points:
        return []

    # Convert to (lat, lon) in radians for BallTree haversine metric
    coords = np.array([(lat, lon) for lon, lat in points], dtype=np.float64)
    coords_rad = np.radians(coords)

    # Radius in radians
    radius_rad = max_distance_m / EARTH_RADIUS_M

    # Build BallTree and query all neighbors within radius
    tree = BallTree(coords_rad, metric="haversine")
    # query_radius returns a list of arrays of neighbor indices for each point
    neighbor_indices = tree.query_radius(coords_rad, r=radius_rad, return_distance=False)

    uf = UnionFind(len(points))
    for i, neighbors in enumerate(neighbor_indices):
        # Union with neighbors that have a higher index to avoid duplicate work
        for j in neighbors:
            if j > i:
                uf.union(i, j)

    # Assign cluster labels in order of first appearance
    root_to_label = {}
    labels = []
    next_label = 0
    for i in range(len(points)):
        root = uf.find(i)
        if root not in root_to_label:
            root_to_label[root] = next_label
            next_label += 1
        labels.append(root_to_label[root])

    return labels
```