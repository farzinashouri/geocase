```python
"""Compute the WGS84 bounding box of a GeoJSON file's features."""
import json
import math

from shapely.geometry import shape


def _iter_geometries(obj):
    if obj is None:
        return
    t = obj.get("type")
    if t == "FeatureCollection":
        for feature in obj.get("features", []):
            yield from _iter_geometries(feature)
    elif t == "Feature":
        yield from _iter_geometries(obj.get("geometry"))
    elif t == "GeometryCollection":
        for geom in obj.get("geometries", []):
            yield from _iter_geometries(geom)
    else:
        yield obj


def geojson_bounds(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    min_lon = math.inf
    min_lat = math.inf
    max_lon = -math.inf
    max_lat = -math.inf

    for geom_dict in _iter_geometries(data):
        geom = shape(geom_dict)
        if geom.is_empty:
            continue
        gmin_lon, gmin_lat, gmax_lon, gmax_lat = geom.bounds
        min_lon = min(min_lon, gmin_lon)
        min_lat = min(min_lat, gmin_lat)
        max_lon = max(max_lon, gmax_lon)
        max_lat = max(max_lat, gmax_lat)

    if math.isinf(min_lon):
        raise ValueError(f"No geometries found in {path!r}")

    min_lon = max(min_lon, -180.0)
    max_lon = min(max_lon, 180.0)

    return (min_lon, min_lat, max_lon, max_lat)
```