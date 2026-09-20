"""Convert shapely geometries in any EPSG CRS to RFC 7946 GeoJSON geometry dicts."""

from __future__ import annotations

from typing import Any

import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import mapping
from shapely.geometry.polygon import orient

__all__ = ["to_rfc7946"]

_WGS84 = 4326
_PRECISION = 9  # decimal places; RFC 7946 §11.2 notes 6 is ~10 cm, we keep a bit more


def _transformer(epsg: int) -> Transformer:
    return Transformer.from_crs(f"EPSG:{int(epsg)}", f"EPSG:{_WGS84}", always_xy=True)


def _reproject(geom, epsg: int):
    if int(epsg) == _WGS84:
        return geom
    tr = _transformer(epsg)

    def _fn(coords: np.ndarray) -> np.ndarray:
        if coords.shape[1] == 3:
            x, y, z = tr.transform(coords[:, 0], coords[:, 1], coords[:, 2])
            return np.column_stack([x, y, z])
        x, y = tr.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])

    out = shapely.transform(geom, _fn, include_z=geom.has_z)
    if not out.is_empty:
        arr = shapely.get_coordinates(out)
        if not np.all(np.isfinite(arr)):
            raise ValueError("Coordinates could not be transformed to WGS 84")
    return out


def _normalise(coords: np.ndarray) -> np.ndarray:
    """Wrap longitudes to [-180, 180], clamp latitudes to [-90, 90], round."""
    coords = coords.copy()
    lon = coords[:, 0]
    lon = ((lon + 180.0) % 360.0) - 180.0
    # keep exactly 180 as 180 rather than -180 after modulo
    lon[np.isclose(coords[:, 0], 180.0)] = 180.0
    coords[:, 0] = lon
    coords[:, 1] = np.clip(coords[:, 1], -90.0, 90.0)
    coords = np.round(coords, _PRECISION)
    return coords


def _orient(geom):
    """Apply the right-hand rule (RFC 7946 §3.1.6): exterior CCW, holes CW."""
    t = geom.geom_type
    if t == "Polygon":
        return orient(geom, sign=1.0) if not geom.is_empty else geom
    if t == "MultiPolygon":
        return shapely.MultiPolygon([_orient(p) for p in geom.geoms])
    if t == "GeometryCollection":
        return shapely.GeometryCollection([_orient(g) for g in geom.geoms])
    return geom


def _listify(obj: Any) -> Any:
    if isinstance(obj, (tuple, list)):
        return [_listify(o) for o in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    return obj


def _to_dict(geom) -> dict:
    t = geom.geom_type
    if t == "GeometryCollection":
        return {"type": t, "geometries": [_to_dict(g) for g in geom.geoms]}
    m = mapping(geom)
    return {"type": m["type"], "coordinates": _listify(m["coordinates"])}


def to_rfc7946(geom, epsg: int) -> dict:
    """Return ``geom`` (whose coordinates are in ``EPSG:<epsg>``) as an RFC 7946
    GeoJSON geometry object: WGS 84 lon/lat(/alt), right-hand-rule polygons,
    plain ``dict``/``list`` values.
    """
    if geom is None:
        raise TypeError("geom must be a shapely geometry")
    geom = _reproject(geom, epsg)
    if not geom.is_empty:
        geom = shapely.transform(geom, _normalise, include_z=geom.has_z)
    geom = _orient(geom)
    return _to_dict(geom)