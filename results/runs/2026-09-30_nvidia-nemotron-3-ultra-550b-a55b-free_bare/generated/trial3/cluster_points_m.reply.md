```python
import numpy as np
from sklearn.neighbors import BallTree

# Mean Earth radius in meters (used by haversine metric)
EARTH_RADIUS_M = 6371000.0


def cluster_points_m(points, max_distance_m):
    """
    Cluster geographic points using single-linkage clustering with a distance threshold.

    Parameters
    ----------
    points : list[tuple[float, float]]
        List of (longitude, latitude) coordinates in WGS84 (degrees).
    max_distance_m : float
        Maximum distance in meters for two points to be considered directly connected.

    Returns
    -------
    list[int]
        Cluster label for each input point. Labels are 0, 1, 2, ... assigned in order
        of first appearance of each cluster.
    """
    if not points:
        return []

    n = len(points)
    # BallTree expects (lat, lon) in radians for haversine metric
    coords = np.array([(lat, lon) for lon, lat in points], dtype=np.float64)
    coords_rad = np.radians(coords)

    # Build BallTree with haversine metric (distance returned in radians)
    tree = BallTree(coords_rad, metric="haversine")

    # Convert distance threshold to radians
    radius_rad = max_distance_m / EARTH_RADIUS_M
    # Cap at pi (maximum possible haversine distance)
    if radius_rad > np.pi:
        radius_rad = np.pi

    # Union-Find (Disjoint Set Union) data structure
    parent = list(range(n))
    rank = [0] * n

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx == ry:
            return
        if rank[rx] < rank[ry]:
            parent[rx] = ry
        elif rank[rx] > rank[ry]:
            parent[ry] = rx
        else:
            parent[ry] = rx
            rank[rx] += 1

    # Find all neighbors within radius for each point
    # query_radius returns a list of arrays of neighbor indices (including the point itself)
    neighbors_list = tree.query_radius(coords_rad, r=radius_rad, return_distance=False)

    for i, neighbors in enumerate(neighbors_list):
        for j in neighbors:
            if j > i:  # avoid duplicate unions and self-union
                union(i, j)

    # Assign cluster labels in order of first appearance
    cluster_map = {}
    labels = []
    next_label = 0
    for i in range(n):
        root = find(i)
        if root not in cluster_map:
            cluster_map[root] = next_label
            next_label += 1
        labels.append(cluster_map[root])

    return labels
```