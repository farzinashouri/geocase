"""Accurate metric buffering of WGS84 (EPSG:4326) geometries.

The public entry point is :func:`buffer_m`.  Importing this module performs no
I/O and has no side effects.

Approach
--------
``shapely`` only knows how to buffer in a Cartesian plane, so a lon/lat
geometry has to be projected first.  A single global projection cannot do this
accurately (a metre is a different number of degrees in Svalbard than in
Ecuador), so instead a *local* azimuthal-equidistant (AEQD) projection is built
on the fly, centred on the geometry itself:

1. Long edges of the input are densified along true geodesics, so that an edge
   is interpreted as the shortest path on the ellipsoid rather than as a
   straight line in lon/lat space.
2. The geometry is projected into an ellipsoidal AEQD frame centred on the
   geometry's spherical mean.  In that frame distances *from the centre* are
   true geodesic distances, so a planar buffer is a geodesic buffer.
3. The buffer is computed with ``shapely``, densified again, and projected back.
4. The result is normalised for spherical topology: rings that wrap around a
   pole get a polar cap inserted, and rings that cross the antimeridian are cut
   at ±180° into a ``MultiPolygon``.

Accuracy notes
--------------
* For a point input the result is a true geodesic circle to within the
  discretisation implied by ``quad_segs``.
* For extended inputs, AEQD's transverse scale error grows with distance from
  the projection centre (~``(s/R)**2 / 6``: about 0.4 % at 1000 km, 1.7 % at
  2000 km *of the buffer distance*, not of the geometry size).  Sub-continental
  inputs are therefore accurate to well under a metre for typical buffer radii.
* Buffers approaching the antipode of the projection centre (~20 000 km) hit
  the AEQD singularity; they are clipped to the projection domain, and a buffer
  that swallows the whole ellipsoid returns the full lon/lat world box.
* Z coordinates are dropped.
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
import shapely
from pyproj import CRS, Geod, Transformer
from shapely.affinity import translate
from shapely.geometry import (
    GeometryCollection,
    LinearRing,
    LineString,
    MultiLineString,
    MultiPolygon,
    Point,
    Polygon,
    box,
)
from shapely.geometry.base import BaseGeometry

__all__ = ["buffer_m"]

_WGS84 = "EPSG:4326"
_GEOD = Geod(ellps="WGS84")
_WORLD = box(-180.0, -90.0, 180.0, 90.0)

# Half the WGS84 meridian circumference: the *smallest* distance to an antipode
# over all azimuths, hence a radius that is safely inside the AEQD domain.
_SAFE_R = 20_003_000.0
# Larger than the greatest possible geodesic distance on WGS84 (pi * a).
_FULL_R = 20_037_600.0

_MULTI = {
    "MultiLineString": MultiLineString,
    "MultiPolygon": MultiPolygon,
    "GeometryCollection": GeometryCollection,
}


def buffer_m(geom, distance_m, *, quad_segs=32, max_segment_m=10_000.0):
    """Buffer a lon/lat geometry by a distance in metres.

    Parameters
    ----------
    geom : shapely geometry
        Any shapely geometry whose coordinates are longitude/latitude degrees
        in EPSG:4326.
    distance_m : float
        Buffer distance in metres.  Positive dilates; negative erodes (only
        meaningful for polygons); zero returns the input unchanged.
    quad_segs : int, optional
        Segments per quarter circle used to approximate round joins.  The
        default of 32 keeps the radial discretisation error below ~0.03 % of
        the buffer distance.
    max_segment_m : float, optional
        Maximum edge length, in metres, used when densifying the input edges
        (as geodesics) and the buffer outline (before returning to lon/lat).

    Returns
    -------
    shapely ``Polygon`` or ``MultiPolygon`` in EPSG:4326, or an empty
    ``Polygon`` if the buffer vanishes.  A geometry that crosses the
    antimeridian is returned as a ``MultiPolygon`` split at ±180°.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"geom must be a shapely geometry, got {type(geom)!r}")
    distance_m = float(distance_m)
    if not math.isfinite(distance_m):
        raise ValueError("distance_m must be finite")
    max_segment_m = float(max_segment_m)
    if not (max_segment_m > 0.0 and math.isfinite(max_segment_m)):
        raise ValueError("max_segment_m must be a positive, finite number")
    quad_segs = int(quad_segs)
    if quad_segs < 1:
        raise ValueError("quad_segs must be >= 1")

    geom = shapely.force_2d(geom)
    if geom.is_empty:
        return Polygon()
    if distance_m == 0.0:
        return geom

    lat0, lon0 = _center(geom)
    fwd, inv = _transformers(lat0, lon0)

    projected = _reproject(_densify(geom, max_segment_m), fwd)
    buffered = projected.buffer(distance_m, quad_segs=quad_segs)
    if buffered.is_empty:
        return Polygon()

    # Keep the buffer inside the domain where AEQD is invertible.
    if _max_radius(buffered) > _SAFE_R:
        if buffered.covers(_disk(_FULL_R, quad_segs)):
            return _WORLD
        buffered = _polygonal(buffered.intersection(_disk(_SAFE_R, quad_segs)))
        if buffered.is_empty:
            return Polygon()

    # Does the buffer swallow a pole?  Cheap and exact to test in the plane.
    north = buffered.covers(Point(*fwd.transform(0.0, 90.0)))
    south = buffered.covers(Point(*fwd.transform(0.0, -90.0)))
    if north and south:
        return _WORLD

    buffered = shapely.segmentize(buffered, max_segment_m)
    return _normalize(_reproject(buffered, inv), north, south)


