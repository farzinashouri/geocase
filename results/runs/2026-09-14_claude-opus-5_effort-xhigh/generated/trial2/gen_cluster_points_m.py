"""Single-linkage clustering of WGS84 lon/lat points under a metric threshold.

Two points join the same cluster when the geodesic (ellipsoidal) distance
between them is at most ``max_distance_m``, transitively through chains of
intermediate points.  Candidate neighbours are found with a KD-tree over
geocentric (ECEF) coordinates: the straight-line chord between two points on
the ellipsoid is never longer than the geodesic joining them, so a chord-radius
query returns a superset of the true neighbours, which is then filtered with
exact geodesic distances.

Importing this module performs no work; the PROJ transformer and geodesic
helper are built lazily on first use.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable, List, Sequence, Tuple

import numpy as np
from pyproj import Geod, Transformer
from sklearn.neighbors import KDTree

__all__ = ["cluster_points_m"]

_WGS84_GEOGRAPHIC = "EPSG:4326"  # lon/lat degrees
_WGS84_GEOCENTRIC = "EPSG:4978"  # earth-centred, earth-fixed metres

# Bound peak memory on dense inputs: query the tree in row blocks and verify
# candidate pairs in batches rather than materialising every pair at once.
_QUERY_BLOCK = 4096
_PAIR_CHUNK = 100_000


@lru_cache(maxsize=1)
def _ecef_transformer() -> Transformer:
    return Transformer.from_crs(_WGS84_GEOGRAPHIC, _WGS84_GEOCENTRIC, always_xy=True)


@lru_cache(maxsize=1)
def _geod() -> Geod:
    return Geod(ellps="WGS84")


def _as_lonlat_array(points: Iterable[Sequence[float]]) -> np.ndarray:
    """Validate the input and return it as an ``(n, 2)`` float array."""
    try:
        arr = np.asarray(points, dtype=float)
    except (TypeError, ValueError) as exc:  # ragged or non-numeric input
        raise ValueError("points must be a sequence of (lon, lat) pairs") from exc
    if arr.size == 0:
        return np.empty((0, 2), dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("points must be a sequence of (lon, lat) pairs")
    if not np.isfinite(arr).all():
        raise ValueError("points must contain finite lon/lat values")
    if np.any(np.abs(arr[:, 1]) > 90.0):
        raise ValueError("latitudes must lie within [-90, 90]")
    return arr


def _find(parent: List[int], i: int) -> int:
    root = i
    while parent[root] != root:
        root = parent[root]
    while parent[i] != root:  # path compression
        parent[i], i = root, parent[i]
    return root


def _union(parent: List[int], rank: List[int], a: int, b: int) -> None:
    ra, rb = _find(parent, a), _find(parent, b)
    if ra == rb:
        return
    if rank[ra] < rank[rb]:
        ra, rb = rb, ra
    parent[rb] = ra
    if rank[ra] == rank[rb]:
        rank[ra] += 1


def _union_close_pairs(
    parent: List[int],
    rank: List[int],
    lon: np.ndarray,
    lat: np.ndarray,
    i_idx: np.ndarray,
    j_idx: np.ndarray,
    max_distance_m: float,
) -> None:
    """Merge the candidate pairs whose geodesic distance is within threshold."""
    _, _, dist = _geod().inv(lon[i_idx], lat[i_idx], lon[j_idx], lat[j_idx])
    close = np.asarray(dist, dtype=float) <= max_distance_m
    for i, j in zip(i_idx[close].tolist(), j_idx[close].tolist()):
        _union(parent, rank, i, j)


def cluster_points_m(
    points: Iterable[Sequence[float]], max_distance_m: float
) -> List[int]:
    """Single-linkage cluster WGS84 ``(lon, lat)`` points by a metre threshold.

    Parameters
    ----------
    points:
        Sequence of ``(lon, lat)`` pairs in decimal degrees (WGS84).
    max_distance_m:
        Linkage threshold in metres.  Two points are directly linked when the
        geodesic distance between them is ``<= max_distance_m``; clustering is
        transitive over such links.  A negative threshold links nothing.

    Returns
    -------
    list of int
        One label per input point, numbered ``0, 1, 2, ...`` in order of each
        cluster's first appearance in ``points``.
    """
    coords = _as_lonlat_array(points)
    n = coords.shape[0]
    if n == 0:
        return []

    max_distance_m = float(max_distance_m)
    if np.isnan(max_distance_m):
        raise ValueError("max_distance_m must not be NaN")
    if n == 1 or max_distance_m < 0.0:
        return list(range(n))

    lon = np.ascontiguousarray(coords[:, 0])
    lat = np.ascontiguousarray(coords[:, 1])

    x, y, z = _ecef_transformer().transform(lon, lat, np.zeros(n, dtype=float))
    xyz = np.column_stack((x, y, z))

    parent = list(range(n))
    rank = [0] * n

    tree = KDTree(xyz)
    left: List[np.ndarray] = []
    right: List[np.ndarray] = []
    pending = 0

    for start in range(0, n, _QUERY_BLOCK):
        block = xyz[start : start + _QUERY_BLOCK]
        for offset, neighbours in enumerate(tree.query_radius(block, r=max_distance_m)):
            i = start + offset
            js = neighbours[neighbours > i]  # keep each pair once, drop self-match
            if js.size == 0:
                continue
            left.append(np.full(js.size, i, dtype=np.intp))
            right.append(js.astype(np.intp, copy=False))
            pending += js.size
            if pending >= _PAIR_CHUNK:
                _union_close_pairs(
                    parent,
                    rank,
                    lon,
                    lat,
                    np.concatenate(left),
                    np.concatenate(right),
                    max_distance_m,
                )
                left, right, pending = [], [], 0

    if pending:
        _union_close_pairs(
            parent,
            rank,
            lon,
            lat,
            np.concatenate(left),
            np.concatenate(right),
            max_distance_m,
        )

    labels: List[int] = []
    first_seen: dict = {}
    for i in range(n):
        root = _find(parent, i)
        label = first_seen.get(root)
        if label is None:
            label = len(first_seen)
            first_seen[root] = label
        labels.append(label)
    return labels