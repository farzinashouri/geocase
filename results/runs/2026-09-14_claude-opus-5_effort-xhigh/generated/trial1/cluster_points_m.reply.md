```python
"""Single-linkage clustering of WGS84 lon/lat points by geodesic distance.

Two points fall in the same cluster when the WGS84 geodesic ("great circle on
the ellipsoid") distance between them is at most a given threshold in meters,
either directly or transitively through intermediate points.
"""

from __future__ import annotations

import functools
from typing import Sequence

import numpy as np
from pyproj import Geod, Transformer
from sklearn.neighbors import KDTree

__all__ = ["cluster_points_m"]

# Number of query points per neighbour lookup, so a dense input never
# materialises all O(n^2) candidate pairs at once.
_QUERY_CHUNK = 1024


@functools.lru_cache(maxsize=1)
def _geod() -> Geod:
    return Geod(ellps="WGS84")


@functools.lru_cache(maxsize=1)
def _to_ecef() -> Transformer:
    # EPSG:4978 is WGS84 geocentric (ECEF) — same ellipsoid as _geod(), so the
    # two agree about where the points are.
    return Transformer.from_crs("EPSG:4326", "EPSG:4978", always_xy=True)


class _DisjointSet:
    """Union-find over ``range(n)`` with path compression and union by rank."""

    __slots__ = ("_parent", "_rank")

    def __init__(self, n: int) -> None:
        self._parent = list(range(n))
        self._rank = [0] * n

    def find(self, i: int) -> int:
        parent = self._parent
        root = i
        while parent[root] != root:
            root = parent[root]
        while parent[i] != root:
            parent[i], i = root, parent[i]
        return root

    def union(self, i: int, j: int) -> None:
        root_i, root_j = self.find(i), self.find(j)
        if root_i == root_j:
            return
        rank = self._rank
        if rank[root_i] < rank[root_j]:
            root_i, root_j = root_j, root_i
        self._parent[root_j] = root_i
        if rank[root_i] == rank[root_j]:
            rank[root_i] += 1


def _as_coords(points) -> np.ndarray:
    try:
        coords = np.asarray(points, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("points must be a sequence of (lon, lat) pairs") from exc
    if coords.size == 0:
        return coords.reshape(0, 2)
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError("points must be a sequence of (lon, lat) pairs")
    if not np.isfinite(coords).all():
        raise ValueError("points must contain finite lon/lat values")
    if np.any(np.abs(coords[:, 1]) > 90.0):
        raise ValueError("latitudes must lie within [-90, 90]")
    return coords


def cluster_points_m(
    points: Sequence[tuple[float, float]], max_distance_m: float
) -> list[int]:
    """Single-linkage cluster WGS84 points on a geodesic distance threshold.

    Args:
        points: Sequence of ``(lon, lat)`` pairs in degrees (WGS84).
        max_distance_m: Linkage threshold in meters. Two points are linked when
            the geodesic distance between them is ``<= max_distance_m``; points
            linked directly or through a chain share a cluster. Must be finite
            and non-negative; ``0`` links only coincident points.

    Returns:
        One integer label per input point, in input order, numbered ``0, 1,
        2, ...`` in order of first appearance. An isolated point gets its own
        label.

    Raises:
        ValueError: If ``points`` is not a sequence of finite ``(lon, lat)``
            pairs with ``lat`` in ``[-90, 90]``, or if ``max_distance_m`` is
            negative or not finite.
    """
    coords = _as_coords(points)
    n = coords.shape[0]

    threshold = float(max_distance_m)
    if not np.isfinite(threshold) or threshold < 0.0:
        raise ValueError("max_distance_m must be finite and non-negative")

    if n == 0:
        return []
    if n == 1:
        return [0]

    lon = np.ascontiguousarray(coords[:, 0])
    lat = np.ascontiguousarray(coords[:, 1])

    # Candidate pairs come from a Euclidean radius search in ECEF. The straight
    # 3D chord between two surface points is never longer than a path along the
    # surface, so every geodesically-close pair is also chord-close: searching
    # at the same radius yields a superset of the true edges, which the exact
    # geodesic check below then filters. The slack absorbs rounding for pairs
    # sitting exactly on the threshold.
    xyz = np.column_stack(_to_ecef().transform(lon, lat, np.zeros(n)))
    radius = threshold * (1.0 + 1e-9) + 1e-6
    tree = KDTree(xyz)

    clusters = _DisjointSet(n)
    for start in range(0, n, _QUERY_CHUNK):
        stop = min(start + _QUERY_CHUNK, n)
        neighbours = tree.query_radius(xyz[start:stop], r=radius)

        left = np.repeat(
            np.arange(start, stop), [len(found) for found in neighbours]
        )
        right = np.concatenate(neighbours)
        # The search is symmetric and includes each query point itself; keeping
        # only right > left visits every unordered pair exactly once overall.
        keep = right > left
        left, right = left[keep], right[keep]
        if left.size == 0:
            continue

        # Edges inside an existing cluster cannot change the partition, so skip
        # their (comparatively expensive) geodesic evaluation.
        unlinked = np.fromiter(
            (
                clusters.find(i) != clusters.find(j)
                for i, j in zip(left.tolist(), right.tolist())
            ),
            dtype=bool,
            count=left.size,
        )
        left, right = left[unlinked], right[unlinked]
        if left.size == 0:
            continue

        *_, distances = _geod().inv(lon[left], lat[left], lon[right], lat[right])
        within = np.asarray(distances, dtype=float) <= threshold
        for i, j in zip(left[within].tolist(), right[within].tolist()):
            clusters.union(i, j)

    labels: list[int] = []
    label_of_root: dict[int, int] = {}
    for i in range(n):
        root = clusters.find(i)
        label = label_of_root.get(root)
        if label is None:
            label = len(label_of_root)
            label_of_root[root] = label
        labels.append(label)
    return labels
```