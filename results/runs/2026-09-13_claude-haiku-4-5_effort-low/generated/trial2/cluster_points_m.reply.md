```python
from pyproj import Geodesic

def cluster_points_m(points, max_distance_m):
    if not points:
        return []
    
    n = len(points)
    
    # Union-Find for connected components
    parent = list(range(n))
    
    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    # Build clusters by connecting points within distance threshold
    geod = Geodesic.WGS84
    for i in range(n):
        for j in range(i + 1, n):
            lon1, lat1 = points[i]
            lon2, lat2 = points[j]
            distance_m = geod.inverse(lon1, lat1, lon2, lat2)[2]
            
            if distance_m <= max_distance_m:
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