# --------------------------------------------------------------------------- #
# projection plumbing
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=256)
def _transformers(lat0, lon0):
    """Forward/inverse transformers for an AEQD frame centred on (lat0, lon0)."""
    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +x_0=0 +y_0=0 "
        "+datum=WGS84 +units=m +no_defs"
    )
    return (
        Transformer.from_crs(_WGS84, aeqd, always_xy=True),
        Transformer.from_crs(aeqd, _WGS84, always_xy=True),
    )


def _center(geom):
    """Spherical mean of the vertices, rounded so nearby calls share a cache slot."""
    coords = shapely.get_coordinates(geom)
    lon = np.radians(coords[:, 0])
    lat = np.radians(coords[:, 1])
    clat = np.cos(lat)
    vec = np.array([np.mean(clat * np.cos(lon)), np.mean(clat * np.sin(lon)), np.mean(np.sin(lat))])
    norm = float(np.linalg.norm(vec))
    if norm < 1e-9:  # vertices cancel out (e.g. antipodal pair): fall back
        return round(float(coords[0, 1]), 6), round(float(coords[0, 0]), 6)
    vec /= norm
    lat0 = math.degrees(math.asin(max(-1.0, min(1.0, vec[2]))))
    lon0 = math.degrees(math.atan2(vec[1], vec[0]))
    return round(lat0, 6), round(lon0, 6)


def _reproject(geom, transformer):
    def fn(coords):
        x, y = transformer.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])

    return shapely.transform(geom, fn)


def _disk(radius, quad_segs):
    return Point(0.0, 0.0).buffer(radius, quad_segs=max(quad_segs, 180))


def _max_radius(geom):
    minx, miny, maxx, maxy = geom.bounds
    return max(math.hypot(x, y) for x in (minx, maxx) for y in (miny, maxy))


# --------------------------------------------------------------------------- #
# geodesic densification of the input
# --------------------------------------------------------------------------- #


def _densify(geom, max_segment_m):
    """Split long edges into geodesic sub-edges, so edges mean shortest paths."""
    gtype = geom.geom_type
    if geom.is_empty or gtype in ("Point", "MultiPoint"):
        return geom
    if gtype == "LineString":
        return LineString(_densify_coords(geom.coords, max_segment_m))
    if gtype == "LinearRing":
        return LinearRing(_densify_coords(geom.coords, max_segment_m))
    if gtype == "Polygon":
        return Polygon(
            _densify_coords(geom.exterior.coords, max_segment_m),
            [_densify_coords(r.coords, max_segment_m) for r in geom.interiors],
        )
    if gtype in _MULTI:
        return _MULTI[gtype]([_densify(part, max_segment_m) for part in geom.geoms])
    return geom


