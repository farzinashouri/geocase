```python
"""Single-linkage clustering of geographic points."""

from pyproj import Geodesic


def cluster_points_m(points, max_distance_m):
    """
    Cluster points using single-linkage clustering with a distance threshold.
    
    Args:
        points: List of (lon, lat) tuples in WGS84
        max_distance_m: Maximum distance threshold in meters
    
    Returns:
        List of integer cluster labels (0, 1, 2, ...) in order of first appearance
    """
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
    
    # Calculate distances and union nearby points
    geod = Geodesic(ellps='WGS84')
    
    for i in range(n):
        for j in range(i + 1, n):
            lon1, lat1 = points[i]
            lon2, lat2 = points[j]
            distance = geod.inverse(lon1, lat1, lon2, lat2)[0]
            
            if distance <= max_distance_m:
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