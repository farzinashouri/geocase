import numpy as np
from sklearn.neighbors import BallTree

def cluster_points_m(points, max_distance_m):
    """
    Cluster geographic points using single-linkage with a distance threshold in meters.

    Parameters
    ----------
    points : list of tuple (float, float)
        List of (longitude, latitude) coordinates in WGS84.
    max_distance_m : float
        Maximum distance in meters for two points to be considered connected.

    Returns
    -------
    list of int
        Cluster labels for each point, numbered 0, 1, 2, ... in order of first appearance.
    """
    if not points:
        return []

    n = len(points)
    # BallTree haversine metric expects (lat, lon) in radians
    coords_rad = np.radians([(lat, lon) for lon, lat in points])

    # Mean Earth radius in meters (spherical approximation for haversine)
    EARTH_RADIUS_M = 6371000.0
    radius_rad = max_distance_m / EARTH_RADIUS_M

    # Build spatial index
    tree = BallTree(coords_rad, metric='haversine')

    # Find all neighbors within the radius for each point
    neighbors = tree.query_radius(coords_rad, r=radius_rad)

    # Union-Find (Disjoint Set Union) for connected components
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

    # Merge points that are within the distance threshold
    for i, neigh in enumerate(neighbors):
        for j in neigh:
            if j > i:  # avoid duplicate unions and self-union
                union(i, j)

    # Assign cluster labels in order of first appearance
    labels = []
    root_to_label = {}
    for i in range(n):
        root = find(i)
        if root not in root_to_label:
            root_to_label[root] = len(root_to_label)
        labels.append(root_to_label[root])

    return labels