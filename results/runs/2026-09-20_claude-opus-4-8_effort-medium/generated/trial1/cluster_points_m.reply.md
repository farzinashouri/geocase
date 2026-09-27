```python
"""Single-linkage geographic clustering by metric distance.

Groups WGS84 ``(lon, lat)`` points so that two points share a cluster
whenever a chain of points connects them, each consecutive pair being within
``max_distance_m`` meters (great-circle distance).
"""

import numpy as np
from sklearn.cluster import DBSCAN

# Mean Earth radius (meters), matching the sphere used by the haversine metric.
_EARTH_RADIUS_M = 6371008.8


def cluster_points_m(points, max_distance_m):
    """Cluster ``points`` by single linkage under a metric distance threshold.

    Args:
        points: list of ``(lon, lat)`` tuples in WGS84 (degrees).
        max_distance_m: distance threshold in meters. Two points are directly
            linked when their great-circle distance is ``<= max_distance_m``.

    Returns:
        A list of integer cluster labels, one per input point, numbered
        0, 1, 2, ... in order of first appearance.
    """
    n = len(points)
    if n == 0:
        return []
    if n == 1:
        return [0]

    # DBSCAN with the haversine metric expects (lat, lon) in radians and
    # measures distance in radians on the unit sphere.
    coords = np.asarray(points, dtype=float)
    lat_lon_rad = np.radians(coords[:, [1, 0]])
    eps_rad = float(max_distance_m) / _EARTH_RADIUS_M

    # min_samples=1 makes every point a core point, so DBSCAN's density
    # connectivity reduces to single-linkage clustering at threshold eps.
    raw = DBSCAN(eps=eps_rad, min_samples=1, metric="haversine").fit_predict(
        lat_lon_rad
    )

    # Renumber labels 0, 1, 2, ... in order of first appearance.
    remap = {}
    labels = []
    for value in raw:
        if value not in remap:
            remap[value] = len(remap)
        labels.append(remap[value])
    return labels
```