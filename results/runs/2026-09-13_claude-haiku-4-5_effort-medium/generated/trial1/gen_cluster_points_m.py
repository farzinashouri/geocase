from math import radians, cos, sin, asin, sqrt

def cluster_points_m(points, max_distance_m):
    """
    Cluster points based on geographic distance using single-linkage clustering.
    
    Args:
        points: List of (lon, lat) tuples in WGS84
        max_distance_m: Maximum distance in meters for points to be in the same cluster
    
    Returns:
        List of cluster labels (0, 1, 2, ...) in order of first appearance
    """
    if not points:
        return []
    
    n = len(points)
    parent = list(range(n))
    
    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    def haversine(lon1, lat1, lon2, lat2):
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return 6371000 * c
    
    for i in range(n):
        for j in range(i + 1, n):
            if haversine(points[i][0], points[i][1], points[j][0], points[j][1]) <= max_distance_m:
                union(i, j)
    
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