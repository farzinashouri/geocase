```python
"""Buffer WGS84 (EPSG:4326) geometries by a distance in meters.

The geometry is projected into an azimuthal equidistant (AEQD) coordinate
system centred on the geometry itself, buffered there, and projected back.
AEQD preserves distance along every line through its origin, so for buffers
that are small compared to the size of the Earth this is accurate anywhere on
the globe, including at the poles and across the antimeridian.
"""

from __future__ import annotations

import math

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

__all__ = ["buffer_m"]

_WGS84 = CRS.from_epsg(4326)

# Semi-major axis / flattening of WGS84, used for the AEQD sphere radius.
_A = 6378137.0
_F = 1 / 298.257223563
_B = _A * (1 - _F)


def _centre(geom: BaseGeometry) -> tuple[float, float]:
    """Return a (lon, lat) origin for the projection.

    The mean is taken on the unit sphere rather than in lon/lat space, so a
    geometry straddling the antimeridian still gets a sensible centre instead
    of one on the opposite side of the planet.
    """
    x = y = z = 0.0
    n = 0
    for lon, lat in _coords(geom):
        lam = math.radians(lon)
        phi = math.radians(lat)
        cos_phi = math.cos(phi)
        x += cos_phi * math.cos(lam)
        y += cos_phi * math.sin(lam)
        z += math.sin(phi)
        n += 1
    if n == 0:
        raise ValueError("cannot buffer an empty geometry")
    x /= n
    y /= n
    z /= n
    hyp = math.hypot(x, y)
    if hyp < 1e-12 and abs(z) < 1e-12:
        # Vertices cancel out (e.g. antipodal points); fall back to (0, 0).
        return 0.0, 0.0
    return math.degrees(math.atan2(y, x)), math.degrees(math.atan2(z, hyp))


def _coords(geom: BaseGeometry):
    """Yield every (x, y) vertex of an arbitrarily nested geometry."""
    if geom.is_empty:
        return
    geom_type = geom.geom_type
    if geom_type in ("Point", "LineString", "LinearRing"):
        for xy in geom.coords:
            yield xy[0], xy[1]
    elif geom_type == "Polygon":
        yield from _coords(geom.exterior)
        for ring in geom.interiors:
            yield from _coords(ring)
    else:  # Multi* and GeometryCollection
        for part in geom.geoms:
            yield from _coords(part)


def buffer_m(geom: BaseGeometry, distance_m: float, **kwargs) -> BaseGeometry:
    """Buffer a lon/lat geometry by ``distance_m`` metres.

    Parameters
    ----------
    geom:
        A shapely geometry with coordinates in EPSG:4326 (lon, lat order).
    distance_m:
        Buffer distance in metres. Negative values erode the geometry.
    **kwargs:
        Passed through to ``shapely.geometry.base.BaseGeometry.buffer``
        (``quad_segs``, ``cap_style``, ``join_style``, ...). Note that these
        act in the projected plane.

    Returns
    -------
    A shapely geometry in EPSG:4326.

    Notes
    -----
    Longitudes of the result are *not* wrapped into [-180, 180]: a buffer that
    crosses the antimeridian is returned as a single continuous ring with
    longitudes running past ±180, rather than being silently torn in two.
    Callers that need wrapped output should split the result on the
    antimeridian themselves.
    """
    if geom.is_empty:
        return geom

    lon0, lat0 = _centre(geom)
    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0!r} +lon_0={lon0!r} "
        f"+a={_A!r} +b={_B!r} +units=m +no_defs"
    )
    fwd = Transformer.from_crs(_WGS84, aeqd, always_xy=True)
    inv = Transformer.from_crs(aeqd, _WGS84, always_xy=True)

    projected = transform(fwd.transform, geom)
    buffered = projected.buffer(distance_m, **kwargs)
    if buffered.is_empty:
        return buffered

    result = transform(inv.transform, buffered)
    return _unwrap(result, lon0)


def _unwrap(geom: BaseGeometry, lon0: float) -> BaseGeometry:
    """Shift longitudes so the geometry stays continuous around ``lon0``.

    The inverse projection returns longitudes in [-180, 180], which splits any
    shape spanning the antimeridian. Rewriting each vertex to the branch
    nearest the projection centre restores a single connected outline.
    """

    def _shift(x, y, z=None):
        try:
            xs = [v - 360.0 * round((v - lon0) / 360.0) for v in x]
        except TypeError:  # scalar
            xs = x - 360.0 * round((x - lon0) / 360.0)
        return (xs, y) if z is None else (xs, y, z)

    return transform(_shift, geom)
```