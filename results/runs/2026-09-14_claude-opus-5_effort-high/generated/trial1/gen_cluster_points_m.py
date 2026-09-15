"""Single-linkage clustering of WGS84 lon/lat points by a metric distance threshold.

Two points join the same cluster when the geodesic (ellipsoidal) distance between
them is at most ``max_distance_m``; clusters are the transitive closure of that
relation.  Candidate pairs are found with a 3-D index over geocentric (ECEF)
coordinates and then confirmed with exact geodesic distances, so the result is
correct across the antimeridian and at the poles.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

import numpy as np
from pyproj import Geod

# WGS84 defining parameters.
_A = 6378137.0
_F = 1.0 / 298.257223563
_E2 = _F * (2.0 - _F)

# Number of candidate pairs whose geodesic distance is evaluated per call to
# ``Geod.inv``; bounds peak memory without paying per-pair Python overhead.
_PAIR_CHUNK = 200_000

# Target number of float entries per block of the brute-force fallback.
_BRUTE_BLOCK_ENTRIES = 4_000_000

__all__ = ["cluster_points_m"]


def cluster_points_m(
    points: Iterable[Sequence[float]], max_distance_m: float
) -> List[int]:
    """Cluster WGS84 ``(lon, lat)`` points by single linkage.

    Parameters
    ----------
    points:
        Iterable of ``(lon, lat)`` pairs in decimal degrees (WGS84).
    max_distance_m:
        Non-negative linkage threshold in meters.  Points at exactly this
        distance are linked.

    Returns
    -------
    list of int
        One label per input point, in input order, numbered ``0, 1, 2, ...`` in
        order of first appearance.

    Raises
    ------
    ValueError
        If the input is not an ``(n, 2)`` array of finite coordinates, a
        latitude lies outside ``[-90, 90]``, or ``max_distance_m`` is negative
        or not finite.
    """
    lon, lat = _parse_points(points)
    n = lon.size

    threshold = float(max_distance_m)
    if not math.isfinite(threshold) or threshold < 0.0:
        raise ValueError("max_distance_m must be a non-negative, finite number")

    if n == 0:
        return []
    if n == 1:
        return [0]

    parent = np.arange(n, dtype=np.int64)
    size = np.ones(n, dtype=np.int64)

    xyz = _ecef(lon, lat)
    geod = Geod(ellps="WGS84")

    # The straight-line (chord) distance between two surface points never
    # exceeds the geodesic distance, so a chord-radius query with `threshold`
    # returns a superset of the truly linked pairs.  Each candidate is then
    # checked against the exact geodesic distance.
    for rows, cols in _candidate_pairs(xyz, threshold):
        if rows.size == 0:
            continue
        _, _, dist = geod.inv(lon[rows], lat[rows], lon[cols], lat[cols])
        linked = np.asarray(dist) <= threshold
        for i, j in zip(rows[linked], cols[linked]):
            _union(parent, size, int(i), int(j))

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


def _parse_points(points: Iterable[Sequence[float]]) -> Tuple[np.ndarray, np.ndarray]:
    """Validate the input and return contiguous ``(lon, lat)`` float arrays."""
    arr = np.asarray(list(points), dtype=float)
    if arr.size == 0:
        empty = np.empty(0, dtype=float)
        return empty, empty.copy()
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("points must be an iterable of (lon, lat) pairs")
    if not np.isfinite(arr).all():
        raise ValueError("points must contain only finite coordinates")

    lon = np.ascontiguousarray(arr[:, 0])
    lat = np.ascontiguousarray(arr[:, 1])
    if np.any(np.abs(lat) > 90.0):
        raise ValueError("latitudes must lie within [-90, 90] degrees")
    return lon, lat


def _ecef(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Convert lon/lat degrees to WGS84 geocentric XYZ meters at height 0."""
    lon_rad = np.radians(lon)
    lat_rad = np.radians(lat)
    sin_lat = np.sin(lat_rad)
    cos_lat = np.cos(lat_rad)
    prime_vertical = _A / np.sqrt(1.0 - _E2 * sin_lat * sin_lat)

    xyz = np.empty((lon.size, 3), dtype=float)
    xyz[:, 0] = prime_vertical * cos_lat * np.cos(lon_rad)
    xyz[:, 1] = prime_vertical * cos_lat * np.sin(lon_rad)
    xyz[:, 2] = prime_vertical * (1.0 - _E2) * sin_lat
    return xyz


def _candidate_pairs(xyz: np.ndarray, radius: float):
    """Yield ``(rows, cols)`` index arrays of pairs within ``radius`` (chord).

    Only pairs with ``rows < cols`` are emitted, in chunks.
    """
    try:
        from sklearn.neighbors import KDTree
    except ImportError:
        yield from _brute_force_pairs(xyz, radius)
        return

    tree = KDTree(xyz)
    neighbors = tree.query_radius(xyz, r=radius)

    rows_buf: List[np.ndarray] = []
    cols_buf: List[np.ndarray] = []
    buffered = 0
    for i, idx in enumerate(neighbors):
        idx = np.asarray(idx, dtype=np.int64)
        idx = idx[idx > i]
        if idx.size == 0:
            continue
        rows_buf.append(np.full(idx.size, i, dtype=np.int64))
        cols_buf.append(idx)
        buffered += idx.size
        if buffered >= _PAIR_CHUNK:
            yield np.concatenate(rows_buf), np.concatenate(cols_buf)
            rows_buf, cols_buf, buffered = [], [], 0
    if buffered:
        yield np.concatenate(rows_buf), np.concatenate(cols_buf)


def _brute_force_pairs(xyz: np.ndarray, radius: float):
    """Blocked O(n^2) candidate search, used when scikit-learn is unavailable."""
    n = xyz.shape[0]
    block = max(1, _BRUTE_BLOCK_ENTRIES // max(n, 1))
    radius_sq = radius * radius
    for start in range(0, n, block):
        stop = min(start + block, n)
        deltas = xyz[start:stop, None, :] - xyz[None, :, :]
        dist_sq = np.einsum("ijk,ijk->ij", deltas, deltas)
        local_rows, cols = np.nonzero(dist_sq <= radius_sq)
        rows = local_rows.astype(np.int64) + start
        upper = cols > rows
        yield rows[upper], cols[upper].astype(np.int64)


def _find(parent: np.ndarray, i: int) -> int:
    """Union-find lookup with full path compression."""
    root = i
    while parent[root] != root:
        root = int(parent[root])
    while parent[i] != root:
        parent[i], i = root, int(parent[i])
    return root


def _union(parent: np.ndarray, size: np.ndarray, i: int, j: int) -> None:
    """Merge the sets containing ``i`` and ``j``, smaller tree under larger."""
    root_i = _find(parent, i)
    root_j = _find(parent, j)
    if root_i == root_j:
        return
    if size[root_i] < size[root_j]:
        root_i, root_j = root_j, root_i
    parent[root_j] = root_i
    size[root_i] += size[root_j]