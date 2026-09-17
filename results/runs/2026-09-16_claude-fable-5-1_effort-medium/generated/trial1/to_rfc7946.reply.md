```python
"""Convert shapely geometries to RFC 7946 (GeoJSON) geometry objects.

RFC 7946 requires WGS 84 longitude/latitude coordinates, right-hand-rule
polygon winding (exterior rings counterclockwise, holes clockwise), and at
most three coordinate values per position (no measure values).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry.polygon import orient

__all__ = ["to_rfc7946"]

_WGS84 = 4326


def _to_wgs84(geom: shapely.Geometry, epsg: int) -> shapely.Geometry:
    """Reproject geom from the given EPSG code to WGS 84 (lon/lat order)."""
    if geom.is_empty or int(epsg) == _WGS84:
        return geom
    transformer = Transformer.from_crs(
        CRS.from_epsg(int(epsg)), CRS.from_epsg(_WGS84), always_xy=True
    )
    has_z = bool(geom.has_z)

    def _fn(coords: np.ndarray) -> np.ndarray:
        out = np.array(coords, dtype=float, copy=True)
        if out.size == 0:
            return out
        xs, ys = transformer.transform(out[:, 0], out[:, 1])
        out[:, 0] = xs
        out[:, 1] = ys
        if not np.all(np.isfinite(out[:, :2])):
            raise ValueError(
                f"Coordinates could not be transformed from EPSG:{epsg} to EPSG:4326"
            )
        return out

    return shapely.transform(geom, _fn, include_z=has_z)


def _positions(geom: shapely.Geometry, has_z: bool) -> List[List[float]]:
    """Return the coordinate sequence of a single-part geometry as plain floats."""
    arr = shapely.get_coordinates(geom, include_z=has_z)
    out: List[List[float]] = []
    for row in arr:
        pos = [float(v) for v in row]
        if has_z and (len(pos) < 3 or math.isnan(pos[2])):
            pos = pos[:2]
        out.append(pos)
    return out


def _ring(ring: shapely.Geometry, has_z: bool) -> List[List[float]]:
    coords = _positions(ring, has_z)
    if coords and coords[0] != coords[-1]:
        coords.append(list(coords[0]))
    return coords


def _polygon_coords(poly: shapely.Geometry, has_z: bool) -> List[List[List[float]]]:
    if poly.is_empty:
        return []
    # Right-hand rule: exterior counterclockwise, interiors clockwise.
    poly = orient(poly, sign=1.0)
    rings = [_ring(poly.exterior, has_z)]
    rings.extend(_ring(interior, has_z) for interior in poly.interiors)
    return rings


def _encode(geom: shapely.Geometry, has_z: bool) -> Dict[str, Any]:
    gtype = geom.geom_type

    if gtype == "Point":
        coords = _positions(geom, has_z)
        return {"type": "Point", "coordinates": coords[0] if coords else []}

    if gtype in ("LineString", "LinearRing"):
        return {"type": "LineString", "coordinates": _positions(geom, has_z)}

    if gtype == "Polygon":
        return {"type": "Polygon", "coordinates": _polygon_coords(geom, has_z)}

    if gtype == "MultiPoint":
        return {
            "type": "MultiPoint",
            "coordinates": [
                _positions(p, has_z)[0] for p in geom.geoms if not p.is_empty
            ],
        }

    if gtype == "MultiLineString":
        return {
            "type": "MultiLineString",
            "coordinates": [
                _positions(line, has_z) for line in geom.geoms if not line.is_empty
            ],
        }

    if gtype == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [
                _polygon_coords(p, has_z) for p in geom.geoms if not p.is_empty
            ],
        }

    if gtype == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [_encode(g, has_z) for g in geom.geoms],
        }

    raise TypeError(f"Unsupported geometry type: {gtype}")


def to_rfc7946(geom: shapely.Geometry, epsg: int) -> Dict[str, Any]:
    """Return ``geom`` as an RFC 7946 GeoJSON geometry object.

    Parameters
    ----------
    geom : shapely.Geometry
        Input geometry whose coordinates are expressed in ``epsg``.
        Coordinates are interpreted as (x=easting/longitude, y=northing/latitude).
    epsg : int
        EPSG code of the coordinate reference system of ``geom``.

    Returns
    -------
    dict
        A GeoJSON geometry object with ``type`` and ``coordinates`` members
        (or ``geometries`` for a GeometryCollection), in WGS 84 longitude/
        latitude, with polygons following the right-hand rule and measure
        values removed.
    """
    if not isinstance(geom, shapely.Geometry):
        raise TypeError("geom must be a shapely geometry")
    wgs = _to_wgs84(geom, epsg)
    return _encode(wgs, bool(wgs.has_z))
```