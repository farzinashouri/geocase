```python
"""Convert shapely geometries in an arbitrary CRS to RFC 7946 GeoJSON geometry dicts."""

from __future__ import annotations

from pyproj import Transformer
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry
from shapely.geometry.multipolygon import MultiPolygon
from shapely.geometry.collection import GeometryCollection
from shapely.geometry.polygon import Polygon, orient
from shapely.ops import transform as shapely_transform


def _reproject(geom: BaseGeometry, epsg: int) -> BaseGeometry:
    if epsg == 4326:
        return geom
    transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    return shapely_transform(transformer.transform, geom)


def _fix_winding(geom: BaseGeometry) -> BaseGeometry:
    """Apply the RFC 7946 right-hand rule (CCW exterior, CW holes) to polygons."""
    if isinstance(geom, Polygon):
        return orient(geom, sign=1.0)
    if isinstance(geom, MultiPolygon):
        return MultiPolygon([orient(part, sign=1.0) for part in geom.geoms])
    if isinstance(geom, GeometryCollection):
        return GeometryCollection([_fix_winding(part) for part in geom.geoms])
    return geom


def _tuples_to_lists(obj):
    if isinstance(obj, dict):
        return {key: _tuples_to_lists(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_tuples_to_lists(value) for value in obj]
    return obj


def to_rfc7946(geom: BaseGeometry, epsg: int) -> dict:
    """Return `geom` (in the CRS given by `epsg`) as an RFC 7946 GeoJSON geometry dict."""
    reprojected = _reproject(geom, epsg)
    oriented = _fix_winding(reprojected)
    geojson = mapping(oriented)
    return _tuples_to_lists(geojson)
```