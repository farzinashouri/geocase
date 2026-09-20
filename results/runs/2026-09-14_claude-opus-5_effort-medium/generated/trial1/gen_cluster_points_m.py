"""Single-linkage clustering of WGS84 lon/lat points by a metric distance threshold.

Two points join the same cluster when the geodesic (WGS84 ellipsoid) distance
between them is at most ``max_distance_m``, transitively through intermediate
points. Candidate neighbour pairs are found with a haversine BallTree using a
radius inflated to the sphere's minimum radius of curvature, so the candidate
set is a strict superset of the true geodesic neighbours; each candidate pair is
then verified exactly with pyproj's geodesic inverse.

Importing this module has no side effects beyond constructing a Geod object.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

import numpy as np
from pyproj import Geod
from sklearn.neighbors import BallTree

__all__ = ["cluster_points_m"]

_GEOD = Geod(ellps="WGS84")

# Smallest radius of curvature of the WGS84 ellipsoid (meridional, at the
# equator). For a central angle theta, the geodesic length is at least
# _MIN_RADIUS_M * theta, so theta <= d / _MIN_RADIUS_M for any geodesic of
# length d. Dividing the threshold by this radius therefore never under-covers.
_MIN_RADIUS_M = 6_335_439.0

# Guard against floating point shaving off borderline pairs.
_SLACK = 1.0 + 1e-9


def _find(parent: List[int], i: int) -> int:
    root = i
    while parent[root] != root:
        root = parent[root]
    while parent[i] != root:  # path compression
        parent[i], i = root, parent[i]
    return root


def _union(parent: List[int], a: int, b: int) -> None:
    ra, rb = _find(parent, a), _find(parent, b)
    if ra != rb:
        parent[max(ra, rb)] = min(ra, rb)


def cluster_points_m(
    points: Sequence[Tuple[float, float]], max_distance_m: float
) -> List[int]:
    """Cluster ``(lon, lat)`` points by single linkage under a metre threshold.

    Args:
        points: Sequence of ``(lon, lat)`` pairs in WGS84 degrees.
        max_distance_m: Linkage threshold in metres (inclusive). Values below
            zero put every point in its own cluster; zero links only coincident
            points.

    Returns:
        One integer label per input point, numbered 0, 1, 2, ... in order of
        each cluster's first appearance in ``points``.

    Raises:
        ValueError: If the input is not an ``(n, 2)`` array of finite
            coordinates with latitudes in [-90, 90], or if ``max_distance_m``
            is not finite.
    """
    coords = np.asarray(points, dtype=float)
    if coords.size == 0:
        return []
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError("points must be a sequence of (lon, lat) pairs")
    if not np.isfinite(coords).all():
        raise ValueError("points must contain finite coordinates")
    if np.any(np.abs(coords[:, 1]) > 90.0):
        raise ValueError("latitudes must lie in [-90, 90]")

    max_distance_m = float(max_distance_m)
    if not math.isfinite(max_distance_m):
        raise ValueError("max_distance_m must be finite")

    n = coords.shape[0]
    parent = list(range(n))

    if n > 1 and max_distance_m >= 0.0:
        # BallTree's haversine metric wants (lat, lon) in radians.
        latlon_rad = np.radians(coords[:, ::-1])
        tree = BallTree(latlon_rad, metric="haversine")
        radius = min(max_distance_m / _MIN_RADIUS_M * _SLACK + 1e-12, math.pi)
        neighborhoods = tree.query_radius(latlon_rad, r=radius)

        left: List[int] = []
        right: List[int] = []
        for i, neighbors in enumerate(neighborhoods):
            for j in neighbors:
                if j > i:  # each unordered pair once
                    left.append(i)
                    right.append(int(j))

        if left:
            li = np.asarray(left, dtype=np.intp)
            ri = np.asarray(right, dtype=np.intp)
            _, _, dist = _GEOD.inv(
                coords[li, 0], coords[li, 1], coords[ri, 0], coords[ri, 1]
            )
            dist = np.asarray(dist, dtype=float)
            # Antipodal/degenerate inverse solutions can come back as NaN; those
            # are far beyond any sane threshold, so drop them.
            linked = np.flatnonzero(np.isfinite(dist) & (dist <= max_distance_m))
            for k in linked:
                _union(parent, int(li[k]), int(ri[k]))

    labels: List[int] = [0] * n
    seen: dict = {}
    for i in range(n):
        root = _find(parent, i)
        label = seen.get(root)
        if label is None:
            label = len(seen)
            seen[root] = label
        labels[i] = label
    return labels