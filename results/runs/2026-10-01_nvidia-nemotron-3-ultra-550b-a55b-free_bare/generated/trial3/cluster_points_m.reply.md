```python
import numpy as np
from sklearn.neighbors import KDTree
import pyproj


class _DSU:
    """Disjoint Set Union (Union-Find) with path compression and union by rank."""
    __slots__ = ("parent", "rank")

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        xr = self.find(x)
        yr = self.find(y)
        if xr == yr:
            return
        if self.rank[xr] < self.rank[yr]:
            self.parent[xr] = yr
        elif self.rank[xr] > self.rank[yr]:
            self.parent[yr] = xr
        else:
            self.parent[yr] = xr
            self.rank[xr] += 1


def cluster_points_m(points, max_distance_m):
    """
    Group points into single-linkage clusters based on a geodesic distance threshold.

    Parameters
    ----------
    points : list[tuple[float, float]]
        List of (longitude, latitude) coordinates in WGS84 (EPSG:4326).
    max_distance_m : float
        Maximum distance in meters for two points to be considered connected.

    Returns
    -------
    list[int]
        Cluster label for each input point. Labels are 0, 1, 2, ... assigned in
        order of first appearance of each cluster in the input list.
    """
    if not points:
        return []

    n = len(points)
    pts = np.asarray(points, dtype=np.float64)
    lons, lats = pts[:, 0], pts[:, 1]

    # Convert to ECEF (EPSG:4978) for fast chord-distance neighbour search.
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:4978", always_xy=True)
    x, y, z = transformer.transform(lons, lats)
    ecef = np.column_stack((x, y, z))

    # KDTree on chord distance (Euclidean in ECEF). Chord distance <= geodesic distance,
    # so querying with max_distance_m (+ tiny epsilon) guarantees no false negatives.
    tree = KDTree(ecef, metric="euclidean")
    pairs_set = tree.query_pairs(r=max_distance_m + 1e-9)

    if not pairs_set:
        return list(range(n))

    pairs = np.fromiter(pairs_set, dtype=np.intp, count=len(pairs_set) * 2).reshape(-1, 2)

    # Exact geodesic filter using WGS84 ellipsoid.
    geod = pyproj.Geod(ellps="WGS84")
    i_idx, j_idx = pairs[:, 0], pairs[:, 1]
    _, _, dists = geod.inv(lons[i_idx], lats[i_idx], lons[j_idx], lats[j_idx])
    valid_pairs = pairs[dists <= max_distance_m]

    # Union-Find to build clusters.
    dsu = _DSU(n)
    for i, j in valid_pairs:
        dsu.union(i, j)

    # Assign labels in order of first appearance.
    root_to_label = {}
    labels = []
    for idx in range(n):
        root = dsu.find(idx)
        if root not in root_to_label:
            root_to_label[root] = len(root_to_label)
        labels.append(root_to_label[root])

    return labels
```