"""Accurate metric buffering of WGS84 (EPSG:4326) geometries.

``buffer_m(geom, distance_m)`` takes a shapely geometry whose coordinates are
longitude/latitude on WGS84, buffers it by a distance in meters, and returns the
result in longitude/latitude.

Method
------
The geometry is projected onto an azimuthal equidistant (AEQD) plane centred on
the geometry itself, buffered there with GEOS, and projected back.  PROJ
implements the *ellipsoidal* AEQD with geodesic formulas, so the planar distance
and azimuth from the projection centre are exactly the WGS84 geodesic distance
and azimuth: a planar circle of radius ``d`` around the centre is exactly the set
of points ``d`` meters away on the ellipsoid.  A buffer around a point is
therefore geodesically exact (up to the polygonal approximation of the circle),
and error grows only with the extent of the *input* geometry around its own
centre -- roughly ``(r / R_earth)**2 / 6`` relative scale error at distance ``r``
from the centre, i.e. ~0.1% at 500 km, ~1% at 1600 km.

Edges of the input are treated as geodesics: they are densified along the
geodesic before projection, and the buffered outline is densified again before
being projected back, so that the straight lon/lat segments of the output stay
within ~0.1% of the buffer distance of the true shape.

Antimeridian and poles are handled explicitly: output rings are unwrapped into a
continuous longitude frame, rings encircling a pole are closed over the pole
itself (instead of collapsing into a zero-width sliver), and the result is cut
back into the [-180, 180] window.

Importing this module has no side effects; PROJ objects are built lazily on the
first call and cached.
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
import shapely
from pyproj import CRS, Geod, Transformer
from shapely.affinity import translate
from shapely.geometry import LinearRing, LineString, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

__all__ = ["buffer_m"]

# Segments per quarter circle; 64 keeps the polygonal circle within 0.03% of the
# true circle.
_QUAD_SEGS = 64
# Target chord error of the densified outlines, relative to the buffer distance.
_REL_TOL = 1e-3
_MIN_TOL_M = 0.05
# Bounds on the densification step, to keep pathological inputs tractable.
_MIN_SEGMENT_M = 100.0
_MAX_SEGMENT_M = 100_000.0
_MEAN_EARTH_RADIUS_M = 6_371_008.8
# Longest possible WGS84 geodesic (pole to pole); the AEQD disc has this radius.
_MAX_GEODESIC_M = 20_003_931.5
_LON_EPS = 1e-9


def buffer_m(geom, distance_m):
    """Buffer a WGS84 lon/lat geometry by ``distance_m`` meters.

    Parameters
    ----------
    geom : shapely geometry
        Any geometry type, coordinates as (longitude, latitude) in EPSG:4326.
        Longitudes outside [-180, 180] are accepted.
    distance_m : float
        Buffer distance in meters.  Positive expands; negative erodes polygons
        (and empties lower-dimensional geometries), following shapely semantics.

    Returns
    -------
    shapely ``Polygon`` or ``MultiPolygon`` in EPSG:4326, with longitudes in
    [-180, 180].  A buffer crossing the antimeridian is returned as a
    ``MultiPolygon`` split along it.  ``distance_m == 0`` returns ``geom``
    unchanged; an empty input returns an empty ``Polygon``.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError("geom must be a shapely geometry")
    distance_m = float(distance_m)
    if not math.isfinite(distance_m):
        raise ValueError("distance_m must be finite")
    if geom.is_empty:
        return Polygon()
    if distance_m == 0.0:
        return geom

    lon0, lat0 = _projection_centre(geom)
    fwd, inv = _transformers(lon0, lat0)

    tol_m = max(abs(distance_m) * _REL_TOL, _MIN_TOL_M)
    # Sagitta of a chord of length L on a sphere is ~L^2 / (8 R); invert for L.
    max_seg_m = min(
        max(math.sqrt(8.0 * _MEAN_EARTH_RADIUS_M * tol_m), _MIN_SEGMENT_M),
        _MAX_SEGMENT_M,
    )

    planar = _map_coords(geom, _projector(fwd, max_seg_m))
    buffered = planar.buffer(distance_m, quad_segs=_QUAD_SEGS)
    if buffered.is_empty:
        return Polygon()

    # A buffer reaching past the antipode of the projection centre wraps around
    # the far edge of the AEQD disc, where the projection is no longer usable.
    # Such a buffer covers (essentially) the whole globe.
    xy = shapely.get_coordinates(buffered)
    if float(np.max(np.hypot(xy[:, 0], xy[:, 1]))) >= _MAX_GEODESIC_M:
        return box(-180.0, -90.0, 180.0, 90.0)

    buffered = shapely.segmentize(buffered, max_seg_m)

    pole_x, pole_y = fwd.transform([0.0, 0.0], [90.0, -90.0])
    planar_poles = (
        (90.0, Point(pole_x[0], pole_y[0])),
        (-90.0, Point(pole_x[1], pole_y[1])),
    )

    parts = []
    for poly in _polygons(buffered):
        lonlat = _polygon_to_wgs84(poly, inv, lon0, planar_poles)
        if not lonlat.is_valid:
            lonlat = shapely.make_valid(lonlat)
        parts.extend(_polygons(lonlat))
    if not parts:
        return Polygon()

    return _split_antimeridian(unary_union(parts))


