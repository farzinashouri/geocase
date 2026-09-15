```python
"""Convert shapely geometries to RFC 7946 GeoJSON geometry objects.

Importing this module has no side effects.

RFC 7946 fixes the coordinate reference system to WGS 84 longitude/latitude
(EPSG:4326, axis order longitude-then-latitude), so geometries given in any
other CRS are reprojected here.  The RFC's other geometry-level rules are
applied as well: polygon rings follow the right-hand rule (exterior
counterclockwise, interior clockwise), rings are explicitly closed,
GeometryCollections are never nested, and longitudes are normalised into
[-180, 180].
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Sequence

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry, BaseMultipartGeometry

__all__ = ["to_rfc7946"]

_WGS84 = CRS.from_epsg(4326)

# Transformers are cheap to reuse and expensive to build; cache per source CRS.
_TRANSFORMER_CACHE: Dict[int, Transformer] = {}


def _transformer(epsg: int) -> Transformer:
    transformer = _TRANSFORMER_CACHE.get(epsg)
    if transformer is None:
        # always_xy: interpret input as (x, y) and emit (longitude, latitude),
        # regardless of the authority-defined axis order of either CRS.
        transformer = Transformer.from_crs(
            CRS.from_epsg(epsg), _WGS84, always_xy=True
        )
        _TRANSFORMER_CACHE[epsg] = transformer
    return transformer


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180], leaving the poles' +/-180 intact."""
    if not math.isfinite(lon):
        raise ValueError("non-finite longitude after reprojection")
    if -180.0 <= lon <= 180.0:
        return lon
    wrapped = math.fmod(lon + 180.0, 360.0)
    if wrapped < 0.0:
        wrapped += 360.0
    return wrapped - 180.0


def _clamp_lat(lat: float) -> float:
    if not math.isfinite(lat):
        raise ValueError("non-finite latitude after reprojection")
    # Guard against tiny floating-point overshoot at the poles.
    return min(90.0, max(-90.0, lat))


def _position(coord: Sequence[float], transformer: Transformer | None) -> List[float]:
    x, y = float(coord[0]), float(coord[1])
    z = float(coord[2]) if len(coord) > 2 else None
    if transformer is not None:
        if z is None:
            x, y = transformer.transform(x, y)
        else:
            x, y, z = transformer.transform(x, y, z)
    position = [_normalize_lon(x), _clamp_lat(y)]
    if z is not None and math.isfinite(z):
        position.append(z)
    return position


def _positions(
    coords: Iterable[Sequence[float]], transformer: Transformer | None
) -> List[List[float]]:
    return [_position(c, transformer) for c in coords]


def _ring(coords: Sequence[Sequence[float]], transformer) -> List[List[float]]:
    ring = _positions(coords, transformer)
    if ring and ring[0] != ring[-1]:
        ring.append(list(ring[0]))
    return ring


def _signed_area(ring: Sequence[Sequence[float]]) -> float:
    """Shoelace area of a closed ring; positive when counterclockwise."""
    total = 0.0
    for (x1, y1, *_), (x2, y2, *_) in zip(ring, ring[1:]):
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _wind(ring: List[List[float]], counterclockwise: bool) -> List[List[float]]:
    if len(ring) < 4:
        return ring
    is_ccw = _signed_area(ring) > 0.0
    return ring if is_ccw == counterclockwise else ring[::-1]


def _polygon_rings(polygon, transformer) -> List[List[List[float]]]:
    rings = [_wind(_ring(polygon.exterior.coords, transformer), True)]
    rings.extend(
        _wind(_ring(interior.coords, transformer), False)
        for interior in polygon.interiors
    )
    return rings


def _convert(geom: BaseGeometry, transformer) -> Dict[str, Any]:
    geom_type = geom.geom_type

    if geom_type == "GeometryCollection":
        # RFC 7946 discourages nesting; flatten any collection-of-collections.
        members: List[Dict[str, Any]] = []
        for part in geom.geoms:
            converted = _convert(part, transformer)
            if converted["type"] == "GeometryCollection":
                members.extend(converted["geometries"])
            else:
                members.append(converted)
        return {"type": "GeometryCollection", "geometries": members}

    if geom.is_empty:
        # An empty geometry has no positions; an empty coordinate array is the
        # RFC 7946 representation (Point included, per the "unlocated" note).
        return {"type": "Point" if geom_type == "Point" else geom_type,
                "coordinates": []}

    if geom_type == "Point":
        return {"type": "Point",
                "coordinates": _position(geom.coords[0], transformer)}

    if geom_type in ("LineString", "LinearRing"):
        # RFC 7946 has no LinearRing type; it is emitted as a LineString.
        return {"type": "LineString",
                "coordinates": _positions(geom.coords, transformer)}

    if geom_type == "Polygon":
        return {"type": "Polygon", "coordinates": _polygon_rings(geom, transformer)}

    if geom_type == "MultiPoint":
        return {
            "type": "MultiPoint",
            "coordinates": [_position(p.coords[0], transformer) for p in geom.geoms],
        }

    if geom_type == "MultiLineString":
        return {
            "type": "MultiLineString",
            "coordinates": [_positions(ls.coords, transformer) for ls in geom.geoms],
        }

    if geom_type == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [_polygon_rings(p, transformer) for p in geom.geoms],
        }

    raise ValueError(f"unsupported geometry type: {geom_type}")


def to_rfc7946(geom: BaseGeometry, epsg: int) -> Dict[str, Any]:
    """Return ``geom`` as an RFC 7946 GeoJSON geometry ``dict``.

    Parameters
    ----------
    geom:
        A shapely geometry whose coordinates are expressed in ``epsg``.
    epsg:
        Integer EPSG code of the geometry's coordinate reference system
        (for example ``4326`` or ``3857``).

    The result contains only the geometry object -- ``type`` plus
    ``coordinates`` (or ``geometries`` for a GeometryCollection) -- with
    coordinates reprojected to WGS 84 longitude/latitude.
    """
    if not isinstance(geom, (BaseGeometry, BaseMultipartGeometry)):
        raise TypeError("geom must be a shapely geometry")
    if isinstance(epsg, bool) or not isinstance(epsg, int):
        raise TypeError("epsg must be an integer EPSG code")

    source = CRS.from_epsg(epsg)
    transformer = None if source.equals(_WGS84) else _transformer(epsg)
    return _convert(geom, transformer)
```