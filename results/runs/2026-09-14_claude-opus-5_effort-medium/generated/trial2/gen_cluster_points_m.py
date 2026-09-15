"""Single-linkage spatial clustering of WGS84 points with a metric threshold.

Two points are placed in the same cluster when the geodesic (ellipsoidal)
distance between them is at most ``max_distance_m``, transitively.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import numpy as np
from pyproj import Geod, Transformer

__all__ = ["cluster_points_m"]

# WGS84 geographic (lon, lat) -> WGS84 geocentric (ECEF, metres).
_TO_ECEF = Transformer.from_crs("EPSG:4326", "EPSG:4978", always_xy=True)
_GEOD = Geod(ellps="WGS84")

# Geodesic distances are computed in blocks to bound peak memory.
_CHUNK = 100_000


class _DisjointSet:
    """Union-find with path halving and union by size."""

    def __init__(self, n: int) -> None:
        self._parent = list(range(n))
        self._size = [1] * n

    def find(self, x: int) -> int:
        parent = self._parent
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self._size[ra] < self._size[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        self._size[ra] += self._size[rb]


def _as_array(points: Iterable[Sequence[float]]) -> np.ndarray:
    """Validate the input and return an (n, 2) float array of (lon, lat)."""
    arr = np.asarray(list(points), dtype=float)
    if arr.size == 0:
        return np.empty((0, 2), dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("points must be a sequence of (lon, lat) pairs")
    if not np.isfinite(arr).all():
        raise ValueError("points must contain only finite coordinates")
    if np.any(np.abs(arr[:, 1]) > 90.0):
        raise ValueError("latitudes must lie within [-90, 90]")
    return arr


def _candidate_pairs(lonlat: np.ndarray, max_distance_m: float) -> np.ndarray:
    """Return an (m, 2) array of index pairs (i < j) that may be within range.

    Points are embedded in 3D geocentric coordinates, where the straight-line
    (chord) distance is never greater than the geodesic distance on the
    ellipsoid.  A chord-radius query therefore yields a superset of the true
    neighbours, which is then filtered exactly by the caller.
    """
    n = len(lonlat)
    x, y, z = _TO_ECEF.transform(lonlat[:, 0], lonlat[:, 1], np.zeros(n))
    xyz = np.column_stack((x, y, z))

    try:
        from sklearn.neighbors import KDTree
    except ImportError:  # pragma: no cover - exercised only without sklearn
        return _candidate_pairs_bruteforce(xyz, max_distance_m)

    tree = KDTree(xyz)
    neighbours = tree.query_radius(xyz, r=max_distance_m)

    left: List[np.ndarray] = []
    right: List[np.ndarray] = []
    for i, js in enumerate(neighbours):
        js = js[js > i]
        if js.size:
            left.append(np.full(js.shape, i, dtype=np.intp))
            right.append(js.astype(np.intp, copy=False))
    if not left:
        return np.empty((0, 2), dtype=np.intp)
    return np.column_stack((np.concatenate(left), np.concatenate(right)))


def _candidate_pairs_bruteforce(xyz: np.ndarray, max_distance_m: float) -> np.ndarray:
    """Blocked O(n^2) fallback used when scikit-learn is unavailable."""
    n = len(xyz)
    block = max(1, _CHUNK // max(n, 1))
    left: List[np.ndarray] = []
    right: List[np.ndarray] = []
    for start in range(0, n, block):
        stop = min(start + block, n)
        d = np.linalg.norm(xyz[start:stop, None, :] - xyz[None, :, :], axis=2)
        rows, cols = np.nonzero(d <= max_distance_m)
        rows = rows + start
        keep = cols > rows
        if keep.any():
            left.append(rows[keep])
            right.append(cols[keep])
    if not left:
        return np.empty((0, 2), dtype=np.intp)
    return np.column_stack(
        (np.concatenate(left).astype(np.intp), np.concatenate(right).astype(np.intp))
    )


def cluster_points_m(
    points: Iterable[Sequence[float]], max_distance_m: float
) -> List[int]:
    """Single-linkage cluster WGS84 ``(lon, lat)`` points by geodesic distance.

    Args:
        points: Iterable of ``(lon, lat)`` pairs in decimal degrees (WGS84).
        max_distance_m: Linkage threshold in metres; points closer than or
            equal to this distance are linked, directly or through a chain.

    Returns:
        A list of integer cluster labels, one per input point, numbered
        ``0, 1, 2, ...`` in order of first appearance.
    """
    if not np.isfinite(max_distance_m) or max_distance_m < 0:
        raise ValueError("max_distance_m must be a finite, non-negative number")

    lonlat = _as_array(points)
    n = len(lonlat)
    if n == 0:
        return []
    if n == 1:
        return [0]

    dsu = _DisjointSet(n)
    pairs = _candidate_pairs(lonlat, float(max_distance_m))

    # Confirm each candidate with an exact geodesic distance on the ellipsoid.
    for start in range(0, len(pairs), _CHUNK):
        block = pairs[start : start + _CHUNK]
        i, j = block[:, 0], block[:, 1]
        _, _, dist = _GEOD.inv(
            lonlat[i, 0], lonlat[i, 1], lonlat[j, 0], lonlat[j, 1]
        )
        dist = np.asarray(dist, dtype=float)
        # Coincident points yield NaN azimuths but a zero distance.
        dist = np.where(np.isnan(dist), 0.0, dist)
        for a, b in zip(i[dist <= max_distance_m], j[dist <= max_distance_m]):
            dsu.union(int(a), int(b))

    labels: List[int] = []
    seen: dict[int, int] = {}
    for idx in range(n):
        root = dsu.find(idx)
        label = seen.get(root)
        if label is None:
            label = len(seen)
            seen[root] = label
        labels.append(label)
    return labels