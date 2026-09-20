"""Accurate metric buffering of longitude/latitude geometries.

The module exposes one public function, :func:`buffer_m`, which buffers a
shapely geometry whose coordinates are lon/lat in EPSG:4326 by a distance in
metres and returns the result in EPSG:4326.

Approach
--------
Buffering is a metric operation and cannot be done in degrees.  For each
geometry an *azimuthal equidistant* (AEQD) projection is built on the fly,
centred on the geometry itself.  PROJ's ellipsoidal AEQD preserves true
geodesic distance and azimuth measured *from the projection centre*, so the
buffer is geodetically exact for a point input and degrades slowly with
distance from the centre.  The buffered polygon is densified, projected back to
lon/lat, and then repaired for the two ways the lon/lat plane fails to describe
a sphere:

* rings crossing the antimeridian are unwrapped into a continuous longitude
  frame and split at +/-180 into a MultiPolygon;
* rings enclosing a pole are closed with a cap at +/-90 -- or, when a ring winds
  no net longitude yet still encloses a pole, it is interpreted as the
  *complement* of the drawn ring.

Conventions and limits
----------------------
* Input edges are treated as geodesics (they are straightened in the AEQD
  plane), so a segment from lon 179 to lon -179 takes the short way across the
  antimeridian rather than the long way around.
* Accuracy is centimetre-level for inputs spanning a few hundred kilometres.
  Multi-part inputs wider than ``_SPLIT_RADIUS_M`` are buffered part-by-part,
  each in its own local projection, and unioned.  A *single* continent-scale
  ring still carries AEQD distortion at its far edges.
* ``distance_m`` may be negative (erosion).  ``distance_m == 0`` follows
  shapely's ``buffer(0)`` semantics (empty for points and lines).
* Z coordinates are dropped; the result is always a ``Polygon`` or
  ``MultiPolygon`` (possibly empty).

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry import MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry

__all__ = ["buffer_m"]

_WGS84 = "EPSG:4326"
_WORLD = box(-180.0, -90.0, 180.0, 90.0)

# Largest radius (m) for which the ellipsoidal AEQD inverse stays well defined;
# the antipode sits at ~20 004 km, so stop a little short of it.
_MAX_AEQD_RADIUS_M = 19_950_000.0

# Multi-part geometries wider than this get one local projection per part.
_SPLIT_RADIUS_M = 150_000.0

_MIN_DENSIFY_M = 1_000.0
_MAX_VERTICES = 100_000
_MAX_DEPTH = 5

_MULTI_TYPES = ("MultiPoint", "MultiLineString", "MultiPolygon", "GeometryCollection")


# --------------------------------------------------------------------------- #
# projection plumbing
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=1024)
def _transformers(lon0: float, lat0: float):
    """Forward/inverse transformers between EPSG:4326 and a local AEQD plane."""
    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +x_0=0 +y_0=0 "
        f"+datum=WGS84 +units=m +no_defs"
    )
    fwd = Transformer.from_crs(_WGS84, aeqd, always_xy=True)
    inv = Transformer.from_crs(aeqd, _WGS84, always_xy=True)
    return fwd, inv


def _apply(geom: BaseGeometry, tf: Transformer) -> BaseGeometry:
    """Vectorised coordinate transform of a whole geometry."""

    def _fn(coords: np.ndarray) -> np.ndarray:
        if coords.size == 0:
            return coords
        x, y = tf.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([np.asarray(x, dtype=float), np.asarray(y, dtype=float)])

    return shapely.transform(geom, _fn)


def _center(geom: BaseGeometry):
    """Mean vertex direction on the unit sphere, as (lon, lat) in degrees.

    Averaging 3-D direction vectors rather than degrees keeps the centre sane
    for inputs straddling the antimeridian or sitting near a pole.
    """
    coords = shapely.get_coordinates(geom)
    if coords.size == 0:
        return 0.0, 0.0
    lon = np.radians(coords[:, 0])
    lat = np.radians(coords[:, 1])
    cos_lat = np.cos(lat)
    x = float(np.mean(cos_lat * np.cos(lon)))
    y = float(np.mean(cos_lat * np.sin(lon)))
    z = float(np.mean(np.sin(lat)))
    norm = math.sqrt(x * x + y * y + z * z)
    if norm < 1e-12:  # antipodally spread vertices: any centre will do
        return round(float(coords[0, 0]), 6), round(float(coords[0, 1]), 6)
    lat0 = math.degrees(math.asin(max(-1.0, min(1.0, z / norm))))
    lon0 = math.degrees(math.atan2(y, x))
    return round(lon0, 6), round(lat0, 6)


# --------------------------------------------------------------------------- #
# small geometry helpers
# --------------------------------------------------------------------------- #

def _valid(geom: BaseGeometry) -> BaseGeometry:
    if geom.is_empty or geom.is_valid:
        return geom
    return shapely.make_valid(geom)


def _flatten_polygons(geom: BaseGeometry, out: list) -> None:
    if geom is None or geom.is_empty:
        return
    if geom.geom_type == "Polygon":
        out.append(geom)
    elif geom.geom_type in _MULTI_TYPES:
        for part in geom.geoms:
            _flatten_polygons(part, out)


def _polygonal(geom: BaseGeometry) -> BaseGeometry:
    """Keep only the polygonal content, as a Polygon/MultiPolygon."""
    parts: list = []
    _flatten_polygons(geom, parts)
    if not parts:
        return Polygon()
    if len(parts) == 1:
        return parts[0]
    return MultiPolygon(parts)


def _union(geoms) -> BaseGeometry:
    geoms = [g for g in geoms if g is not None and not g.is_empty]
    if not geoms:
        return Polygon()
    return _polygonal(_valid(shapely.union_all(geoms)))


def _shift_lon(geom: BaseGeometry, dx: float) -> BaseGeometry:
    offset = np.array([[dx, 0.0]])
    return shapely.transform(geom, lambda c: c if c.size == 0 else c + offset)


def _unwrap(lon: np.ndarray) -> np.ndarray:
    """Remove +/-360 jumps, giving a continuous longitude track."""
    if lon.size < 2:
        return lon.astype(float)
    step = np.diff(lon.astype(float))
    step -= 360.0 * np.round(step / 360.0)
    return np.concatenate([lon[:1].astype(float), lon[0] + np.cumsum(step)])


def _to_domain(poly: Polygon) -> BaseGeometry:
    """Clip a continuous-longitude polygon back into [-180, 180]."""
    if poly.is_empty:
        return Polygon()
    poly = _valid(poly)
    if poly.is_empty:
        return Polygon()
    minx, _, maxx, _ = poly.bounds
    k0 = int(math.floor((minx + 180.0) / 360.0))
    k1 = int(math.floor((maxx + 180.0) / 360.0))
    pieces = []
    for k in range(k0, k1 + 1):
        piece = shapely.intersection(_shift_lon(poly, -360.0 * k), _WORLD)
        piece = _polygonal(_valid(piece))
        if not piece.is_empty:
            pieces.append(piece)
    return _union(pieces)


def _covers(geom: BaseGeometry, point) -> bool:
    if point is None or geom.is_empty:
        return False
    try:
        return bool(geom.covers(point))
    except shapely.errors.GEOSException:  # pragma: no cover - defensive
        return False


def _pole_point(fwd: Transformer, lat: float):
    x, y = fwd.transform(0.0, lat)
    if not (math.isfinite(x) and math.isfinite(y)):
        return None
    if math.hypot(x, y) > _MAX_AEQD_RADIUS_M:
        return None
    return shapely.Point(x, y)


# --------------------------------------------------------------------------- #
# lon/lat reconstruction
# --------------------------------------------------------------------------- #

def _ring_region(ring, inv: Transformer, pole_n, pole_s) -> BaseGeometry:
    """Map one AEQD ring to the lon/lat region its interior covers."""
    ring_poly = _valid(Polygon(ring))
    north = _covers(ring_poly, pole_n)
    south = _covers(ring_poly, pole_s)

    xy = shapely.get_coordinates(ring)
    lon, lat = inv.transform(xy[:, 0], xy[:, 1])
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    keep = np.isfinite(lon) & np.isfinite(lat)
    if keep.sum() < 4:
        return Polygon()
    if not keep.all():
        lon, lat = lon[keep], lat[keep]

    lon = _unwrap(lon)
    lat = np.clip(lat, -90.0, 90.0)
    winding = int(round((lon[-1] - lon[0]) / 360.0))

    if winding != 0:
        # The ring wraps the polar axis: close it with a cap at one pole.
        if winding < 0:
            lon, lat = lon[::-1], lat[::-1]
        if north and not south:
            cap = 90.0
        elif south and not north:
            cap = -90.0
        else:  # degenerate/invalid ring: fall back to the dominant hemisphere
            cap = 90.0 if float(np.mean(lat)) >= 0.0 else -90.0
        coords = np.vstack(
            [np.column_stack([lon, lat]), [[lon[-1], cap], [lon[0], cap]]]
        )
        return _to_domain(Polygon(coords))

    region = _to_domain(Polygon(np.column_stack([lon, lat])))
    if north or south:
        # The ring bounds a region that swallows the poles, so the drawn
        # lon/lat polygon is the part that is *outside* it.
        return _polygonal(_valid(_WORLD.difference(region)))
    return region


def _part_region(part: Polygon, inv: Transformer, pole_n, pole_s) -> BaseGeometry:
    region = _ring_region(part.exterior, inv, pole_n, pole_s)
    if region.is_empty:
        return region
    for hole in part.interiors:
        hole_region = _ring_region(hole, inv, pole_n, pole_s)
        if not hole_region.is_empty:
            region = _polygonal(_valid(region.difference(hole_region)))
            if region.is_empty:
                break
    return region


# --------------------------------------------------------------------------- #
# core
# --------------------------------------------------------------------------- #

def _buffer(geom, distance_m, quad_segs, cap_style, join_style, mitre_limit,
            densify_m, depth):
    lon0, lat0 = _center(geom)
    fwd, inv = _transformers(lon0, lat0)

    projected = _apply(geom, fwd)
    xy = shapely.get_coordinates(projected)
    if xy.size and not np.isfinite(xy).all():
        raise ValueError("geometry could not be projected; check that coordinates "
                         "are lon/lat degrees in EPSG:4326")
    radius = float(np.hypot(xy[:, 0], xy[:, 1]).max()) if xy.size else 0.0

    # Wide multi-part input: give every part its own local projection.
    if (depth < _MAX_DEPTH
            and radius > _SPLIT_RADIUS_M
            and geom.geom_type in _MULTI_TYPES):
        return _union([
            _buffer(part, distance_m, quad_segs, cap_style, join_style,
                    mitre_limit, densify_m, depth + 1)
            for part in geom.geoms if not part.is_empty
        ])

    buffered = _valid(projected.buffer(
        distance_m,
        quad_segs=quad_segs,
        cap_style=cap_style,
        join_style=join_style,
        mitre_limit=mitre_limit,
    ))
    buffered = _polygonal(buffered)
    if buffered.is_empty:
        return Polygon()

    # Keep the polygon inside the region where the AEQD inverse is meaningful.
    if radius + abs(distance_m) > _MAX_AEQD_RADIUS_M:
        disc = shapely.Point(0.0, 0.0).buffer(_MAX_AEQD_RADIUS_M, quad_segs=128)
        if buffered.covers(disc):
            return _WORLD
        buffered = _polygonal(_valid(buffered.intersection(disc)))
        if buffered.is_empty:
            return Polygon()

    # Straight AEQD edges are curves in lon/lat, so densify before inverting.
    step = float(densify_m) if densify_m else max(abs(distance_m) / 8.0, _MIN_DENSIFY_M)
    perimeter = buffered.length
    if perimeter > 0.0:
        step = max(step, perimeter / _MAX_VERTICES)
    buffered = shapely.segmentize(buffered, step)

    pole_n = _pole_point(fwd, 90.0)
    pole_s = _pole_point(fwd, -90.0)

    parts: list = []
    _flatten_polygons(buffered, parts)
    return _union([_part_region(p, inv, pole_n, pole_s) for p in parts])


def _as_geometry(geom):
    if isinstance(geom, BaseGeometry):
        return geom
    if hasattr(geom, "__geo_interface__"):
        return shapely.geometry.shape(geom)
    raise TypeError(f"expected a shapely geometry, got {type(geom).__name__}")


def buffer_m(geom, distance_m, *, quad_segs=16, cap_style="round",
             join_style="round", mitre_limit=5.0, densify_m=None):
    """Buffer a lon/lat (EPSG:4326) geometry by ``distance_m`` metres.

    Parameters
    ----------
    geom :
        A shapely geometry, or anything exposing ``__geo_interface__``, with
        coordinates as (longitude, latitude) degrees in EPSG:4326.
    distance_m :
        Buffer distance in metres.  Negative values erode.
    quad_segs :
        Segments per quarter circle used for round joins and caps.  The default
        of 16 keeps the boundary within ~0.03% of the true distance.
    cap_style, join_style, mitre_limit :
        Passed through to :meth:`shapely.geometry.base.BaseGeometry.buffer`.
    densify_m :
        Maximum edge length, in metres, imposed on the buffered polygon before
        it is projected back to lon/lat.  Defaults to ``distance_m / 8``, with a
        1 km floor and a vertex-count ceiling.

    Returns
    -------
    Polygon or MultiPolygon
        The buffered geometry in EPSG:4326.  Results crossing the antimeridian
        are split into a MultiPolygon; results enclosing a pole are capped at
        +/-90 degrees latitude.

    Raises
    ------
    TypeError
        If ``geom`` is not a geometry.
    ValueError
        If ``distance_m`` is not finite, if a latitude is outside [-90, 90]
        (usually a sign the axis order is swapped), or if the projection fails.
    """
    geom = _as_geometry(geom)
    distance_m = float(distance_m)
    if not math.isfinite(distance_m):
        raise ValueError("distance_m must be finite")
    if geom.is_empty:
        return Polygon()

    coords = shapely.get_coordinates(geom)
    if coords.size:
        if not np.isfinite(coords).all():
            raise ValueError("geometry contains non-finite coordinates")
        if np.abs(coords[:, 1]).max() > 90.0 + 1e-9:
            raise ValueError("latitudes outside [-90, 90]; expected lon/lat order")

    return _buffer(geom, distance_m, quad_segs, cap_style, join_style,
                   mitre_limit, densify_m, depth=0)