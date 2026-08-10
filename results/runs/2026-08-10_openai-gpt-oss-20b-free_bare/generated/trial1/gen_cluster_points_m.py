import math
from typing import List, Tuple

import numpy as np
from sklearn.cluster import DBSCAN


def cluster_points_m(points: List[Tuple[float, float]], max_distance_m: float) -> List[int]:
    """
    Cluster geographic points using single-linkage based on a maximum distance threshold.

    Parameters
    ----------
    points : list of (lon, lat) tuples
        Input points in WGS84 longitude/latitude degrees.
    max_distance_m : float
        Distance threshold in meters. Points within this distance (directly or via a chain)
        belong to the same cluster.

    Returns
    -------
    list of int
        Cluster labels for each input point. Labels are consecutive integers starting at 0.
    """
    if not points:
        return []

    # Convert degrees to radians for haversine metric
    coords = np.radians(np.asarray(points, dtype=float))

    # Earth's radius in meters (WGS84 mean radius)
    EARTH_RADIUS_M = 6371000.0

    # DBSCAN epsilon in radians
    eps_rad = max_distance_m / EARTH_RADIUS_M

    # Perform DBSCAN clustering with haversine metric
    db = DBSCAN(eps=eps_rad, min_samples=1, metric="haversine")
    db.fit(coords)

    # DBSCAN labels are already consecutive integers starting from 0
    return db.labels_.tolist()