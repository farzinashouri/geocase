```python
from pyproj import Geodesic


def cluster_points_m(points, max_distance_m):
    if not points:
        return []
    
    n = len(points)
    geod = Geodesic()
    parent = list(range(n))
    
    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    for i in range(n):
        for j in range(i + 1, n):
            lon1, lat1 = points[i]
            lon2, lat2 = points[j]
            result = geod.inverse(lon1, lat1, lon2, lat2)
            if result['s12'] <= max_distance_m:
                union(i, j)
    
    seen = {}
    labels = []
    next_label = 0
    for i in range(n):
        root = find(i)
        if root not in seen:
            seen[root] = next_label
            next_label += 1
        labels.append(seen[root])
    
    return labels
```