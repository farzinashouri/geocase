```python
import numpy as np
from sklearn.cluster import DBSCAN
from pyproj import Geod

__all__ = ["cluster_points_m"]


def cluster_points_m(points, max_distance_m):
    """
    Cluster geographic points using single-linkage with a distance threshold.

    Parameters
    ----------
    points : list[tuple[float, float]]
        List of (lon, lat) tuples in WGS84 coordinates.
    max_distance_m : float
        Distance threshold in meters. Points within this distance (directly or
        via a chain of intermediate points) belong to the same cluster.

    Returns
    -------
    list[int]
        Cluster labels for each input point. Labels are consecutive integers
        starting at 0, assigned in the order of first appearance.
    """
    if not points:
        return []

    # Convert to NumPy array for easier manipulation
    pts = np.asarray(points, dtype=float)
    n = pts.shape[0]

    # Prepare a distance matrix
    dist_matrix = np.zeros((n, n), dtype=float)

    # Geodesic distance calculator (WGS84 ellipsoid)
    geod = Geod(ellps="WGS84")

    # Compute pairwise distances
    for i in range(n):
        lon1, lat1 = pts[i]
        for j in range(i + 1, n):
            lon2, lat2 = pts[j]
            _, _, d = geod.inv(lon1, lat1, lon2, lat2)
            dist_matrix[i, j] = d
            dist_matrix[j, i] = d

    # Perform DBSCAN with precomputed distance matrix
    db = DBSCAN(eps=max_distance_m, min_samples=1, metric="precomputed")
    db.fit(dist_matrix)

    # Remap labels to ensure they are in order of first appearance
    original_labels = db.labels_
    label_map = {}
    next_label = 0
    remapped = []
    for lbl in original_labels:
        if lbl not in label_map:
            label_map[lbl] = next_label
            next_label += 1
        remapped.append(label_map[lbl])

    return remapped
```