"""Buffer EPSG:4326 (WGS84 lon/lat) geometries by a distance in metres.

``buffer_m`` projects the geometry into an azimuthal equidistant (AEQD)
projection centred on the geometry itself, buffers there, and projects the
result back to lon/lat.  Ellipsoidal AEQD reproduces true geodesic distance and
azimuth from its centre, so the requested distance is exact at the centre of a
patch and accurate to ~0.1% at its edge.  Geometries too large for a single
patch are cut up and buffered piecewise: dilation distributes over unions, so
the pieces reassemble into exactly the right result.

The projection follows the data, so there is no UTM zone to pick, no Web
Mercator scale error and no degrees-per-metre approximation; rings that cross
the antimeridian are split at +/-180 and rings that enclose a pole are closed
over it.

Importing this module has no side effects: PROJ objects are built lazily on
first use and cached.
"""

from __future__ import annotations

import math
import warnings
from functools import lru_cache

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.affinity import translate
from shapely.geometry import GeometryCollection, Polygon, box
from shapely.geometry.base import BaseGeometry, BaseMultipartGeometry

__all__ = ["buffer_m"]

# Largest angular radius (degrees of arc from the patch centre) a single AEQD
# patch may cover.  AEQD stretches lengths perpendicular to the radius by
# c/sin(c), which is 0.13% at 5 degrees.
_MAX_PATCH_DEG = 5.0

# Erosion cannot be split into patches, so it gets one (looser) limit instead.
_MAX_ERODE_PATCH_DEG = 30.0

_MAX_SPLIT_DEPTH = 16


