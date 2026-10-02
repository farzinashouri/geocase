import numpy as np
from sklearn.neighbors import BallTree

EARTH_RADIUS_M = 6371000.0  # mean Earth radius in meters


def cluster_points_m(points, max_distance_m):
    """
    Cluster points (lon, lat) in WGS84 using single-linkage with a distance threshold in meters.

    Parameters
    ----------
    points : list[tuple[float, float]]
        List of (longitude, latitude) coordinates.
    max_distance_m : float
        Maximum distance in meters for two points to be considered connected.

    Returns
    -------
    list[int]
        Cluster label for each input point, labeled 0, 1, 2, ... in order of first appearance.
    """
    n = len(points)
    if n == 0:
        return []

    # Convert (lon, lat) to (lat, lon) in radians for BallTree haversine metric
    coords_rad = np.radians([[lat, lon] for lon, lat in points])

    # Radius in radians
    radius_rad = max_distance_m / EARTH_RADIUS_M

    # Build BallTree and query all neighbors within radius
    tree = BallTree(coords_rad, metric="haversine")
    neighbor_indices = tree.query_radius(coords_rad, r=radius_rad, return_distance=False)

    # Disjoint Set Union (Union-Find) with path compression and union by rank
    parent = list(range(n))
    rank = [0] * n

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
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

    # Union each point with its neighbors
    for i, neighbors in enumerate(neighbor_indices):
        for j in neighbors:
            if i != j:
                union(i, j)

    # Assign cluster labels in order of first appearance
    root_to_label = {}
    labels = []
    next_label = 0
    for i in range(n):
        root = find(i)
        if root not in root_to_label:
            root_to_label[root] = next_label
            next_label += 1
        labels.append(root_to_label[root])

    return labels