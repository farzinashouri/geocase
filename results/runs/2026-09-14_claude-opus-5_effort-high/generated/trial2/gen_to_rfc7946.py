"""Convert shapely geometries into RFC 7946 (GeoJSON) geometry objects.

The single public entry point is :func:`to_rfc7946`.

RFC 7946 pins the coordinate reference system to WGS 84 (EPSG:4326) with
positions ordered longitude, latitude and an optional third element for
elevation, so the source coordinates are reprojected from ``epsg`` before
serialisation.  The conventions this module follows:

* Geometries are always interpreted with ``always_xy=True``, i.e. a geometry
  tagged ``epsg=4326`` is assumed to hold ``(lon, lat)`` vertices, which is the
  usual shapely convention.
* M values are dropped (RFC 7946 has no place for them).  Z is kept only for
  coordinate sequences where every vertex carries a finite Z.
* Polygon exterior rings are emitted counter-clockwise and interior rings
  clockwise (RFC 7946 section 3.1.6).
* Longitudes are wrapped into [-180, 180] and latitudes are clamped to
  [-90, 90]; a reprojection that lands measurably outside those ranges is an
  error, not something to silently truncate.
* 2-D lines and polygons crossing the antimeridian are cut into pieces
  (section 3.1.9).  3-D geometries are only wrapped, not cut, because clipping
  does not carry Z through reliably -- cutting is a SHOULD, valid coordinate
  ranges are a MUST.
* Nested GeometryCollections are flattened (section 3.1.8).

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any, Callable, Dict, List, Sequence

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.affinity import translate
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
    box,
)
from shapely.geometry.base import BaseGeometry

__all__ = ["to_rfc7946"]

WGS84_EPSG = 4326

#: Latitudes are clamped inside this tolerance and rejected beyond it.
_LAT_TOL = 1e-6

_SIMPLE_TYPES = ("Point", "LineString", "LinearRing", "Polygon")
_COLLECTION_TYPES = (
    "MultiPoint",
    "MultiLineString",
    "MultiPolygon",
    "GeometryCollection",
)


# --------------------------------------------------------------------------- #
# projection
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=64)
def _transformer(epsg: int):
    """Return a transformer from ``epsg`` to WGS 84, or ``None`` if it is a no-op."""
    if epsg == WGS84_EPSG:
        return None
    try:
        src = CRS.from_epsg(epsg)
    except Exception as exc:  # pyproj raises CRSError; keep the API honest
        raise ValueError(f"not a usable EPSG code: {epsg!r}") from exc
    return Transformer.from_crs(src, CRS.from_epsg(WGS84_EPSG), always_xy=True)


def _coords(geom: BaseGeometry) -> np.ndarray:
    """Coordinates of a single-sequence geometry as an ``(n, 3)`` array.

    ``include_z=True`` yields NaN for absent Z, and M is excluded, which is how
    both are detected/dropped downstream.
    """
    arr = shapely.get_coordinates(geom, include_z=True)
    return np.asarray(arr, dtype=float).reshape(-1, 3)


def _wrap_lon(lons: np.ndarray) -> np.ndarray:
    """Wrap longitudes into [-180, 180], leaving in-range values untouched."""
    out = np.asarray(lons, dtype=float).copy()
    outside = (out < -180.0) | (out > 180.0)
    if outside.any():
        out[outside] = ((out[outside] + 180.0) % 360.0) - 180.0
    return out


def _unwrap_lon(lons: np.ndarray) -> np.ndarray:
    """Make a longitude sequence continuous: every step is made < 180 degrees.

    The first vertex is placed in [-180, 180]; later vertices may fall outside
    it so that a sequence crossing the antimeridian stays connected.  The
    antimeridian cut later folds everything back into range.
    """
    wrapped = _wrap_lon(lons)
    if wrapped.size < 2:
        return wrapped
    steps = np.diff(wrapped)
    out = wrapped.copy()
    out[1:] += np.cumsum(-360.0 * np.round(steps / 360.0))
    return out


def _clamp_lat(lats: np.ndarray) -> np.ndarray:
    if lats.size and (
        (lats < -90.0 - _LAT_TOL).any() or (lats > 90.0 + _LAT_TOL).any()
    ):
        raise ValueError(
            "reprojected latitudes fall outside [-90, 90]; check the EPSG code "
            "and the axis order of the input geometry"
        )
    return np.clip(lats, -90.0, 90.0)


def _project_seq(arr: np.ndarray, transformer) -> np.ndarray:
    """Reproject one coordinate sequence and normalise it to lon/lat degrees."""
    if arr.shape[0] == 0:
        return arr[:, :2]

    x, y, z = arr[:, 0], arr[:, 1], arr[:, 2]
    keep_z = bool(np.isfinite(z).all())

    if transformer is not None:
        if keep_z:
            x, y, z = transformer.transform(x, y, z)
        else:
            x, y = transformer.transform(x, y)
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        z = np.asarray(z, dtype=float)

    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        raise ValueError(
            "reprojection produced non-finite coordinates; the geometry is "
            "probably outside the area of use of the source CRS"
        )

    lon = _unwrap_lon(x)
    lat = _clamp_lat(y)
    if keep_z and np.isfinite(z).all():
        return np.column_stack((lon, lat, z))
    return np.column_stack((lon, lat))


def _wrap_seq(arr: np.ndarray) -> np.ndarray:
    """Fold an already-projected sequence back into [-180, 180] without cutting."""
    if arr.shape[0] == 0:
        return arr[:, :2]
    lon = _wrap_lon(arr[:, 0])
    lat = arr[:, 1]
    z = arr[:, 2]
    if np.isfinite(z).all():
        return np.column_stack((lon, lat, z))
    return np.column_stack((lon, lat))


# --------------------------------------------------------------------------- #
# structural rebuild
# --------------------------------------------------------------------------- #


def _align_hole(hole: np.ndarray, shell: np.ndarray) -> np.ndarray:
    """Shift an interior ring by whole turns so it shares the shell's frame.

    Unwrapping starts each ring from its own first vertex, so a shell running
    170 -> 190 can end up with a hole at -182 -> -178, i.e. a full turn away and
    no longer inside its shell.
    """
    if hole.shape[0] == 0 or shell.shape[0] == 0:
        return hole
    shift = 360.0 * round((shell[:, 0].mean() - hole[:, 0].mean()) / 360.0)
    if shift:
        hole = hole.copy()
        hole[:, 0] += shift
    return hole


def _check_ring_closed(ring: np.ndarray) -> None:
    if ring.shape[0] and abs(ring[0, 0] - ring[-1, 0]) > 180.0:
        raise ValueError(
            "polygon ring encircles a pole; RFC 7946 has no representation for "
            "it without inserting vertices at the pole, which this function "
            "does not do"
        )


def _rebuild(
    geom: BaseGeometry,
    seq_fn: Callable[[np.ndarray], np.ndarray],
    align_holes: bool,
) -> BaseGeometry:
    """Rebuild ``geom``, applying ``seq_fn`` to each coordinate sequence."""
    gtype = geom.geom_type

    if gtype == "LinearRing":
        # RFC 7946 has no LinearRing; a standalone one becomes a LineString.
        gtype = "LineString"
    if gtype not in _SIMPLE_TYPES + _COLLECTION_TYPES:
        raise ValueError(f"unsupported geometry type: {geom.geom_type}")

    if geom.is_empty:
        return LineString() if gtype == "LineString" else geom

    if gtype == "Point":
        return Point(seq_fn(_coords(geom))[0])

    if gtype == "LineString":
        return LineString(seq_fn(_coords(geom)))

    if gtype == "Polygon":
        shell = seq_fn(_coords(geom.exterior))
        _check_ring_closed(shell)
        holes = []
        for ring in geom.interiors:
            hole = seq_fn(_coords(ring))
            _check_ring_closed(hole)
            if align_holes:
                hole = _align_hole(hole, shell)
            holes.append(hole)
        return Polygon(shell, holes)

    parts = [_rebuild(part, seq_fn, align_holes) for part in geom.geoms]
    return type(geom)(parts)


def _parts(geom: BaseGeometry) -> List[BaseGeometry]:
    if geom.geom_type in _COLLECTION_TYPES:
        return list(geom.geoms)
    return [geom]


# --------------------------------------------------------------------------- #
# antimeridian cutting (RFC 7946 section 3.1.9)
# --------------------------------------------------------------------------- #


def _cut_simple(geom: BaseGeometry) -> BaseGeometry:
    """Cut one line/polygon spanning past +-180 into per-band pieces."""
    minx, miny, maxx, maxy = geom.bounds
    if minx >= -180.0 and maxx <= 180.0:
        return geom

    ylo = min(miny, -90.0) - 1.0
    yhi = max(maxy, 90.0) + 1.0
    first = math.ceil((minx - 180.0) / 360.0)
    last = math.floor((maxx + 180.0) / 360.0)
    dim = shapely.get_dimensions(geom)

    pieces: List[BaseGeometry] = []
    for turn in range(first, last + 1):
        offset = 360.0 * turn
        clipped = geom.intersection(box(-180.0 + offset, ylo, 180.0 + offset, yhi))
        if clipped.is_empty:
            continue
        clipped = translate(clipped, xoff=-offset)
        # Touching a band edge yields lower-dimensional slivers; drop them.
        pieces.extend(
            p
            for p in _parts(clipped)
            if not p.is_empty and shapely.get_dimensions(p) == dim
        )

    if not pieces:
        raise ValueError("antimeridian cut removed the whole geometry")
    if len(pieces) == 1:
        return pieces[0]
    return MultiLineString(pieces) if dim == 1 else MultiPolygon(pieces)


def _cut_antimeridian(geom: BaseGeometry) -> BaseGeometry:
    gtype = geom.geom_type
    if geom.is_empty or gtype in ("Point", "MultiPoint"):
        return geom  # single positions are already wrapped into range
    if gtype == "GeometryCollection":
        return GeometryCollection([_cut_antimeridian(g) for g in geom.geoms])
    if gtype in ("MultiLineString", "MultiPolygon"):
        pieces: List[BaseGeometry] = []
        for part in geom.geoms:
            pieces.extend(_parts(_cut_antimeridian(part)))
        return type(geom)(pieces)
    return _cut_simple(geom)


def _unnest(geom: BaseGeometry) -> BaseGeometry:
    """Flatten nested GeometryCollections (RFC 7946 section 3.1.8)."""
    if geom.geom_type != "GeometryCollection":
        return geom
    flat: List[BaseGeometry] = []

    def walk(collection: BaseGeometry) -> None:
        for part in collection.geoms:
            if part.geom_type == "GeometryCollection":
                walk(part)
            else:
                flat.append(part)

    walk(geom)
    return GeometryCollection(flat)


# --------------------------------------------------------------------------- #
# serialisation
# --------------------------------------------------------------------------- #


def _positions(arr: np.ndarray) -> List[List[float]]:
    if not np.isfinite(arr).all():
        raise ValueError("geometry contains non-finite coordinates")
    return [[float(v) for v in row] for row in arr]


def _ring(ring: BaseGeometry, counter_clockwise: bool) -> List[List[float]]:
    arr = _coords(ring)
    if arr.shape[1] == 3 and not np.isfinite(arr[:, 2]).all():
        arr = arr[:, :2]
    if bool(ring.is_ccw) != counter_clockwise:
        arr = arr[::-1]
    return _positions(arr)


def _drop_nan_z(arr: np.ndarray) -> np.ndarray:
    return arr if np.isfinite(arr[:, 2]).all() else arr[:, :2]


def _geometry_dict(geom: BaseGeometry) -> Dict[str, Any]:
    gtype = geom.geom_type

    if gtype == "Point":
        if geom.is_empty:
            raise ValueError(
                "an empty Point has no RFC 7946 representation: a position must "
                "have at least two numbers"
            )
        return {"type": "Point", "coordinates": _positions(_drop_nan_z(_coords(geom)))[0]}

    if gtype in ("LineString", "LinearRing"):
        if geom.is_empty:
            raise ValueError(
                "an empty LineString has no RFC 7946 representation: at least "
                "two positions are required"
            )
        return {
            "type": "LineString",
            "coordinates": _positions(_drop_nan_z(_coords(geom))),
        }

    if gtype == "Polygon":
        if geom.is_empty:
            return {"type": "Polygon", "coordinates": []}
        rings = [_ring(geom.exterior, counter_clockwise=True)]
        rings.extend(_ring(r, counter_clockwise=False) for r in geom.interiors)
        return {"type": "Polygon", "coordinates": rings}

    if gtype == "MultiPoint":
        return {
            "type": "MultiPoint",
            "coordinates": [_geometry_dict(p)["coordinates"] for p in geom.geoms],
        }

    if gtype == "MultiLineString":
        return {
            "type": "MultiLineString",
            "coordinates": [_geometry_dict(ls)["coordinates"] for ls in geom.geoms],
        }

    if gtype == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [_geometry_dict(p)["coordinates"] for p in geom.geoms],
        }

    if gtype == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [_geometry_dict(g) for g in geom.geoms],
        }

    raise ValueError(f"unsupported geometry type: {gtype}")


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #


def to_rfc7946(geom: BaseGeometry, epsg: int) -> Dict[str, Any]:
    """Return ``geom`` as an RFC 7946 GeoJSON geometry object.

    Parameters
    ----------
    geom:
        A shapely geometry whose coordinates are expressed in ``epsg``.  Under
        the usual shapely convention the first ordinate is easting/longitude.
    epsg:
        Integer EPSG code of the geometry's CRS (e.g. ``4326``, ``3857``).

    Returns
    -------
    dict
        A GeoJSON geometry object -- ``type`` plus ``coordinates`` (or
        ``geometries`` for a GeometryCollection) -- in WGS 84 lon/lat degrees.
        No ``crs`` member is emitted; RFC 7946 removed it.

    Raises
    ------
    TypeError
        If ``geom`` is not a shapely geometry or ``epsg`` is not an integer.
    ValueError
        For an unsupported or empty-but-unrepresentable geometry, an unusable
        EPSG code, a reprojection that fails or leaves the valid lat range, or
        a polygon ring that encircles a pole.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"expected a shapely geometry, got {type(geom).__name__}")
    if isinstance(epsg, bool) or not isinstance(epsg, (int, np.integer)):
        raise TypeError(f"expected an integer EPSG code, got {type(epsg).__name__}")

    transformer = _transformer(int(epsg))
    wgs84 = _rebuild(
        geom,
        lambda arr: _project_seq(arr, transformer),
        align_holes=True,
    )

    # Only cut 2-D geometries: clipping does not carry Z through dependably, and
    # cutting is a SHOULD while in-range coordinates are a MUST.
    coords = shapely.get_coordinates(wgs84, include_z=True)
    has_z = coords.size > 0 and bool(np.isfinite(coords[:, 2]).any())
    if has_z:
        wgs84 = _rebuild(wgs84, _wrap_seq, align_holes=False)
    else:
        wgs84 = _cut_antimeridian(wgs84)

    return _geometry_dict(_unnest(wgs84))