# --------------------------------------------------------------------------- #
# PROJ objects (built lazily so that importing the module does nothing)
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=1)
def _geod() -> Geod:
    return Geod(ellps="WGS84")


@lru_cache(maxsize=64)
def _transformers(lon0: float, lat0: float):
    """Forward/inverse transformers between EPSG:4326 and AEQD at (lon0, lat0)."""
    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0!r} +lon_0={lon0!r} "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )
    return (
        Transformer.from_crs("EPSG:4326", aeqd, always_xy=True),
        Transformer.from_crs(aeqd, "EPSG:4326", always_xy=True),
    )


def _projection_centre(geom):
    """Centre for the AEQD plane: the mean of the vertices as 3D unit vectors.

    Averaging on the sphere rather than in lon/lat keeps the centre sane for
    geometries crossing the antimeridian or sitting on a pole.
    """
    xy = shapely.get_coordinates(geom)
    lon = np.radians(xy[:, 0])
    lat = np.radians(xy[:, 1])
    coslat = np.cos(lat)
    v = np.array(
        [
            float(np.mean(coslat * np.cos(lon))),
            float(np.mean(coslat * np.sin(lon))),
            float(np.mean(np.sin(lat))),
        ]
    )
    norm = float(np.linalg.norm(v))
    if norm < 1e-9:
        # Vertices cancel out (antipodally balanced); any centre will do.
        return float(xy[0, 0]), float(xy[0, 1])
    v /= norm
    lon0 = math.degrees(math.atan2(v[1], v[0]))
    lat0 = math.degrees(math.asin(max(-1.0, min(1.0, v[2]))))
    return lon0, lat0


# --------------------------------------------------------------------------- #
# lon/lat -> AEQD
# --------------------------------------------------------------------------- #


def _projector(fwd, max_seg_m):
    """Coordinate mapper: geodesic densification followed by projection."""

    def project(coords):
        dense = _densify_geodesic(coords, max_seg_m)
        x, y = fwd.transform(
            np.ascontiguousarray(dense[:, 0]), np.ascontiguousarray(dense[:, 1])
        )
        return np.column_stack([x, y])

    return project


