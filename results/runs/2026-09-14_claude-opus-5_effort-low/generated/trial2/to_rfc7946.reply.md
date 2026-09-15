```python
"""Convert shapely geometries to RFC 7946 (GeoJSON) geometry objects.

RFC 7946 mandates that GeoJSON coordinates are in WGS 84 (CRS84 / EPSG:4326)
with longitude before latitude, so geometries in any other CRS are reprojected
here.  It also requires the right-hand rule for polygon ring winding order
(exterior rings counterclockwise, interior rings clockwise).

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from typing import Any, Dict

from pyproj import CRS, Transformer
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform

__all__ = ["to_rfc7946"]

# RFC 7946 section 4: GeoJSON uses WGS 84 (a.k.a. urn:ogc:def:crs:OGC::CRS84).
_WGS84_EPSG = 4326

# Section 11.2 suggests ~6 decimal places; 7 keeps ~1 cm of precision while
# still trimming the float noise that reprojection introduces.
_DEFAULT_PRECISION = 7

_SIMPLE_TYPES = frozenset(
    {"Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"}
)

# Transformers are expensive to build and safe to reuse, so cache per EPSG code.
_transformer_cache: Dict[int, Transformer] = {}


def to_rfc7946(geom: BaseGeometry, epsg: int, precision: int = _DEFAULT_PRECISION) -> dict:
    """Return ``geom`` as an RFC 7946 GeoJSON geometry object.

    Parameters
    ----------
    geom:
        A shapely geometry whose coordinates are expressed in ``epsg``.
    epsg:
        Integer EPSG code of the geometry's coordinate reference system, e.g.
        ``4326`` or ``3857``.
    precision:
        Number of decimal places to round output coordinates to.  Pass ``None``
        to keep full float precision.

    Returns
    -------
    dict
        A GeoJSON geometry object with only ``type`` and ``coordinates``
        members (``geometries`` for a GeometryCollection), with coordinates in
        WGS 84 longitude/latitude order.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"geom must be a shapely geometry, got {type(geom).__name__!r}")
    if isinstance(epsg, bool) or not isinstance(epsg, int):
        raise TypeError(f"epsg must be an int EPSG code, got {type(epsg).__name__!r}")
    if precision is not None and (isinstance(precision, bool) or not isinstance(precision, int)):
        raise TypeError("precision must be an int or None")

    geom = _reproject(geom, epsg)
    geom = _orient(geom)

    geojson = mapping(geom)
    return _clean(geojson, precision)


def _reproject(geom: BaseGeometry, epsg: int) -> BaseGeometry:
    """Reproject ``geom`` from ``epsg`` to EPSG:4326, in longitude/latitude order."""
    if epsg == _WGS84_EPSG:
        return geom
    if geom.is_empty:
        # Nothing to transform, and some pipelines choke on empty coordinate arrays.
        return geom

    transformer = _transformer_cache.get(epsg)
    if transformer is None:
        source = CRS.from_epsg(epsg)  # raises for unknown codes
        transformer = Transformer.from_crs(
            source, CRS.from_epsg(_WGS84_EPSG), always_xy=True
        )
        _transformer_cache[epsg] = transformer

    return shapely_transform(transformer.transform, geom)


def _orient(geom: BaseGeometry) -> BaseGeometry:
    """Apply the RFC 7946 right-hand rule to every polygon in ``geom``."""
    geom_type = geom.geom_type
    if geom_type == "Polygon":
        return _orient_polygon(geom)
    if geom_type == "MultiPolygon":
        from shapely.geometry import MultiPolygon

        return MultiPolygon([_orient_polygon(part) for part in geom.geoms])
    if geom_type == "GeometryCollection":
        from shapely.geometry import GeometryCollection

        return GeometryCollection([_orient(part) for part in geom.geoms])
    return geom


def _orient_polygon(polygon):
    from shapely.geometry import Polygon

    if polygon.is_empty:
        return polygon
    shell = polygon.exterior
    if not _is_ccw(shell):
        shell = shell.reverse()
    holes = [ring if _is_ccw(ring) is False else ring.reverse() for ring in polygon.interiors]
    return Polygon(shell, holes)


def _is_ccw(ring) -> bool:
    """Signed-area test that ignores any Z ordinate."""
    return ring.is_ccw


def _clean(node: Any, precision: int | None) -> Any:
    """Recursively turn the mapping into plain lists/floats with valid values."""
    if isinstance(node, dict):
        out: Dict[str, Any] = {"type": node["type"]}
        if node["type"] == "GeometryCollection":
            out["geometries"] = [_clean(g, precision) for g in node["geometries"]]
        elif node["type"] in _SIMPLE_TYPES:
            out["coordinates"] = _clean(node["coordinates"], precision)
        else:
            raise ValueError(f"unsupported geometry type for RFC 7946: {node['type']!r}")
        return out

    if isinstance(node, (list, tuple)):
        if node and isinstance(node[0], (int, float)):
            return _clean_position(node, precision)
        return [_clean(item, precision) for item in node]

    raise ValueError(f"unexpected value in geometry mapping: {node!r}")


def _clean_position(position, precision: int | None) -> list:
    """Normalise one position: lon/lat in range, finite, optional elevation."""
    values = [float(v) for v in position]
    if len(values) not in (2, 3):
        raise ValueError(f"positions must have 2 or 3 ordinates, got {len(values)}")
    if any(not math.isfinite(v) for v in values):
        raise ValueError(f"non-finite coordinate in geometry: {position!r}")

    lon, lat = values[0], values[1]
    if not -180.0 <= lon <= 180.0:
        lon = ((lon + 180.0) % 360.0) - 180.0
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude {lat} is outside [-90, 90]; is EPSG code correct?")

    values[0], values[1] = lon, lat
    if precision is not None:
        # round() can emit -0.0; adding 0.0 normalises it back to 0.0.
        values = [round(v, precision) + 0.0 for v in values]
    return values
```