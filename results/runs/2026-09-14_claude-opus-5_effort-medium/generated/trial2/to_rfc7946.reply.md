```python
"""Convert shapely geometries to RFC 7946 (GeoJSON) geometry objects.

The public entry point is :func:`to_rfc7946`.

Importing this module has no side effects beyond importing ``shapely`` and
``pyproj``.

Notes on strict conformance
---------------------------
* RFC 7946 fixes the CRS to WGS 84 (OGC:CRS84 / EPSG:4326) with positions
  ordered ``[longitude, latitude]`` (and an optional third element,
  elevation in metres).  Input coordinates are therefore reprojected from
  the supplied EPSG code, using ``always_xy=True`` so that the shapely
  convention ``x``/``y`` is honoured on both sides of the transform.
* Linear rings are re-oriented to follow the right-hand rule (RFC 7946
  §3.1.6): exterior rings counter-clockwise, interior rings clockwise.
* ``M`` values have no GeoJSON representation and are dropped; ``Z`` values
  are preserved and passed through unchanged (the transform is horizontal
  only -- no vertical datum shift is applied).
* Geometries that cross the antimeridian are *not* split into a
  ``Multi*`` geometry.  RFC 7946 §3.1.9 states this as a SHOULD, and a
  silent split is more likely to corrupt data than to help; the output is
  still a valid geometry object.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any, Dict, List, Sequence

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry

__all__ = ["to_rfc7946"]

_WGS84 = "EPSG:4326"

# shapely type name -> GeoJSON "type" member.  A bare LinearRing is not a
# GeoJSON type; it is emitted as a (closed) LineString.
_TYPE_MAP = {
    "Point": "Point",
    "MultiPoint": "MultiPoint",
    "LineString": "LineString",
    "LinearRing": "LineString",
    "MultiLineString": "MultiLineString",
    "Polygon": "Polygon",
    "MultiPolygon": "MultiPolygon",
    "GeometryCollection": "GeometryCollection",
}


@lru_cache(maxsize=None)
def _transformer(epsg: int) -> Transformer:
    """Return a cached lon/lat-ordered transformer from ``epsg`` to WGS 84."""
    return Transformer.from_crs(CRS.from_epsg(epsg), _WGS84, always_xy=True)


def _wrap_lon(lon: float) -> float:
    """Fold a longitude into the RFC 7946 range [-180, 180]."""
    if -180.0 <= lon <= 180.0:
        return lon
    wrapped = math.fmod(lon + 180.0, 360.0)
    if wrapped < 0.0:
        wrapped += 360.0
    wrapped -= 180.0
    # fmod maps +540 -> -180; prefer the antimeridian sign of the input.
    if wrapped == -180.0 and lon > 0.0:
        wrapped = 180.0
    return wrapped


def _clean(value: float) -> float:
    """Normalise a float for JSON output (no -0.0, no NaN/Inf)."""
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("geometry contains a non-finite coordinate")
    return value + 0.0  # collapses -0.0 to 0.0


def _position(row: Sequence[float]) -> List[float]:
    """Build one RFC 7946 position from a transformed coordinate row."""
    lon = _wrap_lon(_clean(row[0]))
    lat = _clean(row[1])
    if not -90.0 <= lat <= 90.0:
        # Projections such as EPSG:3857 can overshoot by rounding; clamp
        # the tiny excursions and reject anything genuinely off-globe.
        if lat > 90.0 + 1e-7 or lat < -90.0 - 1e-7:
            raise ValueError(f"latitude {lat} outside [-90, 90] after reprojection")
        lat = max(-90.0, min(90.0, lat))
    position = [lon + 0.0, lat + 0.0]
    if len(row) > 2:
        position.append(_clean(row[2]))
    return position


def _ring_is_ccw(ring: List[List[float]]) -> bool:
    """Sign of the shoelace area of a closed ring in lon/lat space."""
    total = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        total += x1 * y2 - x2 * y1
    return total > 0.0


def _ring_coords(ring: BaseGeometry, ccw: bool) -> List[List[float]]:
    """Emit a closed, ≥4-position ring wound per the right-hand rule."""
    coords = [_position(row) for row in np.asarray(ring.coords, dtype=float)]
    if coords and coords[0] != coords[-1]:
        coords.append(list(coords[0]))
    if len(coords) < 4:
        raise ValueError("a linear ring must have at least four positions")
    if _ring_is_ccw(coords) != ccw:
        coords.reverse()
    return coords


def _coords(geom: BaseGeometry) -> List[Any]:
    """Recursively build the ``coordinates`` member of a simple geometry."""
    kind = geom.geom_type
    if geom.is_empty:
        return []
    if kind == "Point":
        return _position(np.asarray(geom.coords, dtype=float)[0])
    if kind in ("LineString", "LinearRing", "MultiPoint"):
        if kind == "MultiPoint":
            return [_coords(part) for part in geom.geoms]
        return [_position(row) for row in np.asarray(geom.coords, dtype=float)]
    if kind == "Polygon":
        rings = [_ring_coords(geom.exterior, ccw=True)]
        rings.extend(_ring_coords(hole, ccw=False) for hole in geom.interiors)
        return rings
    if kind in ("MultiLineString", "MultiPolygon"):
        return [_coords(part) for part in geom.geoms if not part.is_empty]
    raise ValueError(f"unsupported geometry type: {kind}")


def _build(geom: BaseGeometry) -> Dict[str, Any]:
    """Turn an already-reprojected shapely geometry into a GeoJSON dict."""
    kind = geom.geom_type
    gj_type = _TYPE_MAP.get(kind)
    if gj_type is None:
        raise ValueError(f"unsupported geometry type: {kind}")
    if gj_type == "GeometryCollection":
        # RFC 7946 §3.1.8: the member is "geometries", not "coordinates".
        return {
            "type": "GeometryCollection",
            "geometries": [_build(part) for part in geom.geoms],
        }
    return {"type": gj_type, "coordinates": _coords(geom)}


def to_rfc7946(geom: BaseGeometry, epsg: int) -> Dict[str, Any]:
    """Return ``geom`` as an RFC 7946 GeoJSON geometry object.

    Parameters
    ----------
    geom:
        Any shapely geometry whose coordinates are expressed in ``epsg``.
    epsg:
        Integer EPSG code of the geometry's coordinate reference system
        (for example ``4326`` or ``3857``).

    Returns
    -------
    dict
        A GeoJSON geometry object -- ``{"type": ..., "coordinates": ...}``
        (or ``{"type": "GeometryCollection", "geometries": [...]}``) with
        positions in WGS 84 longitude/latitude order.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"expected a shapely geometry, got {type(geom).__name__}")
    if isinstance(epsg, bool) or not isinstance(epsg, (int, np.integer)):
        raise TypeError("epsg must be an integer EPSG code")
    epsg = int(epsg)

    include_z = bool(shapely.has_z(geom))
    if epsg == 4326:
        # Already lon/lat; run an identity pass so that any M values are
        # dropped in the same way as on the reprojecting path.
        transformation = lambda xy: xy  # noqa: E731
    else:
        transformer = _transformer(epsg)
        def transformation(xy: np.ndarray) -> np.ndarray:
            if include_z:
                x, y, z = transformer.transform(xy[:, 0], xy[:, 1], xy[:, 2])
                return np.column_stack([x, y, z])
            x, y = transformer.transform(xy[:, 0], xy[:, 1])
            return np.column_stack([x, y])

    projected = shapely.transform(
        geom, transformation, include_z=include_z, include_m=False
    )
    return _build(projected)
```