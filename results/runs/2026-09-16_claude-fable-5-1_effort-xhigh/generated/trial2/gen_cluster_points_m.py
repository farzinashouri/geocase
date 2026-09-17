"""Single-linkage clustering of WGS84 points by geodesic distance in metres.

``cluster_points_m`` groups ``(lon, lat)`` points so that two points share a
cluster whenever their surface distance is at most ``max_distance_m`` metres,
either directly or through a chain of intermediate points.

Distances are geodesics on the WGS84 ellipsoid (via pyproj) when pyproj is
installed, and great-circle (haversine) distances on a mean-radius sphere
otherwise.  Candidate pairs are found with a 3-D grid over Earth-centred
Cartesian coordinates: the straight-line chord between two surface points can
never exceed the surface distance, so only points in the same or an adjacent
grid cell can possibly be within the threshold.  Those candidates are then
verified with the exact distance and merged with a union-find structure.
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Sequence, Tuple

try:  # Exact WGS84 geodesics when available.
    from pyproj import Geod as _Geod
except ImportError:  # pragma: no cover - only exercised without pyproj
    _Geod = None

__all__ = ["cluster_points_m"]

# WGS84 ellipsoid parameters.
_WGS84_A = 6378137.0
_WGS84_F = 1.0 / 298.257223563
_WGS84_E2 = _WGS84_F * (2.0 - _WGS84_F)
# IUGG mean Earth radius, used by the spherical fallback.
_SPHERE_R = 6371008.8
# No two points on Earth are farther apart than this along the surface.
_MAX_EARTH_DISTANCE_M = 20_100_000.0
# Slack added to the grid cell size to absorb floating-point rounding.
_CELL_SLACK_M = 1e-3
# Candidate pairs are distance-checked in batches of this size.
_BATCH = 100_000

_GEOD = _Geod(ellps="WGS84") if _Geod is not None else None

# The 13 "forward" neighbours of a cell: every unordered pair of distinct
# adjacent cells is visited exactly once when each cell looks only forward.
_FORWARD_OFFSETS: Tuple[Tuple[int, int, int], ...] = tuple(
    (dx, dy, dz)
    for dx in (-1, 0, 1)
    for dy in (-1, 0, 1)
    for dz in (-1, 0, 1)
    if (dx, dy, dz) > (0, 0, 0)
)


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
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]


def _parse_points(points: Iterable[Sequence[float]]) -> Tuple[List[float], List[float]]:
    lons: List[float] = []
    lats: List[float] = []
    for idx, p in enumerate(points):
        try:
            lon, lat = p
            lon = float(lon)
            lat = float(lat)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"point {idx} must be a (lon, lat) pair of numbers, got {p!r}") from exc
        if not (math.isfinite(lon) and math.isfinite(lat)):
            raise ValueError(f"point {idx} has a non-finite coordinate: {p!r}")
        if not -90.0 <= lat <= 90.0:
            raise ValueError(f"point {idx} has latitude {lat!r} outside [-90, 90]")
        lons.append(lon)
        lats.append(lat)
    return lons, lats


def _parse_threshold(max_distance_m: float) -> float:
    try:
        threshold = float(max_distance_m)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"max_distance_m must be a number, got {max_distance_m!r}") from exc
    if math.isnan(threshold) or threshold < 0.0:
        raise ValueError(f"max_distance_m must be non-negative, got {max_distance_m!r}")
    return threshold


def _ecef(lon_deg: float, lat_deg: float) -> Tuple[float, float, float]:
    """Earth-centred Cartesian coordinates on the same surface used for distances."""
    lam = math.radians(lon_deg)
    phi = math.radians(lat_deg)
    cphi = math.cos(phi)
    sphi = math.sin(phi)
    if _GEOD is not None:
        n = _WGS84_A / math.sqrt(1.0 - _WGS84_E2 * sphi * sphi)
        return (n * cphi * math.cos(lam), n * cphi * math.sin(lam), n * (1.0 - _WGS84_E2) * sphi)
    return (_SPHERE_R * cphi * math.cos(lam), _SPHERE_R * cphi * math.sin(lam), _SPHERE_R * sphi)


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = p2 - p1
    dlam = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2.0) ** 2
    return 2.0 * _SPHERE_R * math.asin(min(1.0, math.sqrt(h)))


def _distances_m(
    lons1: Sequence[float], lats1: Sequence[float], lons2: Sequence[float], lats2: Sequence[float]
) -> Sequence[float]:
    """Element-wise surface distance in metres between two point sequences."""
    if _GEOD is not None:
        _, _, dist = _GEOD.inv(list(lons1), list(lats1), list(lons2), list(lats2))
        return dist
    return [_haversine_m(a, b, c, d) for a, b, c, d in zip(lons1, lats1, lons2, lats2)]


def cluster_points_m(points: Iterable[Sequence[float]], max_distance_m: float) -> List[int]:
    """Single-linkage clustering of WGS84 ``(lon, lat)`` points by distance.

    Two points belong to the same cluster whenever they are within
    ``max_distance_m`` metres (inclusive) of each other, directly or through a
    chain of intermediate points.  An isolated point forms its own cluster.

    Args:
        points: Iterable of ``(lon, lat)`` pairs in decimal degrees (WGS84).
        max_distance_m: Non-negative linkage threshold in metres.

    Returns:
        One integer label per input point, in input order.  Labels are
        ``0, 1, 2, ...`` assigned in order of each cluster's first appearance.

    Raises:
        ValueError: on malformed points, latitudes outside [-90, 90],
            non-finite coordinates, or a negative / NaN threshold.
        TypeError: if ``max_distance_m`` is not a number.

    Complexity is roughly O(n + p) where p is the number of point pairs that
    fall in the same or neighbouring grid cells of size ``max_distance_m``;
    for data that is sparse relative to the threshold this is close to linear.
    """
    lons, lats = _parse_points(points)
    threshold = _parse_threshold(max_distance_m)
    n = len(lons)
    if n == 0:
        return []
    if threshold >= _MAX_EARTH_DISTANCE_M:  # also covers +inf
        return [0] * n

    uf = _UnionFind(n)

    # Bucket points into cubic cells slightly larger than the threshold.  Any
    # pair with chord <= threshold shares a cell or sits in adjacent cells.
    cell = threshold + _CELL_SLACK_M
    grid: Dict[Tuple[int, int, int], List[int]] = {}
    for i in range(n):
        x, y, z = _ecef(lons[i], lats[i])
        key = (math.floor(x / cell), math.floor(y / cell), math.floor(z / cell))
        grid.setdefault(key, []).append(i)

    pending_a: List[int] = []
    pending_b: List[int] = []

    def flush() -> None:
        if not pending_a:
            return
        dist = _distances_m(
            [lons[i] for i in pending_a],
            [lats[i] for i in pending_a],
            [lons[j] for j in pending_b],
            [lats[j] for j in pending_b],
        )
        for i, j, d in zip(pending_a, pending_b, dist):
            if d <= threshold:
                uf.union(i, j)
        pending_a.clear()
        pending_b.clear()

    find = uf.find
    for key, members in grid.items():
        # Pairs inside this cell.
        for a_pos in range(len(members)):
            i = members[a_pos]
            for b_pos in range(a_pos + 1, len(members)):
                j = members[b_pos]
                if find(i) != find(j):
                    pending_a.append(i)
                    pending_b.append(j)
            if len(pending_a) >= _BATCH:
                flush()
        # Pairs between this cell and each forward neighbour.
        kx, ky, kz = key
        for dx, dy, dz in _FORWARD_OFFSETS:
            other = grid.get((kx + dx, ky + dy, kz + dz))
            if other is None:
                continue
            for i in members:
                for j in other:
                    if find(i) != find(j):
                        pending_a.append(i)
                        pending_b.append(j)
                if len(pending_a) >= _BATCH:
                    flush()
    flush()

    labels = [0] * n
    label_of_root: Dict[int, int] = {}
    for i in range(n):
        root = find(i)
        label = label_of_root.get(root)
        if label is None:
            label = len(label_of_root)
            label_of_root[root] = label
        labels[i] = label
    return labels