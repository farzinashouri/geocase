```python
import numpy as np
from sklearn.neighbors import KDTree
from pyproj import Transformer, Geod

def cluster_points_m(points, max_distance_m):
    """
    Cluster points (lon, lat) in WGS84 using single-linkage with a distance threshold in meters.

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
    points_arr = np.array(points, dtype=np.float64)
    lons = points_arr[:, 0]
    lats = points_arr[:, 1]

    # Transform to ECEF (Earth-Centered, Earth-Fixed) coordinates in meters.
    # Chord distance in 3D is a lower bound for geodesic distance on the ellipsoid.
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:4978", always_xy=True)
    x, y, z = transformer.transform(lons, lats)
    ecef_coords = np.column_stack((x, y, z))

    # Build KDTree for efficient radius search using chord distance.
    tree = KDTree(ecef_coords, metric='euclidean')

    # Union-Find data structure for connected components.
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

    # Geod for exact geodesic distance calculation on WGS84 ellipsoid.
    geod = Geod(ellps='WGS84')

    # Query all neighbors within chord distance <= max_distance_m.
    neighbor_indices = tree.query_radius(ecef_coords, r=max_distance_m, return_distance=False)

    for i, neighbors in enumerate(neighbor_indices):
        for j in neighbors:
            if j <= i:
                continue
            # Verify with exact geodesic distance.
            _, _, dist = geod.inv(lons[i], lats[i], lons[j], lats[j])
            if dist <= max_distance_m:
                union(i, j)

    # Assign cluster labels in order of first appearance.
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
```