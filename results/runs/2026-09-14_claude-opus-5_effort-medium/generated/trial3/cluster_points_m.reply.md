```python
"""Single-linkage clustering of WGS84 lon/lat points by a metric distance threshold.

Two points join the same cluster when the geodesic (WGS84 ellipsoid) distance
between them is at most ``max_distance_m``, transitively through chains of
intermediate points.

Candidate neighbour pairs are found with a spherical (haversine) ball tree using
a conservatively inflated radius, then each candidate pair is confirmed with an
exact geodesic inverse computation before being merged.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

import numpy as np
from pyproj import Geod
from sklearn.neighbors import BallTree

# WGS84 ellipsoid axes, in meters.
_WGS84_A = 6378137.0
_WGS84_B = 6356752.314245179

# A great-circle arc on a sphere of radius _WGS84_B is never longer than the
# corresponding WGS84 geodesic, so searching with this radius (plus a little
# slack for round-off) cannot miss a qualifying pair.
_RADIUS_SAFETY = 1.0001

# Cap on how many candidate pairs are handed to Geod.inv at once.
_INV_CHUNK = 1_000_000


class _UnionFind:
    def __init__(self, n: int) -> None:
        self._parent = list(range(n))
        self._rank = [0] * n

    def find(self, x: int) -> int:
        parent = self._parent
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1


def _labels_from_roots(uf: _UnionFind, n: int) -> List[int]:
    """Number clusters 0, 1, 2, ... in order of first appearance."""
    labels = [0] * n
    seen = {}
    for i in range(n):
        root = uf.find(i)
        label = seen.get(root)
        if label is None:
            label = len(seen)
            seen[root] = label
        labels[i] = label
    return labels


def _candidate_pairs(lon: np.ndarray, lat: np.ndarray, max_distance_m: float):
    """Yield (i_array, j_array) chunks of index pairs worth an exact check."""
    n = lon.size
    radius_rad = max_distance_m * _RADIUS_SAFETY / _WGS84_B
    if radius_rad >= math.pi:
        # The threshold exceeds any possible geodesic distance on the ellipsoid;
        # every pair is a candidate, but only pair each point with its successor
        # since transitivity does the rest.
        idx = np.arange(n - 1)
        yield idx, idx + 1
        return

    coords = np.column_stack((np.radians(lat), np.radians(lon)))
    tree = BallTree(coords, metric="haversine")
    neighbors = tree.query_radius(coords, r=radius_rad, return_distance=False)

    left: List[np.ndarray] = []
    right: List[np.ndarray] = []
    buffered = 0
    for i, nbrs in enumerate(neighbors):
        nbrs = nbrs[nbrs > i]
        if nbrs.size == 0:
            continue
        left.append(np.full(nbrs.size, i, dtype=np.int64))
        right.append(nbrs.astype(np.int64, copy=False))
        buffered += nbrs.size
        if buffered >= _INV_CHUNK:
            yield np.concatenate(left), np.concatenate(right)
            left, right, buffered = [], [], 0
    if buffered:
        yield np.concatenate(left), np.concatenate(right)


def cluster_points_m(
    points: Sequence[Tuple[float, float]], max_distance_m: float
) -> List[int]:
    """Single-linkage cluster ``points`` using a geodesic distance threshold.

    Args:
        points: Sequence of ``(lon, lat)`` tuples in WGS84 degrees.
        max_distance_m: Linkage threshold in meters. Points at most this far
            apart (directly or via a chain) share a cluster.

    Returns:
        One integer label per input point, numbered 0, 1, 2, ... in order of
        first appearance.
    """
    coords = np.asarray(points, dtype=float)
    if coords.size == 0:
        return []
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError("points must be a sequence of (lon, lat) pairs")
    if not np.isfinite(coords).all():
        raise ValueError("points must contain finite lon/lat values")

    n = coords.shape[0]
    if n == 1:
        return [0]

    threshold = float(max_distance_m)
    if math.isnan(threshold):
        raise ValueError("max_distance_m must not be NaN")
    if threshold < 0.0:
        # Nothing can link, so every point is its own cluster.
        return list(range(n))

    lon = coords[:, 0]
    lat = coords[:, 1]

    uf = _UnionFind(n)
    geod = Geod(ellps="WGS84")
    for i_idx, j_idx in _candidate_pairs(lon, lat, threshold):
        _, _, dist = geod.inv(lon[i_idx], lat[i_idx], lon[j_idx], lat[j_idx])
        dist = np.asarray(dist, dtype=float)
        # Non-convergent antipodal cases can come back as NaN; those are far
        # beyond any candidate radius, so drop them rather than linking.
        keep = np.isfinite(dist) & (dist <= threshold)
        for a, b in zip(i_idx[keep], j_idx[keep]):
            uf.union(int(a), int(b))

    return _labels_from_roots(uf, n)
```