def _densify_geodesic(coords, max_seg_m):
    """Insert vertices so consecutive lon/lat points are <= max_seg_m apart."""
    if len(coords) < 2:
        return coords
    geod = _geod()
    lon = np.ascontiguousarray(coords[:, 0], dtype=float)
    lat = np.ascontiguousarray(coords[:, 1], dtype=float)
    _, _, dist = geod.inv(lon[:-1], lat[:-1], lon[1:], lat[1:])
    dist = np.asarray(dist, dtype=float)
    if not np.any(dist > max_seg_m):
        return coords
    out = [coords[0]]
    for i, d in enumerate(dist):
        if d > max_seg_m:
            out.extend(
                geod.npts(lon[i], lat[i], lon[i + 1], lat[i + 1], int(d // max_seg_m))
            )
        out.append(coords[i + 1])
    return np.asarray(out, dtype=float)


def _map_coords(geom, func):
    """Rebuild ``geom`` with each coordinate sequence replaced by ``func(seq)``.

    ``func`` takes and returns an (N, 2) float array.  Sequences are mapped one
    ring / part at a time, which is what densification needs.
    """
    if geom.is_empty:
        return geom
    kind = geom.geom_type
    if kind == "Point":
        return Point(func(shapely.get_coordinates(geom))[0])
    if kind == "LineString":
        return LineString(func(shapely.get_coordinates(geom)))
    if kind == "LinearRing":
        return LinearRing(func(shapely.get_coordinates(geom)))
    if kind == "Polygon":
        shell = func(_ring_coords(geom.exterior))
        holes = [func(_ring_coords(r)) for r in geom.interiors]
        return Polygon(shell, holes)
    if kind in ("MultiPoint", "MultiLineString", "MultiPolygon", "GeometryCollection"):
        return type(geom)([_map_coords(g, func) for g in geom.geoms])
    raise TypeError(f"unsupported geometry type: {kind}")


def _ring_coords(ring):
    return np.asarray(ring.coords, dtype=float)[:, :2]


# --------------------------------------------------------------------------- #
# AEQD -> lon/lat, with antimeridian and pole handling
# --------------------------------------------------------------------------- #


def _polygon_to_wgs84(poly, inv, lon0, planar_poles):
    """Inverse-project one planar polygon into an unwrapped lon/lat frame."""
    shell = _ring_to_wgs84(_ring_coords(poly.exterior), inv, lon0)
    holes = []
    for ring in poly.interiors:
        hole = _ring_to_wgs84(_ring_coords(ring), inv, lon0)
        # A hole encircling a pole cannot be expressed as a lon/lat ring; such a
        # polar annulus is pathological, so drop the hole rather than emit junk.
        if abs(hole[-1, 0] - hole[0, 0]) < 180.0:
            holes.append(hole)

    if abs(shell[-1, 0] - shell[0, 0]) > 180.0:
        # The ring winds once around a pole: its unwrapped start and end are 360
        # apart.  Close it over the pole so it covers the cap instead of
        # collapsing to a zero-width sliver.
        outline = Polygon(poly.exterior)
        pole_lat = next(
            (lat for lat, pt in planar_poles if outline.contains(pt)), None
        )
        if pole_lat is not None:
            shell = np.vstack(
                [shell, [[shell[-1, 0], pole_lat], [shell[0, 0], pole_lat]]]
            )
    return Polygon(shell, holes)


def _ring_to_wgs84(coords, inv, lon0):
    lon, lat = inv.transform(
        np.ascontiguousarray(coords[:, 0]), np.ascontiguousarray(coords[:, 1])
    )
    lat = np.clip(np.asarray(lat, dtype=float), -90.0, 90.0)
    return np.column_stack([_unwrap(np.asarray(lon, dtype=float), lon0), lat])


def _unwrap(lons, lon0):
    """Remove 360-degree jumps, anchoring the first vertex near ``lon0``."""
    out = np.empty_like(lons)
    out[0] = lon0 + _wrap180(lons[0] - lon0)
    if out.size > 1:
        out[1:] = out[0] + np.cumsum(_wrap180(np.diff(lons)))
    return out


def _wrap180(x):
    return (np.asarray(x, dtype=float) + 180.0) % 360.0 - 180.0


def _split_antimeridian(geom):
    """Cut an unwrapped-longitude geometry back into the [-180, 180] window."""
    if geom.is_empty:
        return geom
    minx, _, maxx, _ = geom.bounds
    if minx >= -180.0 - _LON_EPS and maxx <= 180.0 + _LON_EPS:
        return geom
    pieces = []
    for k in range(
        math.floor((minx + 180.0) / 360.0), math.floor((maxx + 180.0) / 360.0) + 1
    ):
        shift = 360.0 * k
        piece = geom.intersection(box(-180.0 + shift, -90.0, 180.0 + shift, 90.0))
        if piece.is_empty or piece.area <= 0.0:
            continue
        pieces.extend(_polygons(translate(piece, xoff=-shift)))
    # Halves that meet at the cut line (e.g. a polar cap) are merged back here.
    return unary_union(pieces) if pieces else Polygon()


def _polygons(geom):
    """Flatten a geometry to its list of non-empty ``Polygon`` parts."""
    if geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type in ("MultiPolygon", "GeometryCollection"):
        return [p for part in geom.geoms for p in _polygons(part)]
    return []