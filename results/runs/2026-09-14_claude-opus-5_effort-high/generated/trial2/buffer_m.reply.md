```python
"""Metre-accurate buffering of geometries whose coordinates are in EPSG:4326.

The trick is to never buffer in degrees.  For every call an azimuthal
equidistant (``aeqd``) projection is created that is centred on the input
geometry; in that projection one map unit is one metre along every ray from
the centre, so ``shapely``'s planar buffer is a true metre buffer.  The result
is projected back to longitude/latitude.

Accuracy notes
--------------
* A buffered ``Point`` is a geodesic circle (exact up to the polygonal
  approximation controlled by ``quad_segs``).
* For extended geometries the distortion grows with the distance between the
  projection centre and the part of the boundary being buffered; it stays
  below roughly 0.1 % for geometries spanning a few hundred kilometres, which
  covers the overwhelming majority of real inputs.
* Results that cross the antimeridian are split and returned as a
  ``MultiPolygon`` with all longitudes inside [-180, 180]; results that cover
  a pole get the pole cap stitched in along latitude +/-90.
* A buffer large enough to reach the antipode of the projection centre
  saturates to the whole globe.

Only the standard library, numpy, shapely and pyproj are used, and importing
this module performs no work beyond defining names.
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.affinity import translate
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.ops import transform as _shapely_transform

__all__ = ["buffer_m"]

# Mean radius of the WGS84 ellipsoid, used for the spherical fallback and for
# deciding when a buffer has swallowed the entire planet.
_MEAN_RADIUS_M = 6371008.7714
_HALF_CIRCUMFERENCE_M = math.pi * _MEAN_RADIUS_M

# Beyond this reach the straight segments of the projected buffer visibly bend
# in longitude/latitude, so the ring is densified before being projected back.
_DENSIFY_REACH_M = 25_000.0

_WORLD = (-180.0, -90.0, 180.0, 90.0)


class _Unprojectable(Exception):
    """Raised internally when the aeqd round trip produces non-finite output."""


@lru_cache(maxsize=256)
def _transformers(lon_0: float, lat_0: float, spherical: bool):
    """Return (forward, inverse) transform callables for a local aeqd CRS."""
    if spherical:
        # A sphere keeps aeqd well defined all the way to the antipode.
        proj = f"+proj=aeqd +lat_0={lat_0!r} +lon_0={lon_0!r} +R={_MEAN_RADIUS_M!r} +units=m +no_defs"
    else:
        proj = f"+proj=aeqd +lat_0={lat_0!r} +lon_0={lon_0!r} +datum=WGS84 +units=m +no_defs"
    local = CRS.from_proj4(proj)
    wgs84 = CRS.from_epsg(4326)
    forward = Transformer.from_crs(wgs84, local, always_xy=True).transform
    inverse = Transformer.from_crs(local, wgs84, always_xy=True).transform
    return forward, inverse


def buffer_m(geom, distance_m, *, quad_segs: int = 16):
    """Buffer an EPSG:4326 geometry by ``distance_m`` metres.

    Parameters
    ----------
    geom
        Any shapely geometry with longitude/latitude coordinates (EPSG:4326).
    distance_m
        Buffer distance in metres.  Negative values erode, as in shapely.
    quad_segs
        Segments per quarter circle used to approximate round joins.

    Returns
    -------
    Polygon or MultiPolygon in EPSG:4326 (empty ``Polygon`` if nothing is left).
    """
    if geom is None:
        raise TypeError("geom must be a shapely geometry, not None")
    distance_m = float(distance_m)
    if not math.isfinite(distance_m):
        raise ValueError("distance_m must be a finite number of metres")
    if geom.is_empty:
        return Polygon()

    coords = shapely.get_coordinates(geom)
    if coords.size == 0:
        return Polygon()
    if not np.isfinite(coords).all():
        raise ValueError("geom contains non-finite coordinates")

    lon_0, lat_0 = _projection_center(coords)

    # The ellipsoidal aeqd solution is the accurate one but degrades near the
    # antipode of its centre; fall back to the sphere only if it misbehaves.
    for spherical in (False, True):
        try:
            return _buffer_once(geom, distance_m, lon_0, lat_0, spherical, quad_segs)
        except _Unprojectable:
            continue
    raise ValueError("geometry and distance cannot be represented in EPSG:4326")


def _buffer_once(geom, distance_m, lon_0, lat_0, spherical, quad_segs):
    forward, inverse = _transformers(lon_0, lat_0, spherical)

    projected = _shapely_transform(forward, geom)
    pxy = shapely.get_coordinates(projected)
    if not np.isfinite(pxy).all():
        raise _Unprojectable("forward projection produced non-finite coordinates")

    reach = float(np.hypot(pxy[:, 0], pxy[:, 1]).max()) + max(distance_m, 0.0)
    if reach >= _HALF_CIRCUMFERENCE_M:
        return shapely.box(*_WORLD)

    buffered = projected.buffer(distance_m, quad_segs=quad_segs)
    if buffered.is_empty:
        return Polygon()
    if reach > _DENSIFY_REACH_M:
        # Straight lines in aeqd are curves in lon/lat: add vertices so the
        # unprojected ring follows them, and so longitude steps stay < 180.
        buffered = shapely.segmentize(buffered, max_segment_length=reach / 100.0)

    parts = []
    for poly in _polygons(buffered):
        shell = _ring_to_polygon(poly.exterior, inverse, forward, lon_0)
        holes = [_ring_to_polygon(r, inverse, forward, lon_0) for r in poly.interiors]
        if holes:
            shell = _valid(shell).difference(shapely.unary_union([_valid(h) for h in holes]))
        parts.append(_valid(shell))

    merged = parts[0] if len(parts) == 1 else shapely.unary_union(parts)
    return _polygonal(_wrap_into_range(merged))


def _projection_center(coords):
    """Pick an aeqd centre, robust to geometries straddling the antimeridian."""
    lons = coords[:, 0]
    lats = coords[:, 1]
    rad = np.radians(lons)
    mean_lon = math.degrees(
        math.atan2(float(np.sin(rad).mean()), float(np.cos(rad).mean()))
    )
    # Unwrap around that mean so min/max are meaningful across the seam.
    unwrapped = mean_lon + _wrap180(lons - mean_lon)
    lon_0 = _wrap180(float(unwrapped.min() + unwrapped.max()) / 2.0)
    lat_0 = float(lats.min() + lats.max()) / 2.0
    return float(lon_0), max(-90.0, min(90.0, lat_0))


def _wrap180(values):
    """Wrap degrees into [-180, 180); works for scalars and arrays."""
    return (values + 180.0) % 360.0 - 180.0


def _ring_to_polygon(ring, inverse, forward, lon_ref):
    """Unproject one projected ring into a lon/lat polygon (continuous lons)."""
    xy = np.asarray(ring.coords, dtype=float)
    lon, lat = inverse(xy[:, 0], xy[:, 1])
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    if not (np.isfinite(lon).all() and np.isfinite(lat).all()):
        raise _Unprojectable("inverse projection produced non-finite coordinates")

    # Remove the +/-360 jumps the inverse transform introduces at the seam,
    # then park the whole ring on the branch closest to the projection centre.
    lon = np.unwrap(lon, period=360.0)
    lon = lon + 360.0 * round((lon_ref - 0.5 * float(lon.min() + lon.max())) / 360.0)

    if abs(float(lon[-1] - lon[0])) > 180.0:
        # The ring winds once around a pole, so it is not closed in lon/lat.
        # Close it through the pole to get the cap it actually bounds.
        pole = _encircled_pole(ring, forward)
        if pole is not None:
            if lon[-1] < lon[0]:
                lon, lat = lon[::-1], lat[::-1]
            pts = list(zip(lon.tolist(), lat.tolist()))
            pts.append((float(lon[-1]), pole))
            pts.append((float(lon[0]), pole))
            return Polygon(pts)

    return Polygon(zip(lon.tolist(), lat.tolist()))


def _encircled_pole(projected_ring, forward):
    """Return +90 / -90 for the pole enclosed by a projected ring, else None."""
    ring_poly = _valid(Polygon(projected_ring))
    for lat in (90.0, -90.0):
        x, y = forward(0.0, lat)
        if math.isfinite(x) and math.isfinite(y) and ring_poly.contains(Point(x, y)):
            return lat
    return None


def _wrap_into_range(geom):
    """Cut a geometry with out-of-range longitudes into [-180, 180] slices."""
    minx, _, maxx, _ = geom.bounds
    if minx >= -180.0 and maxx <= 180.0:
        return geom

    pieces = []
    first = math.floor((minx + 180.0) / 360.0)
    last = math.floor((maxx + 180.0) / 360.0)
    for k in range(first, last + 1):
        band = shapely.box(-180.0 + 360.0 * k, -90.0, 180.0 + 360.0 * k, 90.0)
        piece = geom.intersection(band)
        if piece.is_empty:
            continue
        if k:
            piece = translate(piece, xoff=-360.0 * k)
        pieces.append(piece)
    if not pieces:
        return Polygon()
    return shapely.unary_union(pieces)


def _polygons(geom):
    return [p for p in shapely.get_parts(geom) if isinstance(p, Polygon) and not p.is_empty]


def _valid(geom):
    if geom.is_valid:
        return geom
    return _polygonal(shapely.make_valid(geom))


def _polygonal(geom):
    """Keep only the polygonal parts and normalise the container type."""
    if isinstance(geom, Polygon):
        return geom
    polys = _polygons(geom)
    if not polys:
        return Polygon()
    if len(polys) == 1:
        return polys[0]
    return MultiPolygon(polys)
```