from pyproj import Geodesic


def cluster_points_m(points, max_distance_m):
    if not points:
        return []
    
    n = len(points)
    
    # Union-Find data structure
    parent = list(range(n))
    
    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    # Calculate geodesic distances and union points that are close
    geod = Geodesic("+ellps=WGS84")
    
    for i in range(n):
        for j in range(i + 1, n):
            lon1, lat1 = points[i]
            lon2, lat2 = points[j]
            
            result = geod.inverse(lon1, lat1, lon2, lat2)
            distance = result['s12']  # distance in meters
            
            if distance <= max_distance_m:
                union(i, j)
    
    # Assign cluster labels in order of first appearance
    label_map = {}
    labels = []
    next_label = 0
    
    for i in range(n):
        root = find(i)
        if root not in label_map:
            label_map[root] = next_label
            next_label += 1
        labels.append(label_map[root])
    
    return labels