def buffer_m(geom, distance_m, *, quad_segs: int = 16):
    """Buffer a WGS84 geometry by a distance in metres.

    Args:
        geom: Any shapely geometry whose coordinates are longitude/latitude in
            EPSG:4326.  Z values are dropped (buffering is planar).
        distance_m: Distance in metres, as geodesic distance on the WGS84
            ellipsoid.  Positive dilates, zero returns ``geom`` unchanged, and
            negative erodes (see Raises).
        quad_segs: Segments per quarter circle used to round corners.  The
            default of 16 keeps the polygonal approximation of a circle within
            ~0.12% of the true distance.

    Returns:
        A ``Polygon`` or ``MultiPolygon`` in EPSG:4326, split at the
        antimeridian where it crosses +/-180 and closed over the pole where it
        encloses one.  An empty ``Polygon`` if nothing survives, e.g. an
        erosion that consumes the whole input.

    Raises:
        TypeError: ``geom`` is not a shapely geometry.
        ValueError: coordinates are not plausible lon/lat, ``distance_m`` is
            not finite, or a negative ``distance_m`` was asked of a geometry
            too large to erode in a single projection.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"geom must be a shapely geometry, got {type(geom).__name__}")
    if quad_segs < 1:
        raise ValueError("quad_segs must be >= 1")
    distance_m = float(distance_m)
    if not math.isfinite(distance_m):
        raise ValueError("distance_m must be a finite number of metres")

    if geom.is_empty:
        return Polygon()

    coords = shapely.get_coordinates(geom)
    if not np.isfinite(coords).all():
        raise ValueError("geom contains non-finite coordinates")
    if np.abs(coords[:, 1]).max() > 90.0:
        raise ValueError(
            "geom has latitudes outside [-90, 90]; coordinates must be "
            "EPSG:4326 longitude/latitude in that order"
        )

    if distance_m == 0.0:
        return geom

    if distance_m < 0.0:
        # Erosion does not distribute over a union, so it cannot be split into
        # patches the way dilation can -- it has to fit in one projection.
        lon0, lat0 = _centre(coords)
        radius = _angular_radius(coords, lon0, lat0)
        if radius > _MAX_ERODE_PATCH_DEG:
            raise ValueError(
                f"geom spans {radius:.1f} deg of arc, too much to erode in a "
                "single local projection; erode its parts separately"
            )
        if radius > _MAX_PATCH_DEG:
            warnings.warn(
                f"geom spans {radius:.1f} deg of arc; the eroded distance may "
                f"be off by up to {100.0 * (_stretch(radius) - 1.0):.1f}% at "
                "its far edge",
                stacklevel=2,
            )
        return _patch_buffer(geom, distance_m, quad_segs, lon0, lat0)

    return _dilate(geom, distance_m, quad_segs, 0)


# --------------------------------------------------------------------------- #
# projection
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=256)
def _transformers(lon0: float, lat0: float):
    """Forward/inverse transformers for an AEQD patch centred on (lon0, lat0)."""
    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0:.6f} +lon_0={lon0:.6f} +x_0=0 +y_0=0 "
        "+datum=WGS84 +units=m +no_defs"
    )
    wgs84 = CRS.from_epsg(4326)
    return (
        Transformer.from_crs(wgs84, aeqd, always_xy=True),
        Transformer.from_crs(aeqd, wgs84, always_xy=True),
    )


def _reproject(geom, transformer):
    def _fn(xy):
        x, y = transformer.transform(xy[:, 0], xy[:, 1])
        out = np.column_stack([x, y])
        if not np.isfinite(out).all():
            raise ValueError(
                "geometry could not be projected: a vertex is antipodal to the "
                "projection centre"
            )
        return out

    return shapely.transform(geom, _fn, include_z=False)


def _centre(coords):
    """Mean direction of the vertices, as (lon, lat) in degrees.

    Averaging unit vectors rather than degrees keeps the centre sane across the
    antimeridian and at the poles.
    """
    lon = np.radians(coords[:, 0])
    lat = np.radians(coords[:, 1])
    cos_lat = np.cos(lat)
    vx = float(np.mean(cos_lat * np.cos(lon)))
    vy = float(np.mean(cos_lat * np.sin(lon)))
    vz = float(np.mean(np.sin(lat)))
    norm = math.sqrt(vx * vx + vy * vy + vz * vz)
    if norm < 1e-12:
        # Vertices cancel out (e.g. antipodal pairs); any centre is arbitrary.
        return float(coords[0, 0]), float(coords[0, 1])
    return math.degrees(math.atan2(vy, vx)), math.degrees(math.asin(vz / norm))


def _angular_radius(coords, lon0, lat0):
    """Greatest angular distance, in degrees, from (lon0, lat0) to a vertex."""
    lon = np.radians(coords[:, 0])
    lat = np.radians(coords[:, 1])
    lon_c = math.radians(lon0)
    lat_c = math.radians(lat0)
    hav = (
        np.sin(0.5 * (lat - lat_c)) ** 2
        + math.cos(lat_c) * np.cos(lat) * np.sin(0.5 * (lon - lon_c)) ** 2
    )
    return math.degrees(2.0 * math.asin(min(1.0, math.sqrt(float(hav.max())))))


def _stretch(radius_deg):
    """AEQD tangential scale factor c/sin(c) at an angular radius."""
    c = math.radians(radius_deg)
    return 1.0 if c < 1e-9 else c / math.sin(c)


# --------------------------------------------------------------------------- #
# buffering
# --------------------------------------------------------------------------- #


def _dilate(geom, distance_m, quad_segs, depth):
    if isinstance(geom, GeometryCollection):
        # Overlay operations reject mixed collections, so handle the members
        # one by one and merge the buffers.
        parts = []
        for member in geom.geoms:
            if not member.is_empty:
                parts.extend(_polygons(_dilate(member, distance_m, quad_segs, depth)))
        return shapely.union_all(parts) if parts else Polygon()

    coords = shapely.get_coordinates(geom)
    lon0, lat0 = _centre(coords)
    if depth >= _MAX_SPLIT_DEPTH or _angular_radius(coords, lon0, lat0) <= _MAX_PATCH_DEG:
        return _patch_buffer(geom, distance_m, quad_segs, lon0, lat0)

    # Dilation distributes over unions -- (A | B) + d == (A + d) | (B + d) --
    # so anything too big for one patch is halved and the halves reassembled.
    # The halves' buffers overlap by 2 * distance_m, so there is no seam.
    minx, miny, maxx, maxy = geom.bounds
    if maxx - minx >= maxy - miny:
        mid = 0.5 * (minx + maxx)
        halves = (box(minx, miny, mid, maxy), box(mid, miny, maxx, maxy))
    else:
        mid = 0.5 * (miny + maxy)
        halves = (box(minx, miny, maxx, mid), box(minx, mid, maxx, maxy))

    parts = []
    for half in halves:
        piece = shapely.intersection(geom, half)
        if not piece.is_empty:
            parts.extend(_polygons(_dilate(piece, distance_m, quad_segs, depth + 1)))
    return shapely.union_all(parts) if parts else Polygon()


def _patch_buffer(geom, distance_m, quad_segs, lon0, lat0):
    """Buffer within a single AEQD patch and bring the result back to lon/lat."""
    lon0 = round(lon0, 6)
    lat0 = round(lat0, 6)
    fwd, inv = _transformers(lon0, lat0)
    planar = _reproject(geom, fwd).buffer(distance_m, quad_segs=quad_segs)

    parts = []
    for poly in _polygons(planar):
        wrapped = Polygon(
            _ring_to_wgs84(poly.exterior, inv, lon0),
            [_ring_to_wgs84(ring, inv, lon0) for ring in poly.interiors],
        )
        if not wrapped.is_valid:
            wrapped = shapely.make_valid(wrapped)
        parts.extend(_polygons(wrapped))
    if not parts:
        return Polygon()
    return _split_at_antimeridian(shapely.union_all(parts))


def _ring_to_wgs84(ring, inv, lon0):
    """Inverse-project one projected ring into a continuous lon/lat ring.

    Longitudes are unwrapped so the ring does not jump at +/-180, and a ring
    that winds all the way round a pole is closed over that pole.
    """
    xy = np.asarray(ring.coords, dtype=float)
    if not ring.is_ccw:
        # Orient every ring counter-clockwise in the projected plane so the
        # region it bounds is always on its left; AEQD preserves orientation,
        # so that still holds after the inverse projection.
        xy = xy[::-1]

    lon, lat = inv.transform(xy[:, 0], xy[:, 1])
    lon = _unwrap_degrees(np.asarray(lon, dtype=float))
    lat = np.asarray(lat, dtype=float)
    # Place the ring in the 360-degree window around the patch centre.
    lon = lon + 360.0 * round((lon0 - lon[0]) / 360.0)

    out = np.column_stack([lon, lat])
    winding = lon[-1] - lon[0]
    if abs(winding) > 180.0:
        # The ring circles a pole: it is the pole to its left, i.e. the north
        # pole when the ring runs eastward.  Close the ring over it.
        pole = 90.0 if winding > 0.0 else -90.0
        out = np.vstack([out, [lon[-1], pole], [lon[0], pole]])
    return out


def _unwrap_degrees(lon):
    """Remove +/-360 jumps along a longitude sequence."""
    if lon.size < 2:
        return lon
    step = np.diff(lon)
    step -= 360.0 * np.round(step / 360.0)
    return np.concatenate((lon[:1], lon[0] + np.cumsum(step)))


def _split_at_antimeridian(geom):
    """Cut a geometry living in unwrapped longitudes back into [-180, 180]."""
    minx, _, maxx, _ = geom.bounds
    first = math.floor((minx + 180.0) / 360.0)
    last = math.floor((maxx + 180.0) / 360.0)
    if first == 0 and last == 0:
        return geom

    parts = []
    for k in range(first, last + 1):
        band = box(-180.0 + 360.0 * k, -90.0, 180.0 + 360.0 * k, 90.0)
        clipped = shapely.intersection(geom, band)
        if not clipped.is_empty:
            parts.extend(_polygons(translate(clipped, xoff=-360.0 * k)))
    if not parts:
        return Polygon()
    return shapely.union_all(parts)


def _polygons(geom):
    """Every non-empty polygon inside a geometry, however deeply nested."""
    out = []
    stack = [geom]
    while stack:
        part = stack.pop()
        if part.is_empty:
            continue
        if isinstance(part, Polygon):
            out.append(part)
        elif isinstance(part, BaseMultipartGeometry):
            stack.extend(part.geoms)
    return out