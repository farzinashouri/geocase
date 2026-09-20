```python
"""Project a WGS84 (EPSG:4326) LineString into a projected CRS, following the
geodesic course between consecutive vertices.

The input line's segments are interpreted as geodesics on the WGS84 ellipsoid
(the shortest path between the two endpoints), not as straight lines in
lon/lat space.  Because a straight segment in the target CRS is generally not
the image of a geodesic, each input segment is densified with intermediate
points sampled along the geodesic before the coordinates are transformed.  The
sampling step is chosen so that the chord between successive output vertices
stays well within 25 km of the true projected course.
"""

from __future__ import annotations

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

__all__ = ["project_line"]

# Maximum geodesic distance (metres) between successive densified vertices.
#
# The sagitta of a chord of length L on a sphere of radius R is about
# L**2 / (8 * R), so staying within 25 km of the geodesic would already be
# satisfied by L of roughly 1100 km.  A projection can stretch distances
# considerably relative to the ellipsoid, so we densify an order of magnitude
# more finely than that bound requires.
_MAX_SEGMENT_M = 10_000.0

# Geodesic computations are done on WGS84, the datum of the input coordinates.
_GEOD = Geod(ellps="WGS84")


def _densify(lon1, lat1, lon2, lat2):
    """Return intermediate (lon, lat) points strictly between the endpoints."""
    _, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
    if not dist or dist != dist or dist <= _MAX_SEGMENT_M:
        return []
    npts = int(dist // _MAX_SEGMENT_M)
    return _GEOD.npts(lon1, lat1, lon2, lat2, npts)


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Project ``line`` from EPSG:4326 to ``dst_epsg`` along geodesic courses.

    Parameters
    ----------
    line:
        A shapely ``LineString`` whose coordinates are (longitude, latitude)
        in EPSG:4326.
    dst_epsg:
        EPSG code of the projected CRS to transform into.

    Returns
    -------
    LineString
        The projected line, densified so that it traces the geodesic path
        between each pair of consecutive input vertices.
    """
    if not isinstance(line, LineString):
        raise TypeError("line must be a shapely LineString")
    if line.is_empty:
        raise ValueError("line must not be empty")

    coords = [(float(x), float(y)) for x, y in ((c[0], c[1]) for c in line.coords)]

    dense = [coords[0]]
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        dense.extend(_densify(lon1, lat1, lon2, lat2))
        dense.append((lon2, lat2))

    transformer = Transformer.from_crs(
        CRS.from_epsg(4326), CRS.from_epsg(dst_epsg), always_xy=True
    )
    xs, ys = transformer.transform(
        [p[0] for p in dense], [p[1] for p in dense], errcheck=False
    )

    out = []
    for x, y in zip(xs, ys):
        # Drop points the projection cannot represent (outside its domain).
        if x != x or y != y or x in (float("inf"), float("-inf")):
            continue
        if out and out[-1] == (x, y):
            continue
        out.append((x, y))

    if len(out) < 2:
        raise ValueError(
            f"line could not be projected into EPSG:{dst_epsg}: "
            "fewer than two vertices are representable in that CRS"
        )
    return LineString(out)
```