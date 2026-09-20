from pyproj import Geod

def cluster_points_m(points, max_distance_m):
    """
    Cluster points using single-linkage clustering based on geographic distance.
    
    Args:
        points: List of (lon, lat) tuples in WGS84 coordinates
        max_distance_m: Maximum distance in meters to connect points
    
    Returns:
        List of integer cluster labels (0, 1, 2, ...) in order of first appearance
    """
    if not points:
        return []
    
    n = len(points)
    parent = list(range(n))
    
    def find(i):
        if parent[i] != i:
            parent[i] = find(parent[i])
        return parent[i]
    
    def union(i, j):
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j
    
    geod = Geod(ellps='WGS84')
    
    for i in range(n):
        for j in range(i + 1, n):
            lon1, lat1 = points[i]
            lon2, lat2 = points[j]
            _, _, distance = geod.inv(lon1, lat1, lon2, lat2)
            
            if distance <= max_distance_m:
                union(i, j)
    
    root_to_cluster = {}
    cluster_labels = []
    next_cluster_id = 0
    
    for i in range(n):
        root = find(i)
        if root not in root_to_cluster:
            root_to_cluster[root] = next_cluster_id
            next_cluster_id += 1
        cluster_labels.append(root_to_cluster[root])
    
    return cluster_labels