Bash is gated in this session, so the module below is reasoned-through rather than executed here.

```python
"""Single-linkage clustering of WGS84 lon/lat points under a metric threshold.

Two points join the same cluster when the WGS84 geodesic distance between them
is at most ``max_distance_m``; a cluster is a connected component of that
relation, so membership can be transitive through intermediate points.

The neighbour search runs on a ball tree with the haversine (spherical) metric,
which is only an approximation of the ellipsoid, so it is used purely as a
candidate filter with a radius deliberately inflated past the true threshold.
Every surviving candidate pair is then measured exactly with ``pyproj.Geod``,
which is what decides cluster membership.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np
from pyproj import Geod
from sklearn.neighbors import BallTree

__all__ = ["cluster_points_m"]

_GEOD = Geod(ellps="WGS84")

# The smallest radius of curvature of the WGS84 ellipsoid is 6_335_439 m (the
# meridional radius at the equator).  Converting a metric threshold to an angle
# with a radius below that can only over-state the angle, so the spherical query
# is guaranteed to be a superset of the true geodesic neighbourhood.  The extra
# slack also absorbs the error of feeding geodetic latitudes to the haversine
# metric, which matters for thresholds large enough to be non-local.
_SUB_MINIMAL_EARTH_RADIUS_M = 6.3e6

# Rows of the neighbour query handled at a time, to bound peak memory.
_QUERY_BLOCK = 4096


def cluster_points_m(
    points: Iterable[tuple[float, float]], max_distance_m: float
) -> list[int]:
    """Label ``points`` with single-linkage cluster ids.

    Args:
        points: ``(lon, lat)`` pairs in WGS84 decimal degrees.
        max_distance_m: linkage threshold in meters; two points are linked when
            the geodesic distance between them is ``<= max_distance_m``.

    Returns:
        One integer label per input point, in input order, numbered 0, 1, 2, ...
        in order of first appearance.  An isolated point gets a label of its own.

    Raises:
        ValueError: if ``points`` is not shaped as ``(n, 2)`` finite lon/lat
            pairs, or if ``max_distance_m`` is negative or not finite.

    >>> cluster_points_m([(0.0, 0.0), (0.0005, 0.0), (10.0, 10.0)], 100.0)
    [0, 0, 1]
    """
    lon, lat = _to_lon_lat_arrays(points)
    threshold_m = float(max_distance_m)
    if not np.isfinite(threshold_m) or threshold_m < 0.0:
        raise ValueError(
            "max_distance_m must be a finite, non-negative number of meters, "
            f"got {max_distance_m!r}"
        )

    n = lon.size
    if n <= 1:
        return [0] * n

    # The haversine metric wants (lat, lon) in radians.  Wrapping longitudes
    # into [-180, 180) leaves distances untouched and keeps the tree's bounding
    # spheres tight for inputs that straddle the antimeridian.
    wrapped_lon = (lon + 180.0) % 360.0 - 180.0
    coords = np.radians(np.column_stack((lat, wrapped_lon)))
    tree = BallTree(coords, metric="haversine")
    angular_radius = min(np.pi, threshold_m / _SUB_MINIMAL_EARTH_RADIUS_M)

    parent = list(range(n))
    for start in range(0, n, _QUERY_BLOCK):
        block = coords[start : start + _QUERY_BLOCK]
        left, right = _forward_pairs(tree.query_radius(block, r=angular_radius), start)
        if left.size == 0:
            continue
        _, _, distance_m = _GEOD.inv(lon[left], lat[left], lon[right], lat[right])
        linked = np.asarray(distance_m) <= threshold_m
        for i, j in zip(left[linked].tolist(), right[linked].tolist()):
            _union(parent, i, j)

    return _first_appearance_labels(parent, n)


def _to_lon_lat_arrays(points) -> tuple[np.ndarray, np.ndarray]:
    """Split ``points`` into validated contiguous lon and lat degree arrays."""
    if not isinstance(points, (Sequence, np.ndarray)):
        points = list(points)
    try:
        array = np.asarray(points, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError("points must be a sequence of (lon, lat) number pairs") from exc

    if array.size == 0:
        empty = np.empty(0, dtype=np.float64)
        return empty, empty.copy()
    if array.ndim != 2 or array.shape[1] != 2:
        raise ValueError(
            f"points must have shape (n, 2) of (lon, lat) pairs, got {array.shape}"
        )
    if not np.isfinite(array).all():
        raise ValueError("points must contain finite longitude/latitude values")

    lat = np.ascontiguousarray(array[:, 1])
    if np.any(np.abs(lat) > 90.0):
        raise ValueError("latitudes must lie within [-90, 90] degrees")
    return np.ascontiguousarray(array[:, 0]), lat


def _forward_pairs(
    neighbourhoods: Iterable[np.ndarray], offset: int
) -> tuple[np.ndarray, np.ndarray]:
    """Collect candidate ``(i, j)`` index pairs with ``i < j`` from one block.

    Keeping only ``j > i`` deduplicates the symmetric neighbour relation: every
    candidate pair shows up in the row of its lower index, and every row is
    queried exactly once across all blocks.
    """
    lefts: list[np.ndarray] = []
    rights: list[np.ndarray] = []
    for row, neighbours in enumerate(neighbourhoods):
        i = offset + row
        ahead = neighbours[neighbours > i]
        if ahead.size:
            lefts.append(np.full(ahead.size, i, dtype=np.intp))
            rights.append(ahead.astype(np.intp, copy=False))
    if not lefts:
        empty = np.empty(0, dtype=np.intp)
        return empty, empty.copy()
    return np.concatenate(lefts), np.concatenate(rights)


def _find(parent: list[int], i: int) -> int:
    """Return the representative of ``i``, compressing the path to it."""
    root = i
    while parent[root] != root:
        root = parent[root]
    while parent[i] != root:
        parent[i], i = root, parent[i]
    return root


def _union(parent: list[int], a: int, b: int) -> None:
    """Merge the components of ``a`` and ``b``, keeping the lower index as root."""
    root_a, root_b = _find(parent, a), _find(parent, b)
    if root_a != root_b:
        parent[max(root_a, root_b)] = min(root_a, root_b)


def _first_appearance_labels(parent: list[int], n: int) -> list[int]:
    """Number the components 0, 1, 2, ... in order of first appearance."""
    labels = [0] * n
    label_of_root: dict[int, int] = {}
    for i in range(n):
        root = _find(parent, i)
        label = label_of_root.get(root)
        if label is None:
            label = len(label_of_root)
            label_of_root[root] = label
        labels[i] = label
    return labels
```