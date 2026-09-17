Here is the module: pyproj's WGS84 geodesic for pairwise distances, union-find for single-linkage, labels assigned in order of first appearance.

```python
"""Single-linkage clustering of WGS84 (lon, lat) points by geodesic distance."""

from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np
from pyproj import Geod

Point = Tuple[float, float]


def _find(parent: List[int], i: int) -> int:
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def _union(parent: List[int], a: int, b: int) -> None:
    ra, rb = _find(parent, a), _find(parent, b)
    if ra != rb:
        parent[rb] = ra


def cluster_points_m(points: Sequence[Point], max_distance_m: float) -> List[int]:
    """Group points that are within ``max_distance_m`` meters of each other.

    Two points share a cluster if they are within the threshold directly or via a
    chain of intermediate points (single linkage). Returns one integer label per
    input point, numbered 0, 1, 2, ... in order of first appearance.
    """
    n = len(points)
    if n == 0:
        return []
    if max_distance_m < 0:
        raise ValueError("max_distance_m must be non-negative")

    lons = np.asarray([p[0] for p in points], dtype=float)
    lats = np.asarray([p[1] for p in points], dtype=float)
    geod = Geod(ellps="WGS84")
    parent = list(range(n))

    for i in range(n - 1):
        m = n - i - 1
        _, _, dist = geod.inv(
            np.full(m, lons[i]), np.full(m, lats[i]), lons[i + 1:], lats[i + 1:]
        )
        for j in np.nonzero(np.asarray(dist) <= max_distance_m)[0]:
            _union(parent, i, i + 1 + int(j))

    labels: List[int] = []
    root_to_label: dict = {}
    for i in range(n):
        root = _find(parent, i)
        if root not in root_to_label:
            root_to_label[root] = len(root_to_label)
        labels.append(root_to_label[root])
    return labels
```