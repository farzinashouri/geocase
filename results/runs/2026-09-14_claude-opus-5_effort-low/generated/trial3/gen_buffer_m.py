"""Metric buffering of WGS84 (EPSG:4326) geometries.

The trick is that you cannot buffer in degrees: one degree of longitude is
~111 km at the equator and ~0 km at the poles. Instead each geometry is
projected into an azimuthal equidistant (AEQD) projection centred on that
geometry, buffered there (where the unit is the metre), and projected back.

AEQD preserves distance and azimuth *from its centre point*, so centring it on
the geometry keeps the distortion over the geometry and its buffer small.  This
works at any latitude, including the poles, which is why it is preferred over a
fixed grid such as UTM or Web Mercator.

Known limitation: the output is a single EPSG:4326 geometry, so a buffer that
crosses the antimeridian is returned with longitudes wrapped into
[-180, 180] and will appear as a shape smeared across the map rather than
split into two parts. Split it with an antimeridian-aware routine if you need
that. Buffers that enclose a pole have the same issue.
"""

from __future__ import annotations

import math

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform

__all__ = ["buffer_m"]

# Mean Earth radius (m), used only for the sanity check on `distance_m`.
_EARTH_RADIUS_M = 6_371_008.8

# AEQD centres are rounded to this many decimal degrees before being used as a
# cache key, so nearby geometries share a transformer. 1e-3 deg is ~100 m of
# extra offset from the projection centre, which is negligible next to the
# distortion the projection already has at buffer range.
_CENTRE_ROUNDING = 3

_transformer_cache: dict[tuple[float, float], tuple[Transformer, Transformer]] = {}


def _transformers(lon: float, lat: float) -> tuple[Transformer, Transformer]:
    """Return (to_aeqd, from_aeqd) transformers centred on (lon, lat)."""
    key = (round(lon, _CENTRE_ROUNDING), round(lat, _CENTRE_ROUNDING))
    cached = _transformer_cache.get(key)
    if cached is None:
        aeqd = CRS.from_proj4(
            f"+proj=aeqd +lat_0={key[1]} +lon_0={key[0]} "
            "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
        )
        wgs84 = CRS.from_epsg(4326)
        cached = (
            Transformer.from_crs(wgs84, aeqd, always_xy=True),
            Transformer.from_crs(aeqd, wgs84, always_xy=True),
        )
        _transformer_cache[key] = cached
    return cached


def _centre(geom: BaseGeometry) -> tuple[float, float]:
    """Pick an AEQD centre for `geom`.

    Uses the centre of the bounding box rather than the centroid: the centroid
    of an L-shaped or multi-part geometry can sit far from the geometry itself,
    which would put the whole shape in the distorted part of the projection.
    Longitude is averaged on the unit circle so that geometries spanning the
    antimeridian get a centre near them instead of near 0 deg.
    """
    min_x, min_y, max_x, max_y = geom.bounds
    if max_x - min_x > 180.0:
        # Probably spans the antimeridian; average the two extremes circularly.
        a, b = math.radians(min_x), math.radians(max_x)
        lon = math.degrees(
            math.atan2((math.sin(a) + math.sin(b)) / 2.0, (math.cos(a) + math.cos(b)) / 2.0)
        )
    else:
        lon = (min_x + max_x) / 2.0
    lat = max(-90.0, min(90.0, (min_y + max_y) / 2.0))
    return lon, lat


def _wrap_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180]."""
    return (lon + 180.0) % 360.0 - 180.0


def buffer_m(geom: BaseGeometry, distance_m: float, **buffer_kwargs) -> BaseGeometry:
    """Buffer a lon/lat geometry by a distance in metres.

    Parameters
    ----------
    geom:
        Any shapely geometry with coordinates as (longitude, latitude) degrees
        in EPSG:4326.
    distance_m:
        Buffer distance in metres. Negative values erode the geometry, as with
        ``shapely``'s own ``buffer``.
    **buffer_kwargs:
        Passed through to ``shapely.geometry.base.BaseGeometry.buffer``
        (``quad_segs``, ``cap_style``, ``join_style``, ...).

    Returns
    -------
    A shapely geometry in EPSG:4326. May be empty if a negative distance
    erodes the input away.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"geom must be a shapely geometry, got {type(geom).__name__}")
    distance_m = float(distance_m)
    if not math.isfinite(distance_m):
        raise ValueError("distance_m must be finite")
    if abs(distance_m) > math.pi * _EARTH_RADIUS_M:
        raise ValueError(
            "distance_m exceeds half the Earth's circumference; the result "
            "would not be representable as a lon/lat polygon"
        )
    if geom.is_empty:
        return geom

    to_aeqd, from_aeqd = _transformers(*_centre(geom))

    projected = shapely_transform(lambda x, y, z=None: to_aeqd.transform(x, y), geom)
    buffered = projected.buffer(distance_m, **buffer_kwargs)
    if buffered.is_empty:
        return buffered

    def _back(x, y, z=None):
        lon, lat = from_aeqd.transform(x, y)
        # pyproj already returns lon in [-180, 180] for AEQD, but points
        # exactly on the antipode can come back as inf; guard against those.
        return (
            tuple(_wrap_lon(v) if math.isfinite(v) else v for v in lon)
            if hasattr(lon, "__iter__")
            else (_wrap_lon(lon) if math.isfinite(lon) else lon),
            lat,
        )

    return shapely_transform(_back, buffered)