def _densify_coords(coords, max_segment_m):
    pts = [(float(c[0]), float(c[1])) for c in coords]
    out = [pts[0]]
    for (lon1, lat1), (lon2, lat2) in zip(pts, pts[1:]):
        dist = _GEOD.inv(lon1, lat1, lon2, lat2)[2]
        if math.isfinite(dist) and dist > max_segment_m:
            npts = min(int(math.ceil(dist / max_segment_m)) - 1, 4000)
            if npts > 0:
                mid = _GEOD.inv_intermediate(
                    lon1, lat1, lon2, lat2, npts=npts, initial_idx=1, terminus_idx=1
                )
                out.extend(zip(mid.lons, mid.lats))
        out.append((lon2, lat2))
    return out


# --------------------------------------------------------------------------- #
# spherical topology fix-ups on the way back to lon/lat
# --------------------------------------------------------------------------- #


def _polygons(geom):
    if geom.is_empty:
        return []
    gtype = geom.geom_type
    if gtype == "Polygon":
        return [geom]
    if gtype == "MultiPolygon":
        return list(geom.geoms)
    if gtype == "GeometryCollection":
        return [p for part in geom.geoms for p in _polygons(part)]
    return []


def _polygonal(geom):
    parts = _polygons(geom)
    if not parts:
        return Polygon()
    return parts[0] if len(parts) == 1 else MultiPolygon(parts)


def _unwrap(coords):
    """Remove artificial 360° jumps so each edge takes the short way round."""
    lon = coords[:, 0].astype(float).copy()
    if len(lon) > 1:
        delta = np.diff(lon)
        delta -= 360.0 * np.round(delta / 360.0)
        lon[1:] = lon[0] + np.cumsum(delta)
    lat = np.clip(coords[:, 1].astype(float), -90.0, 90.0)
    return np.column_stack([lon, lat])


def _normalize(geom, north_inside, south_inside):
    parts = []
    for poly in _polygons(geom):
        parts.extend(_split_polygon(poly, north_inside, south_inside))
    if not parts:
        return Polygon()
    return _polygonal(shapely.union_all(parts))


def _split_polygon(poly, north_inside, south_inside):
    ext = _unwrap(np.asarray(poly.exterior.coords, dtype=float))
    holes = []
    ext_mean = float(ext[:, 0].mean())
    for ring in poly.interiors:
        hole = _unwrap(np.asarray(ring.coords, dtype=float))
        # Put the hole on the same 360° branch as the shell that contains it.
        hole[:, 0] += 360.0 * round((ext_mean - float(hole[:, 0].mean())) / 360.0)
        holes.append(hole)

    encircles_pole = abs(ext[-1, 0] - ext[0, 0]) > 180.0
    if encircles_pole:
        if north_inside and not south_inside:
            lat_pole = 90.0
        elif south_inside and not north_inside:
            lat_pole = -90.0
        else:
            lat_pole = 90.0 if ext[:, 1].mean() >= 0.0 else -90.0
        # Walk up to the pole, along it, and back down: this closes the cap.
        ext = np.vstack(
            [ext, [[ext[-1, 0], lat_pole], [ext[0, 0], lat_pole], ext[0]]]
        )

    lon_min = float(ext[:, 0].min())
    lon_max = float(ext[:, 0].max())
    if not encircles_pole and -180.0 <= lon_min and lon_max <= 180.0:
        return [poly]  # ordinary case: nothing to cut

    unwrapped = Polygon(ext, holes)
    if not unwrapped.is_valid:
        unwrapped = shapely.make_valid(unwrapped)

    k_lo = int(math.floor((lon_min + 180.0) / 360.0))
    k_hi = int(math.floor((lon_max + 180.0) / 360.0))
    k_hi = min(k_hi, k_lo + 8)  # guard against pathological coordinates

    pieces = []
    for k in range(k_lo, k_hi + 1):
        piece = translate(unwrapped, xoff=-360.0 * k).intersection(_WORLD)
        pieces.extend(_polygons(piece))
    return pieces