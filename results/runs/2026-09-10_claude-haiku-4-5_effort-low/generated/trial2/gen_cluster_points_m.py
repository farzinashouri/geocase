def cluster_points_m(points, max_distance_m):
    """
    Cluster points by geographic distance using single-linkage clustering.
    
    Args:
        points: List of (lon, lat) tuples in WGS84
        max_distance_m: Distance threshold in meters
    
    Returns:
        List of integer cluster labels (0, 1, 2, ...)
    """
    if not points:
        return []
    
    points_list = list(points)
    
    if len(points_list) == 1:
        return [0]
    
    import pyproj
    
    # Find centroid to determine UTM zone
    avg_lon = sum(p[0] for p in points_list) / len(points_list)
    avg_lat = sum(p[1] for p in points_list) / len(points_list)
    
    # Calculate UTM zone from longitude
    utm_zone = int((avg_lon + 180) / 6) + 1
    utm_zone = max(1, min(60, utm_zone))
    
    # Select EPSG code based on hemisphere
    is_north = avg_lat >= 0
    epsg_code = 32600 + utm_zone if is_north else 32700 + utm_zone
    
    # Create coordinate transformer
    wgs84 = pyproj.CRS('EPSG:4326')
    utm_crs = pyproj.CRS(f'EPSG:{epsg_code}')
    transformer = pyproj.Transformer.from_crs(wgs84, utm_crs, always_xy=True)
    
    # Project points to UTM
    projected = []
    for lon, lat in points_list:
        x, y = transformer.transform(lon, lat)
        projected.append((x, y))
    
    # Union-Find data structure for clustering
    parent = list(range(len(projected)))
    
    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    # Connect points within max_distance_m
    for i in range(len(projected)):
        for j in range(i + 1, len(projected)):
            x1, y1 = projected[i]
            x2, y2 = projected[j]
            dist = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
            if dist <= max_distance_m:
                union(i, j)
    
    # Assign cluster labels in order of first appearance
    cluster_map = {}
    labels = []
    next_cluster = 0
    
    for i in range(len(points_list)):
        root = find(i)
        if root not in cluster_map:
            cluster_map[root] = next_cluster
            next_cluster += 1
        labels.append(cluster_map[root])
    
    return labels