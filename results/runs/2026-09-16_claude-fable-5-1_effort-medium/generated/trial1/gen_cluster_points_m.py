"""Single-linkage clustering of WGS84 points by geodesic distance.

Public API: ``cluster_points_m(points, max_distance_m)``.

Two points join the same cluster when they are within ``max_distance_m``
metres of each other, directly or through a chain of intermediate points.
Labels are integers 0, 1, 2, ... assigned in order of first appearance.

Only the standard library is required. If numpy and scikit-learn are
installed, candidate pairs are found with a haversine BallTree instead of an
O(n^2) scan. If pyproj is installed, candidate pairs are confirmed with a
true WGS84 geodesic distance; otherwise the spherical haversine distance is
used.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

# Mean Earth radius (IUGG), metres. Used for the spherical fallback and for
# converting the search radius into radians for the BallTree query.
_EARTH_RADIUS_M = 6371008.8

# Haversine on a sphere differs from the WGS84 geodesic by well under 1 %.
# Candidate search uses an inflated radius so no true neighbour is missed
# before geodesic verification.
_CANDIDATE_INFLATION = 1.01


class _UnionFind:
    __slots__ = ("_parent", "_rank")

    def __init__(self, n: int) -> None:
        self._parent = list(range(n))
        self._rank = [0] * n

    def find(self, x: int) -> int:
        parent = self._parent
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:  # path compression
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


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    a = min(1.0, max(0.0, a))
    return 2.0 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _make_distance_fn():
    """Return a (lon1, lat1, lon2, lat2) -> metres function.

    Prefers the WGS84 geodesic from pyproj; falls back to haversine.
    """
    try:
        from pyproj import Geod  # type: ignore

        geod = Geod(ellps="WGS84")

        def geodesic_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
            _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
            return float(dist)

        return geodesic_m
    except Exception:  # pragma: no cover - depends on environment
        return _haversine_m


def _candidate_pairs_balltree(
    lons: Sequence[float], lats: Sequence[float], radius_m: float
) -> Iterable[Tuple[int, int]]:
    """Yield (i, j) with i < j whose haversine distance <= radius_m.

    Uses scikit-learn's BallTree; raises ImportError if unavailable.
    """
    import numpy as np  # type: ignore
    from sklearn.neighbors import BallTree  # type: ignore

    coords = np.column_stack(
        (np.radians(np.asarray(lats, dtype=float)), np.radians(np.asarray(lons, dtype=float)))
    )
    tree = BallTree(coords, metric="haversine")
    neighbours = tree.query_radius(coords, r=radius_m / _EARTH_RADIUS_M)
    for i, idx in enumerate(neighbours):
        for j in idx.tolist():
            if j > i:
                yield i, j


def _candidate_pairs_bruteforce(
    lons: Sequence[float], lats: Sequence[float], radius_m: float
) -> Iterable[Tuple[int, int]]:
    n = len(lons)
    for i in range(n):
        for j in range(i + 1, n):
            if _haversine_m(lons[i], lats[i], lons[j], lats[j]) <= radius_m:
                yield i, j


def cluster_points_m(points: Sequence[Tuple[float, float]], max_distance_m: float) -> List[int]:
    """Cluster WGS84 ``(lon, lat)`` points by single-linkage geodesic distance.

    Parameters
    ----------
    points
        Sequence of ``(lon, lat)`` pairs in decimal degrees (WGS84).
    max_distance_m
        Linkage threshold in metres. Two points are linked when their
        geodesic distance is less than or equal to this value.

    Returns
    -------
    list of int
        One cluster label per input point, numbered from 0 in order of
        first appearance.
    """
    pts = [(float(lon), float(lat)) for lon, lat in points]
    n = len(pts)
    if n == 0:
        return []
    if not math.isfinite(max_distance_m):
        raise ValueError("max_distance_m must be finite")
    if max_distance_m < 0:
        raise ValueError("max_distance_m must be non-negative")
    for lon, lat in pts:
        if not (math.isfinite(lon) and math.isfinite(lat)):
            raise ValueError("points must contain finite coordinates")
        if not -90.0 <= lat <= 90.0:
            raise ValueError(f"latitude out of range: {lat!r}")

    lons = [p[0] for p in pts]
    lats = [p[1] for p in pts]

    distance_m = _make_distance_fn()
    exact = distance_m is _haversine_m
    search_radius = max_distance_m if exact else max_distance_m * _CANDIDATE_INFLATION

    try:
        candidates = list(_candidate_pairs_balltree(lons, lats, search_radius))
    except ImportError:
        candidates = list(_candidate_pairs_bruteforce(lons, lats, search_radius))

    uf = _UnionFind(n)
    for i, j in candidates:
        if exact or distance_m(lons[i], lats[i], lons[j], lats[j]) <= max_distance_m:
            uf.union(i, j)

    labels: List[int] = [0] * n
    root_to_label = {}
    for i in range(n):
        root = uf.find(i)
        if root not in root_to_label:
            root_to_label[root] = len(root_to_label)
        labels[i] = root_to_label[root]
    return labels


__all__ = ["cluster_points_m"]