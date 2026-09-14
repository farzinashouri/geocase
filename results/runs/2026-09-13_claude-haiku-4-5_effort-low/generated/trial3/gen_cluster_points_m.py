from pyproj import Geod
from typing import List, Tuple


def cluster_points_m(points: List[Tuple[float, float]], max_distance_m: float) -> List[int]:
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
    
    geod = Geod(ellps='WGS84')
    
    for i in range(n):
        for j in range(i + 1, n):
            lon1, lat1 = points[i]
            lon2, lat2 = points[j]
            _, _, distance = geod.inv(lon1, lat1, lon2, lat2)
            if distance <= max_distance_m:
                union(i, j)
    
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