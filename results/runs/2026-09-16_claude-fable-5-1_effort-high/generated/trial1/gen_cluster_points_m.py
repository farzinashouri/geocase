"""Single-linkage clustering of WGS84 points by geodesic distance in meters."""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

try:  # pyproj gives true WGS84 geodesic distances; fall back to haversine if absent.
    from pyproj import Geod as _Geod
except ImportError:  # pragma: no cover
    _Geod = None

_EARTH_RADIUS_M = 6_371_008.8  # mean Earth radius, used only by the haversine fallback
_MAX_DEG_PER_M = 1.0 / 110_574.0  # 1 degree of latitude is never shorter than ~110.57 km


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def _distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    if _Geod is not None:
        geod = _Geod(ellps="WGS84")
        _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
        return float(dist)
    return _haversine_m(lon1, lat1, lon2, lat2)


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
        parent[rb] = ra


def cluster_points_m(points: Sequence[Tuple[float, float]], max_distance_m: float) -> List[int]:
    """Group WGS84 (lon, lat) points by single-linkage within max_distance_m meters.

    Returns one integer label per input point. Labels are 0, 1, 2, ... in order of
    the first point that appears in each cluster. An isolated point is its own cluster.
    """
    pts = [(float(lon), float(lat)) for lon, lat in points]
    n = len(pts)
    parent = list(range(n))

    if n > 1 and max_distance_m >= 0:
        # Cheap pre-filter: a pair whose latitude difference alone exceeds the threshold
        # cannot be within range, so skip the geodesic computation for it.
        lat_tol_deg = max_distance_m * _MAX_DEG_PER_M * 1.01
        for i in range(n):
            lon_i, lat_i = pts[i]
            for j in range(i + 1, n):
                lon_j, lat_j = pts[j]
                if abs(lat_i - lat_j) > lat_tol_deg:
                    continue
                if _find(parent, i) == _find(parent, j):
                    continue
                if _distance_m(lon_i, lat_i, lon_j, lat_j) <= max_distance_m:
                    _union(parent, i, j)

    labels: List[int] = []
    root_to_label: dict = {}
    for i in range(n):
        root = _find(parent, i)
        if root not in root_to_label:
            root_to_label[root] = len(root_to_label)
        labels.append(root_to_label[root])
    return labels