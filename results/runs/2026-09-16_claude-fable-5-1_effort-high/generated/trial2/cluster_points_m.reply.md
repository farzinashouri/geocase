```python
"""Single-linkage clustering of WGS84 (lon, lat) points by geodesic distance in meters."""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import numpy as np

try:  # optional: accurate ellipsoidal distances
    from pyproj import Geod as _Geod
except Exception:  # pragma: no cover
    _Geod = None

try:  # optional: fast neighbour search
    from sklearn.neighbors import KDTree as _KDTree
except Exception:  # pragma: no cover
    _KDTree = None

_WGS84_A = 6378137.0
_WGS84_F = 1.0 / 298.257223563
_WGS84_E2 = _WGS84_F * (2.0 - _WGS84_F)
_MEAN_RADIUS_M = 6371008.8

_geod_instance = None


def _geod():
    """Lazily build the WGS84 Geod so importing the module has no side effects."""
    global _geod_instance
    if _geod_instance is None and _Geod is not None:
        _geod_instance = _Geod(ellps="WGS84")
    return _geod_instance


def _to_ecef(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Convert degrees lon/lat on the WGS84 ellipsoid to ECEF metres, shape (n, 3)."""
    lon_r = np.radians(lon)
    lat_r = np.radians(lat)
    sin_lat = np.sin(lat_r)
    cos_lat = np.cos(lat_r)
    n = _WGS84_A / np.sqrt(1.0 - _WGS84_E2 * sin_lat * sin_lat)
    x = n * cos_lat * np.cos(lon_r)
    y = n * cos_lat * np.sin(lon_r)
    z = n * (1.0 - _WGS84_E2) * sin_lat
    return np.column_stack([x, y, z])


def _geodesic_m(lon1, lat1, lon2, lat2) -> np.ndarray:
    """Geodesic distance in metres (WGS84 via pyproj; haversine fallback)."""
    lon1 = np.asarray(lon1, dtype=float)
    lat1 = np.asarray(lat1, dtype=float)
    lon2 = np.asarray(lon2, dtype=float)
    lat2 = np.asarray(lat2, dtype=float)
    g = _geod()
    if g is not None:
        _, _, dist = g.inv(lon1, lat1, lon2, lat2)
        return np.asarray(dist, dtype=float)
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlmb = np.radians(lon2 - lon1)
    h = np.sin(dphi / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2.0) ** 2
    return 2.0 * _MEAN_RADIUS_M * np.arcsin(np.sqrt(np.clip(h, 0.0, 1.0)))


def _candidate_pairs(xyz: np.ndarray, radius: float) -> Tuple[np.ndarray, np.ndarray]:
    """Index pairs (i < j) whose straight-line chord distance is <= radius.

    A chord never exceeds the geodesic between the same two points, so this is
    a superset of the pairs that are truly within the threshold. Working in
    ECEF also handles the antimeridian and the poles without special casing.
    """
    n = xyz.shape[0]
    empty = (np.empty(0, dtype=np.intp), np.empty(0, dtype=np.intp))
    if n < 2:
        return empty
    if _KDTree is not None and n > 64:
        tree = _KDTree(xyz)
        neigh = tree.query_radius(xyz, r=radius)
        ii, jj = [], []
        for i, js in enumerate(neigh):
            js = js[js > i]
            if js.size:
                ii.append(np.full(js.size, i, dtype=np.intp))
                jj.append(js.astype(np.intp))
        if not ii:
            return empty
        return np.concatenate(ii), np.concatenate(jj)
    # Brute force in row chunks (bounded memory).
    r2 = radius * radius
    ii, jj = [], []
    chunk = max(1, 2_000_000 // n)
    for start in range(0, n, chunk):
        block = xyz[start:start + chunk]
        d2 = ((block[:, None, :] - xyz[None, :, :]) ** 2).sum(axis=2)
        a, b = np.nonzero(d2 <= r2)
        a = a + start
        keep = b > a
        ii.append(a[keep].astype(np.intp))
        jj.append(b[keep].astype(np.intp))
    return np.concatenate(ii), np.concatenate(jj)


class _UnionFind:
    __slots__ = ("parent",)

    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        p = self.parent
        root = x
        while p[root] != root:
            root = p[root]
        while p[x] != root:
            p[x], x = root, p[x]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def cluster_points_m(points: Sequence[Tuple[float, float]], max_distance_m: float) -> List[int]:
    """Single-linkage clustering of WGS84 ``(lon, lat)`` points.

    Two points share a cluster if their geodesic distance is at most
    ``max_distance_m`` metres, directly or through a chain of intermediate
    points. An isolated point forms its own cluster. Returns one integer label
    per input point, numbered 0, 1, 2, ... in order of first appearance.
    """
    pts = list(points)
    n = len(pts)
    if n == 0:
        return []
    arr = np.asarray(pts, dtype=float).reshape(n, 2)
    lon = arr[:, 0]
    lat = arr[:, 1]
    uf = _UnionFind(n)

    threshold = float(max_distance_m)
    valid = np.isfinite(lon) & np.isfinite(lat) & (np.abs(lat) <= 90.0)
    idx = np.flatnonzero(valid)

    if threshold >= 0.0 and idx.size >= 2:
        xyz = _to_ecef(lon[idx], lat[idx])
        radius = threshold * (1.0 + 1e-9) + 1e-6  # tiny slack against rounding
        ci, cj = _candidate_pairs(xyz, radius)
        if ci.size:
            gi, gj = idx[ci], idx[cj]
            dist = _geodesic_m(lon[gi], lat[gi], lon[gj], lat[gj])
            ok = dist <= threshold
            for a, b in zip(gi[ok].tolist(), gj[ok].tolist()):
                uf.union(a, b)

    labels: List[int] = []
    root_to_label: Dict[int, int] = {}
    for i in range(n):
        r = uf.find(i)
        if r not in root_to_label:
            root_to_label[r] = len(root_to_label)
        labels.append(root_to_label[r])
    return labels
```