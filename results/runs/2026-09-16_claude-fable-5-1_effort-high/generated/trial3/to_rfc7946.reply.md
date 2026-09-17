Here is the module.

```python
"""Convert a shapely geometry to an RFC 7946 GeoJSON geometry object.

``to_rfc7946(geom, epsg)`` returns a plain ``dict`` with ``type`` and
``coordinates`` members (``geometries`` for a GeometryCollection) that:

* has its coordinates reprojected to WGS 84 (EPSG:4326) in longitude,
  latitude order, as required by RFC 7946 section 4;
* follows the right-hand rule for polygon rings (exterior counterclockwise,
  holes clockwise), as required by section 3.1.6;
* keeps rings closed, keeps an optional altitude as a third element, drops
  any missing (NaN) altitude, and contains only Python ``float`` values;
* carries no ``crs`` or ``bbox`` member and flattens nested
  GeometryCollections (section 3.1.8).

Antimeridian cutting (section 3.1.9, a SHOULD) is not performed.
Importing this module has no side effects.
"""

from __future__ import annotations

import math
import operator
from typing import Any, Iterator

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry

__all__ = ["to_rfc7946"]

_WGS84 = 4326


def to_rfc7946(geom: BaseGeometry, epsg: int) -> dict[str, Any]:
    """Return ``geom`` (whose coordinates are in ``EPSG:epsg``) as an RFC 7946
    GeoJSON geometry object.

    Raises ``TypeError`` for non-shapely input, ``ValueError`` for an unknown
    geometry type or coordinates that cannot be projected to WGS 84, and a
    ``pyproj`` error for an unknown EPSG code.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"expected a shapely geometry, got {type(geom).__name__}")
    epsg = operator.index(epsg)
    return _build(_reproject(geom, epsg))


# --------------------------------------------------------------------------- #
# Reprojection
# --------------------------------------------------------------------------- #


def _reproject(geom: BaseGeometry, epsg: int) -> BaseGeometry:
    if epsg == _WGS84 or geom.is_empty:
        return geom

    transformer = Transformer.from_crs(
        CRS.from_epsg(epsg), CRS.from_epsg(_WGS84), always_xy=True
    )
    has_z = bool(shapely.has_z(geom))

    def _transform(coords: np.ndarray) -> np.ndarray:
        if has_z:
            x, y, z = transformer.transform(coords[:, 0], coords[:, 1], coords[:, 2])
            out = np.column_stack([x, y, z])
        else:
            x, y = transformer.transform(coords[:, 0], coords[:, 1])
            out = np.column_stack([x, y])
        if not np.all(np.isfinite(out[:, :2])):
            raise ValueError(
                f"some coordinates could not be transformed from EPSG:{epsg} to WGS 84"
            )
        return out

    return shapely.transform(geom, _transform, include_z=has_z)


# --------------------------------------------------------------------------- #
# Coordinate serialisation
# --------------------------------------------------------------------------- #


def _coords(geom: BaseGeometry) -> np.ndarray:
    return shapely.get_coordinates(geom, include_z=bool(shapely.has_z(geom)))


def _positions(coords: np.ndarray) -> list[list[float]]:
    positions: list[list[float]] = []
    for row in coords:
        position = [float(row[0]), float(row[1])]
        if len(row) > 2 and math.isfinite(row[2]):
            position.append(float(row[2]))
        positions.append(position)
    return positions


def _signed_area(ring: list[list[float]]) -> float:
    area = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def _ring(geom: BaseGeometry, clockwise: bool) -> list[list[float]]:
    points = _positions(_coords(geom))
    if points and points[0] != points[-1]:
        points.append(list(points[0]))
    area = _signed_area(points)
    if (clockwise and area > 0.0) or (not clockwise and area < 0.0):
        points.reverse()
    return points


def _polygon(geom: BaseGeometry) -> list[list[list[float]]]:
    if geom.is_empty:
        return []
    rings = [_ring(geom.exterior, clockwise=False)]
    rings.extend(_ring(hole, clockwise=True) for hole in geom.interiors)
    return rings


def _flatten(collection: BaseGeometry) -> Iterator[BaseGeometry]:
    for part in collection.geoms:
        if part.geom_type == "GeometryCollection":
            yield from _flatten(part)
        else:
            yield part


def _build(geom: BaseGeometry) -> dict[str, Any]:
    kind = geom.geom_type

    if kind == "Point":
        coordinates: Any = [] if geom.is_empty else _positions(_coords(geom))[0]
        return {"type": "Point", "coordinates": coordinates}

    if kind in ("LineString", "LinearRing"):
        return {"type": "LineString", "coordinates": _positions(_coords(geom))}

    if kind == "Polygon":
        return {"type": "Polygon", "coordinates": _polygon(geom)}

    if kind == "MultiPoint":
        coordinates = [
            _positions(_coords(part))[0] for part in geom.geoms if not part.is_empty
        ]
        return {"type": "MultiPoint", "coordinates": coordinates}

    if kind == "MultiLineString":
        coordinates = [
            _positions(_coords(part)) for part in geom.geoms if not part.is_empty
        ]
        return {"type": "MultiLineString", "coordinates": coordinates}

    if kind == "MultiPolygon":
        coordinates = [_polygon(part) for part in geom.geoms if not part.is_empty]
        return {"type": "MultiPolygon", "coordinates": coordinates}

    if kind == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [_build(part) for part in _flatten(geom)],
        }

    raise ValueError(f"unsupported geometry type: {kind}")
```