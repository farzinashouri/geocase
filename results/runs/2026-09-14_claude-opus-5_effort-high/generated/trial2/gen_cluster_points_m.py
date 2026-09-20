"""Single-linkage clustering of WGS84 points by true geodesic distance.

``cluster_points_m`` groups ``(lon, lat)`` points so that two points share a
cluster whenever a chain of points connects them with every hop no longer than
``max_distance_m`` meters, measured as a WGS84 geodesic.

Neighbour search is done on the sphere (a fast, conservative superset) and every
candidate pair is then verified with an exact geodesic inverse solution, so the
result is correct near the poles and across the antimeridian.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from typing import Iterator, List, Sequence, Tuple

import numpy as np
from pyproj import Geod

__all__ = ["cluster_points_m"]

_GEOD = Geod(ellps="WGS84")

# Smallest radius of curvature of the WGS84 ellipsoid (b**2 / a, reached at the
# equator).  Along any path, ellipsoidal arc length is at least _MIN_RADIUS_M
# times the arc length of the same path on a unit sphere parameterised by
# geodetic (lat, lon).  Hence a spherical search of angular radius
# max_distance_m / _MIN_RADIUS_M cannot miss a true neighbour.
_MIN_RADIUS_M = 6_335_439.0

_QUERY_CHUNK = 1024
_PAIR_CHUNK = 262_144


def cluster_points_m(
    points: Sequence[Tuple[float, float]], max_distance_m: float
) -> List[int]:
    """Single-linkage cluster ``points`` at a ``max_distance_m`` threshold.

    Args:
        points: sequence of ``(lon, lat)`` pairs in WGS84 decimal degrees.
        max_distance_m: linkage threshold in meters; pairs at exactly this
            distance are linked.  Must be finite and non-negative.

    Returns:
        One integer label per input point, labels numbered 0, 1, 2, ... in
        order of first appearance.
    """
    coords = _coords(points)
    n = coords.shape[0]
    if n == 0:
        return []

    threshold = float(max_distance_m)
    if not math.isfinite(threshold) or threshold < 0.0:
        raise ValueError("max_distance_m must be a finite, non-negative number")
    if n == 1:
        return [0]

    lon = coords[:, 0]
    lat = coords[:, 1]

    # Conservative angular radius, plus a little slack for rounding.
    theta = min(math.pi, threshold / _MIN_RADIUS_M * (1.0 + 1e-9) + 1e-12)

    parent = list(range(n))
    for rows, cols in _candidate_pairs(lon, lat, theta):
        _, _, dist = _GEOD.inv(lon[rows], lat[rows], lon[cols], lat[cols])
        close = np.asarray(dist) <= threshold
        for i, j in zip(rows[close].tolist(), cols[close].tolist()):
            _union(parent, i, j)

    labels = [0] * n
    seen: dict = {}
    for i in range(n):
        root = _find(parent, i)
        label = seen.get(root)
        if label is None:
            label = len(seen)
            seen[root] = label
        labels[i] = label
    return labels


def _coords(points: Sequence[Tuple[float, float]]) -> np.ndarray:
    """Validate the input and return an ``(n, 2)`` float array of lon/lat."""
    arr = np.asarray(points, dtype=float)
    if arr.size == 0:
        return np.empty((0, 2), dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("points must be a sequence of (lon, lat) pairs")
    if not np.isfinite(arr).all():
        raise ValueError("points must contain only finite coordinates")
    if np.any(np.abs(arr[:, 1]) > 90.0):
        raise ValueError("latitudes must lie within [-90, 90] degrees")
    return arr


def _candidate_pairs(
    lon: np.ndarray, lat: np.ndarray, theta: float
) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    """Yield ``(rows, cols)`` index arrays, ``cols > rows``, for pairs that may
    lie within the threshold.  The union of all yields is a superset of the
    truly-linked pairs."""
    try:
        from sklearn.neighbors import BallTree
    except ImportError:  # pragma: no cover - exercised only without sklearn
        yield from _brute_force_pairs(lon, lat, theta)
        return

    n = lon.shape[0]
    radians = np.column_stack([np.radians(lat), np.radians(lon)])
    tree = BallTree(radians, metric="haversine")
    for start in range(0, n, _QUERY_CHUNK):
        stop = min(start + _QUERY_CHUNK, n)
        neighbours = tree.query_radius(radians[start:stop], r=theta)
        counts = [len(item) for item in neighbours]
        rows = np.repeat(np.arange(start, stop), counts)
        cols = np.concatenate(neighbours).astype(np.intp, copy=False)
        keep = cols > rows
        yield from _split(rows[keep], cols[keep])


def _brute_force_pairs(
    lon: np.ndarray, lat: np.ndarray, theta: float
) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    """sklearn-free fallback: chunked dot products of unit sphere vectors."""
    n = lon.shape[0]
    lat_r = np.radians(lat)
    lon_r = np.radians(lon)
    cos_lat = np.cos(lat_r)
    xyz = np.column_stack(
        [cos_lat * np.cos(lon_r), cos_lat * np.sin(lon_r), np.sin(lat_r)]
    )
    cos_theta = math.cos(theta) - 1e-12
    for start in range(0, n, _QUERY_CHUNK):
        stop = min(start + _QUERY_CHUNK, n)
        dots = xyz[start:stop] @ xyz.T
        rows, cols = np.nonzero(dots >= cos_theta)
        rows = rows + start
        keep = cols > rows
        yield from _split(rows[keep], cols[keep])


def _split(
    rows: np.ndarray, cols: np.ndarray
) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    """Emit the pair arrays in bounded-size batches."""
    for start in range(0, rows.shape[0], _PAIR_CHUNK):
        stop = start + _PAIR_CHUNK
        yield rows[start:stop], cols[start:stop]


def _find(parent: List[int], item: int) -> int:
    root = item
    while parent[root] != root:
        root = parent[root]
    while parent[item] != root:
        parent[item], item = root, parent[item]
    return root


def _union(parent: List[int], a: int, b: int) -> None:
    root_a = _find(parent, a)
    root_b = _find(parent, b)
    if root_a != root_b:
        # Attach the larger index to the smaller one: the smallest index in a
        # component stays its root, which keeps `_find` shallow for the
        # first-appearance labelling pass.
        if root_a < root_b:
            parent[root_b] = root_a
        else:
            parent[root_a] = root_b