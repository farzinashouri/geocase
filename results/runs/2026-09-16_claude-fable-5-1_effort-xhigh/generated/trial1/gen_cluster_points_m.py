"""Single-linkage clustering of WGS84 points by geodesic distance.

``cluster_points_m`` groups ``(lon, lat)`` points so that any two points whose
WGS84 geodesic separation is at most ``max_distance_m`` meters end up in the
same cluster, directly or through a chain of intermediate points.  Cluster
labels are dense integers numbered in order of first appearance.

The implementation is a two-stage search:

1. A cheap, provably conservative candidate search on the unit sphere
   (haversine central angle, via scikit-learn's BallTree when available,
   otherwise a chunked brute-force scan).  The search radius is chosen so
   that no pair within ``max_distance_m`` on the ellipsoid can be missed.
2. Exact WGS84 geodesic distances (pyproj) for the candidate pairs only,
   followed by union-find to build the connected components.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np
from pyproj import Geod

try:  # optional accelerator; a brute-force scan is used when it is absent
    from sklearn.neighbors import BallTree
except ImportError:  # pragma: no cover
    BallTree = None

__all__ = ["cluster_points_m"]

# Smallest radius of curvature on the WGS84 ellipsoid: the meridional radius at
# the equator, a * (1 - e^2).  Along any path, ellipsoidal length is at least
# this constant times the path's length on the unit sphere (in lat/lon), and
# the haversine central angle between two points is at most the unit-sphere
# length of any path joining them.  Hence geodesic distance d implies a
# central angle of at most d / _MIN_CURVATURE_RADIUS_M, which makes the
# candidate search below exact-safe.  The multiplicative factor and additive
# epsilon absorb floating-point error (the epsilon matters when d == 0).
_MIN_CURVATURE_RADIUS_M = 6_335_439.0
_ANGLE_SAFETY_FACTOR = 1.001
_ANGLE_EPSILON = 1e-12  # radians, about 6 micrometres on the ground

_PAIR_CHUNK = 1_000_000  # candidate pairs per geodesic call, bounds memory use


def cluster_points_m(
    points: Iterable[tuple[float, float]], max_distance_m: float
) -> list[int]:
    """Cluster WGS84 points by single-linkage geodesic distance.

    Parameters
    ----------
    points
        Iterable of ``(lon, lat)`` pairs in decimal degrees (WGS84).
    max_distance_m
        Linkage threshold in meters.  Two points are linked when their WGS84
        geodesic distance is less than or equal to this value.  Must be
        non-negative; ``0`` links only coincident points, ``inf`` links all.

    Returns
    -------
    list[int]
        One label per input point, in input order.  Labels are ``0, 1, 2, ...``
        assigned in order of each cluster's first appearance, so the first
        point always has label ``0``.  An isolated point forms its own cluster.

    Raises
    ------
    ValueError
        If ``points`` is not a sequence of numeric pairs, contains NaN or
        infinite coordinates, has a latitude outside ``[-90, 90]``, or if
        ``max_distance_m`` is negative or NaN.
    """
    lon, lat = _validate_points(points)
    threshold = _validate_distance(max_distance_m)
    n = lon.shape[0]
    if n == 0:
        return []

    angle = min(
        threshold / _MIN_CURVATURE_RADIUS_M * _ANGLE_SAFETY_FACTOR + _ANGLE_EPSILON,
        math.pi,
    )
    ii, jj = _candidate_pairs(np.radians(lat), np.radians(lon), angle)

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path halving
            x = parent[x]
        return x

    geod = Geod(ellps="WGS84")
    for start in range(0, ii.shape[0], _PAIR_CHUNK):
        a = ii[start : start + _PAIR_CHUNK]
        b = jj[start : start + _PAIR_CHUNK]
        _, _, dist = geod.inv(lon[a], lat[a], lon[b], lat[b])
        close = dist <= threshold
        for x, y in zip(a[close].tolist(), b[close].tolist()):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[ry] = rx

    labels_by_root: dict[int, int] = {}
    labels: list[int] = []
    for i in range(n):
        root = find(i)
        if root not in labels_by_root:
            labels_by_root[root] = len(labels_by_root)
        labels.append(labels_by_root[root])
    return labels


def _validate_points(points: Iterable[tuple[float, float]]) -> tuple[np.ndarray, np.ndarray]:
    """Return contiguous float64 ``(lon, lat)`` arrays, validating the input."""
    pts = list(points)
    if not pts:
        return np.empty(0, dtype=float), np.empty(0, dtype=float)
    try:
        arr = np.asarray(pts, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("points must be (lon, lat) pairs of numbers") from exc
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("points must be (lon, lat) pairs of numbers")
    if not np.isfinite(arr).all():
        raise ValueError("points must not contain NaN or infinite coordinates")
    lon = np.ascontiguousarray(arr[:, 0])
    lat = np.ascontiguousarray(arr[:, 1])
    if (np.abs(lat) > 90.0).any():
        raise ValueError("latitudes must lie within [-90, 90] degrees")
    return lon, lat


def _validate_distance(max_distance_m: float) -> float:
    try:
        threshold = float(max_distance_m)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_distance_m must be a real number") from exc
    if math.isnan(threshold) or threshold < 0.0:
        raise ValueError("max_distance_m must be a non-negative number")
    return threshold


def _candidate_pairs(
    lat_r: np.ndarray, lon_r: np.ndarray, angle: float
) -> tuple[np.ndarray, np.ndarray]:
    """Index pairs ``(i < j)`` whose unit-sphere central angle is at most ``angle``."""
    n = lat_r.shape[0]
    if BallTree is not None:
        coords = np.column_stack([lat_r, lon_r])  # haversine wants [lat, lon]
        neighbours = BallTree(coords, metric="haversine").query_radius(coords, r=angle)
        counts = np.fromiter((nb.shape[0] for nb in neighbours), dtype=np.intp, count=n)
        ii = np.repeat(np.arange(n, dtype=np.intp), counts)
        jj = np.concatenate(list(neighbours)).astype(np.intp, copy=False)
    else:
        ii, jj = _brute_force_pairs(lat_r, lon_r, angle)
    keep = jj > ii
    return ii[keep], jj[keep]


def _brute_force_pairs(
    lat_r: np.ndarray, lon_r: np.ndarray, angle: float
) -> tuple[np.ndarray, np.ndarray]:
    """O(n^2) haversine scan, one row at a time, used when scikit-learn is missing."""
    n = lat_r.shape[0]
    cos_lat = np.cos(lat_r)
    ii_parts: list[np.ndarray] = []
    jj_parts: list[np.ndarray] = []
    for i in range(n - 1):
        j = np.arange(i + 1, n, dtype=np.intp)
        h = (
            np.sin((lat_r[j] - lat_r[i]) / 2.0) ** 2
            + cos_lat[i] * cos_lat[j] * np.sin((lon_r[j] - lon_r[i]) / 2.0) ** 2
        )
        theta = 2.0 * np.arcsin(np.sqrt(np.clip(h, 0.0, 1.0)))
        hit = j[theta <= angle]
        ii_parts.append(np.full(hit.shape[0], i, dtype=np.intp))
        jj_parts.append(hit)
    if not ii_parts:
        return np.empty(0, dtype=np.intp), np.empty(0, dtype=np.intp)
    return np.concatenate(ii_parts), np.concatenate(jj_parts)