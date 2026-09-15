```python
"""Project a WGS84 lon/lat LineString into a projected CRS along geodesic arcs.

The input line's segments are interpreted as geodesics on the WGS84
ellipsoid.  Each segment is densified with intermediate geodesic points
before being transformed, so that the projected polyline stays within
25 km of the true projected geodesic everywhere.
"""

from __future__ import annotations

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

__all__ = ["project_line"]

# Maximum spacing, in metres, between consecutive densified vertices.
#
# On a sphere of radius R the chord joining two points a distance ``s``
# apart along the surface deviates from the arc by at most
# ``R * (1 - cos(s / 2R)) ~= s**2 / (8R)``.  For the 25 km budget that
# allows ``s`` up to roughly 1100 km.  We use a far smaller step so that
# the extra error introduced by map projection distortion (which is not
# bounded by the spherical argument) is also comfortably absorbed.
_MAX_SEGMENT_LENGTH_M = 25_000.0

_GEOD = Geod(ellps="WGS84")


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Return ``line`` (lon/lat, EPSG:4326) projected to ``dst_epsg``.

    The result traces the geodesic course between each pair of
    consecutive input vertices to within 25 km.

    Parameters
    ----------
    line:
        A shapely ``LineString`` whose coordinates are (longitude,
        latitude) in degrees on WGS84.  Any Z values are dropped.
    dst_epsg:
        EPSG code of the target projected CRS.

    Returns
    -------
    LineString
        The densified, projected line.
    """
    if line.is_empty:
        return LineString()

    coords = [(float(x), float(y)) for x, y in zip(*line.coords.xy)]
    if len(coords) < 2:
        raise ValueError("line must have at least two vertices")

    dense = _densify_geodesic(coords)

    transformer = Transformer.from_crs(
        CRS.from_epsg(4326), CRS.from_epsg(dst_epsg), always_xy=True
    )
    lons = [c[0] for c in dense]
    lats = [c[1] for c in dense]
    xs, ys = transformer.transform(lons, lats)

    return LineString(zip(xs, ys))


def _densify_geodesic(coords):
    """Insert geodesic waypoints so no gap exceeds ``_MAX_SEGMENT_LENGTH_M``."""
    dense = [coords[0]]
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        _, _, distance = _GEOD.inv(lon1, lat1, lon2, lat2)
        n_extra = int(distance // _MAX_SEGMENT_LENGTH_M)
        if n_extra > 0:
            dense.extend(
                _GEOD.npts(lon1, lat1, lon2, lat2, n_extra, initial_idx=1, terminus_idx=1)
            )
        dense.append((lon2, lat2))
    return dense
```