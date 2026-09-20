"""Convert shapely geometries to RFC 7946 GeoJSON geometry objects.

Importing this module has no side effects.

The only public entry point is :func:`to_rfc7946`.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any, Dict, List, Sequence

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry

__all__ = ["to_rfc7946"]

# RFC 7946 section 11.2: six decimal places (~10 cm) is plenty for WGS 84
# degrees, and trimming there keeps output stable and compact.
_DECIMALS = 6
_WGS84 = "EPSG:4326"


@lru_cache(maxsize=32)
def _transformer(epsg: int) -> Transformer | None:
    """Return a lon/lat transformer for ``epsg``, or None if already WGS 84.

    ``always_xy=True`` makes both ends longitude-first regardless of the
    authority-declared axis order (EPSG:4326 is officially lat, lon).
    """
    src = CRS.from_epsg(epsg)
    dst = CRS.from_epsg(4326)
    if src.equals(dst):
        return None
    return Transformer.from_crs(src, dst, always_xy=True)


def _round(value: float) -> float:
    r = round(float(value), _DECIMALS)
    # Normalise -0.0 to 0.0 so equal positions compare equal.
    return r + 0.0


def _position(coord: Sequence[float], tr: Transformer | None) -> List[float]:
    x, y = float(coord[0]), float(coord[1])
    z = float(coord[2]) if len(coord) > 2 else None

    if tr is not None:
        x, y = tr.transform(x, y)

    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError(f"non-finite coordinate after transform: ({x}, {y})")

    # RFC 7946 restricts the CRS to WGS 84 in decimal degrees.
    if not -180.0 <= x <= 180.0 or not -90.0 <= y <= 90.0:
        raise ValueError(f"position out of WGS 84 range: ({x}, {y})")

    pos = [_round(x), _round(y)]
    if z is not None:
        if not math.isfinite(z):
            raise ValueError(f"non-finite elevation: {z}")
        # Altitudes are metres above the ellipsoid and are passed through
        # unchanged: a 2D horizontal transform says nothing about height.
        pos.append(_round(z))
    return pos


def _line(coords: Sequence[Sequence[float]], tr: Transformer | None) -> List[List[float]]:
    return [_position(c, tr) for c in coords]


def _signed_area(ring: Sequence[Sequence[float]]) -> float:
    """Twice the signed shoelace area; positive means counterclockwise."""
    total = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        total += x1 * y2 - x2 * y1
    return total


def _ring(coords: Sequence[Sequence[float]], tr: Transformer | None, ccw: bool) -> List[List[float]]:
    """Transform a linear ring and wind it per RFC 7946 section 3.1.6."""
    out = _line(coords, tr)
    if out and out[0] != out[-1]:  # shapely normally closes rings already
        out.append(list(out[0]))
    if len(out) < 4:
        raise ValueError("a linear ring needs at least four positions")
    if (_signed_area(out) >= 0.0) != ccw:
        out.reverse()
    return out


def _polygon(poly, tr: Transformer | None) -> List[List[List[float]]]:
    # Exterior ring counterclockwise, holes clockwise.
    rings = [_ring(poly.exterior.coords, tr, ccw=True)]
    rings.extend(_ring(interior.coords, tr, ccw=False) for interior in poly.interiors)
    return rings


def to_rfc7946(geom: BaseGeometry, epsg: int) -> Dict[str, Any]:
    """Return ``geom`` as an RFC 7946 GeoJSON geometry object.

    Parameters
    ----------
    geom:
        A shapely geometry whose coordinates are expressed in ``epsg``.
    epsg:
        Integer EPSG code of the geometry's coordinate reference system,
        e.g. ``4326`` or ``3857``. Coordinates are reprojected to WGS 84
        longitude/latitude as RFC 7946 requires.

    Returns
    -------
    dict
        A geometry object with ``type`` and ``coordinates`` members (or
        ``type`` and ``geometries`` for a GeometryCollection), containing
        only JSON-serialisable values.

    Notes
    -----
    Geometries crossing the antimeridian are not split into multipart
    geometries; RFC 7946 section 3.1.9 states that only as a SHOULD, and
    splitting would change the geometry's structure.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"expected a shapely geometry, got {type(geom).__name__}")
    if isinstance(epsg, bool) or not isinstance(epsg, int):
        raise TypeError("epsg must be an integer EPSG code")

    tr = _transformer(epsg)
    kind = geom.geom_type

    if kind == "GeometryCollection":
        # A GeometryCollection carries "geometries", never "coordinates",
        # and must not nest another GeometryCollection (section 3.1.8).
        parts = []
        for part in geom.geoms:
            if part.geom_type == "GeometryCollection":
                raise ValueError("nested GeometryCollections are not allowed")
            parts.append(to_rfc7946(part, epsg))
        return {"type": "GeometryCollection", "geometries": parts}

    if geom.is_empty:
        # RFC 7946 has no null geometry: an empty geometry is an empty
        # coordinates array. A Point cannot express emptiness at all.
        if kind == "Point":
            raise ValueError("an empty Point has no RFC 7946 representation")
        return {"type": kind, "coordinates": []}

    if kind == "Point":
        coords: Any = _position(geom.coords[0], tr)
    elif kind == "LineString":
        coords = _line(geom.coords, tr)
        if len(coords) < 2:
            raise ValueError("a LineString needs at least two positions")
    elif kind == "LinearRing":
        # Not an RFC 7946 type; emit it as the LineString it is.
        return {"type": "LineString", "coordinates": _line(geom.coords, tr)}
    elif kind == "Polygon":
        coords = _polygon(geom, tr)
    elif kind == "MultiPoint":
        coords = [_position(p.coords[0], tr) for p in geom.geoms]
    elif kind == "MultiLineString":
        coords = [_line(ls.coords, tr) for ls in geom.geoms]
    elif kind == "MultiPolygon":
        coords = [_polygon(p, tr) for p in geom.geoms]
    else:
        raise ValueError(f"unsupported geometry type: {kind}")

    return {"type": kind, "coordinates": coords}