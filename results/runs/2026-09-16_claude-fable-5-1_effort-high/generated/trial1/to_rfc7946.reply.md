```python
"""Convert shapely geometries to RFC 7946 (GeoJSON) geometry objects.

The single public entry point is :func:`to_rfc7946`.  It reprojects the
geometry to WGS 84 (EPSG:4326) with longitude/latitude axis order, enforces
the right-hand rule for polygon rings, and emits plain Python ``dict``/``list``
/``float`` structures with only ``type`` and ``coordinates`` (or, for a
GeometryCollection, ``type`` and ``geometries``) members.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry

__all__ = ["to_rfc7946"]

_WGS84_EPSG = 4326


@lru_cache(maxsize=64)
def _transformer(epsg: int) -> Transformer:
    """Return a cached transformer from ``epsg`` to WGS 84 in x/y (lon/lat) order."""
    return Transformer.from_crs(
        CRS.from_epsg(epsg), CRS.from_epsg(_WGS84_EPSG), always_xy=True
    )


def _to_wgs84(geom: BaseGeometry, epsg: int) -> BaseGeometry:
    """Reproject ``geom`` from ``epsg`` to WGS 84 longitude/latitude.

    Z values (altitude) are carried through; M values are dropped because
    RFC 7946 positions allow at most three elements.
    """
    has_z = bool(shapely.has_z(geom))
    geom = shapely.force_3d(geom) if has_z else shapely.force_2d(geom)
    transformer = _transformer(epsg)

    def _reproject(coords: np.ndarray) -> np.ndarray:
        if coords.shape[0] == 0:
            return coords
        if has_z:
            x, y, z = transformer.transform(coords[:, 0], coords[:, 1], coords[:, 2])
            out = np.column_stack([x, y, z]).astype(float)
        else:
            x, y = transformer.transform(coords[:, 0], coords[:, 1])
            out = np.column_stack([x, y]).astype(float)
        if not np.all(np.isfinite(out[:, :2])):
            raise ValueError(
                f"coordinates could not be transformed from EPSG:{epsg} to WGS 84"
            )
        # Remove floating-point overshoot such as 180.00000000000003.
        out[:, 0] = np.clip(out[:, 0], -180.0, 180.0)
        out[:, 1] = np.clip(out[:, 1], -90.0, 90.0)
        return out

    return shapely.transform(geom, _reproject, include_z=has_z)


def _position(coord: Any) -> list[float]:
    """Convert one coordinate tuple to a list of plain finite Python floats."""
    pos = [float(v) for v in coord]
    if any(not math.isfinite(v) for v in pos):
        raise ValueError("GeoJSON positions must be finite numbers")
    return pos


def _positions(coords: Any) -> list[list[float]]:
    return [_position(c) for c in coords]


def _polygon_rings(poly: BaseGeometry) -> list[list[list[float]]]:
    if poly.is_empty:
        return []
    rings = [_positions(poly.exterior.coords)]
    rings.extend(_positions(interior.coords) for interior in poly.interiors)
    return rings


def _geometry_object(geom: BaseGeometry) -> dict[str, Any]:
    """Build the GeoJSON geometry object for an already-WGS84, oriented geometry."""
    kind = geom.geom_type

    if kind == "Point":
        coords = [] if geom.is_empty else _position(geom.coords[0])
        return {"type": "Point", "coordinates": coords}

    if kind in ("LineString", "LinearRing"):
        # LinearRing is not a GeoJSON type; it is emitted as a LineString.
        return {"type": "LineString", "coordinates": _positions(geom.coords)}

    if kind == "Polygon":
        return {"type": "Polygon", "coordinates": _polygon_rings(geom)}

    if kind == "MultiPoint":
        return {
            "type": "MultiPoint",
            "coordinates": [_position(p.coords[0]) for p in geom.geoms if not p.is_empty],
        }

    if kind == "MultiLineString":
        return {
            "type": "MultiLineString",
            "coordinates": [_positions(line.coords) for line in geom.geoms if not line.is_empty],
        }

    if kind == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [_polygon_rings(poly) for poly in geom.geoms if not poly.is_empty],
        }

    if kind == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [_geometry_object(g) for g in geom.geoms],
        }

    raise TypeError(f"unsupported geometry type: {kind}")


def to_rfc7946(geom: BaseGeometry, epsg: int) -> dict[str, Any]:
    """Return ``geom`` as an RFC 7946 GeoJSON geometry object.

    Parameters
    ----------
    geom:
        A shapely geometry whose coordinates are expressed in the CRS
        identified by ``epsg`` (x/easting/longitude first, y/northing/latitude
        second).
    epsg:
        Integer EPSG code of the source coordinate reference system, for
        example ``4326`` or ``3857``.

    Returns
    -------
    dict
        A GeoJSON geometry object with ``type`` and ``coordinates`` members
        (``type`` and ``geometries`` for a GeometryCollection).  Positions are
        WGS 84 ``[longitude, latitude]`` or ``[longitude, latitude, altitude]``
        lists of plain Python floats.  Polygon exterior rings are
        counterclockwise and interior rings clockwise (right-hand rule), and
        every ring is closed.  Empty geometries produce an empty
        ``coordinates`` array.

    Notes
    -----
    RFC 7946 recommends (but does not require) splitting geometries that
    cross the antimeridian; this function does not split them.

    Raises
    ------
    TypeError
        If ``geom`` is not a shapely geometry or ``epsg`` is not an integer.
    ValueError
        If ``epsg`` is unknown or the coordinates cannot be transformed.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError("geom must be a shapely geometry")
    if isinstance(epsg, bool) or not isinstance(epsg, int):
        raise TypeError("epsg must be an integer EPSG code")

    try:
        wgs84 = _to_wgs84(geom, epsg)
    except Exception as exc:  # pyproj raises CRSError for unknown codes
        if isinstance(exc, (ValueError, TypeError)):
            raise
        raise ValueError(f"unable to use EPSG:{epsg}: {exc}") from exc

    # Orientation must be fixed *after* reprojection, since some projections
    # reverse ring winding relative to longitude/latitude space.
    oriented = shapely.orient_polygons(wgs84, exterior_cw=False)
    return _geometry_object(oriented)
```