"""Single-linkage clustering of WGS84 (lon, lat) points by geodesic distance.

`cluster_points_m(points, max_distance_m)` groups points so that any two
points within `max_distance_m` meters of each other (directly or through a
chain of intermediate points) share a cluster. Labels are integers starting
at 0, assigned in order of first appearance in the input.

Distances are computed on the WGS84 ellipsoid with pyproj when available and
fall back to the spherical haversine formula otherwise. Importing this module
performs no I/O and constructs no global objects.
"""

from __future__ import annotations

import math
from typing import Callable, List, Sequence, Tuple

Point = Tuple[float, float]

# Mean Earth radius (meters), used only by the haversine fallback.
_EARTH_RADIUS_M = 6371008.8

# Conservative lower bound on meters per degree of latitude on WGS84
# (the true value is ~110,574 m at the equator, ~111,694 m at the poles).
# Used to prune pairs that cannot possibly be within the threshold.
_MIN_M_PER_DEG_LAT = 110_000.0


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in meters on a sphere of mean Earth radius."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = phi2 - phi1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2.0) ** 2
    a = min(1.0, max(0.0, a))
    return 2.0 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _make_distance_fn() -> Callable[[float, float, float, float], float]:
    """Return a distance function, preferring the WGS84 ellipsoid via pyproj."""
    try:
        from pyproj import Geod  # type: ignore
    except Exception:  # pragma: no cover - depends on environment
        return _haversine_m

    geod = Geod(ellps="WGS84")

    def _geodesic_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
        return float(dist)

    return _geodesic_m


class _UnionFind:
    """Disjoint-set forest with path compression and union by size."""

    __slots__ = ("parent", "size")

    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.size = [1] * n

    def find(self, x: int) -> int:
        parent = self.parent
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(self, a: int, b: int) -> None:
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]


def _validate(points: Sequence[Point], max_distance_m: float) -> List[Point]:
    try:
        threshold = float(max_distance_m)
    except (TypeError, ValueError) as exc:
        raise TypeError("max_distance_m must be a real number") from exc
    if math.isnan(threshold) or threshold < 0.0:
        raise ValueError("max_distance_m must be a non-negative number")

    cleaned: List[Point] = []
    for idx, pt in enumerate(points):
        try:
            lon, lat = pt
            lon = float(lon)
            lat = float(lat)
        except (TypeError, ValueError) as exc:
            raise TypeError(f"points[{idx}] must be a (lon, lat) pair of numbers") from exc
        if not (math.isfinite(lon) and math.isfinite(lat)):
            raise ValueError(f"points[{idx}] has non-finite coordinates: {pt!r}")
        if not -90.0 <= lat <= 90.0:
            raise ValueError(f"points[{idx}] latitude out of range [-90, 90]: {lat!r}")
        cleaned.append((lon, lat))
    return cleaned


def cluster_points_m(points: Sequence[Point], max_distance_m: float) -> List[int]:
    """Cluster WGS84 points by single linkage at a geodesic distance threshold.

    Args:
        points: Sequence of ``(lon, lat)`` pairs in decimal degrees (WGS84).
        max_distance_m: Distance threshold in meters. Two points are linked
            when their geodesic separation is ``<= max_distance_m``.

    Returns:
        A list of integer cluster labels, one per input point, numbered
        ``0, 1, 2, ...`` in order of first appearance.

    Raises:
        TypeError: if inputs are malformed.
        ValueError: if a coordinate is non-finite, a latitude is out of range,
            or the threshold is negative / NaN.
    """
    pts = _validate(points, max_distance_m)
    n = len(pts)
    if n == 0:
        return []
    if n == 1:
        return [0]

    threshold = float(max_distance_m)
    distance = _make_distance_fn()
    uf = _UnionFind(n)

    # Sweep by latitude: any pair whose latitude difference alone exceeds the
    # threshold cannot be linked, so we only compare against a sliding window.
    # A small relative slack keeps the prune conservative against the bound.
    max_dlat_deg = (threshold / _MIN_M_PER_DEG_LAT) * 1.001 + 1e-12
    order = sorted(range(n), key=lambda i: pts[i][1])

    for a in range(n):
        i = order[a]
        lon_i, lat_i = pts[i]
        for b in range(a + 1, n):
            j = order[b]
            lon_j, lat_j = pts[j]
            if lat_j - lat_i > max_dlat_deg:
                break
            if uf.find(i) == uf.find(j):
                continue
            if distance(lon_i, lat_i, lon_j, lat_j) <= threshold:
                uf.union(i, j)

    labels: List[int] = [0] * n
    root_to_label: dict = {}
    for i in range(n):
        root = uf.find(i)
        label = root_to_label.get(root)
        if label is None:
            label = len(root_to_label)
            root_to_label[root] = label
        labels[i] = label
    return labels


__all__ = ["cluster_points_m"]