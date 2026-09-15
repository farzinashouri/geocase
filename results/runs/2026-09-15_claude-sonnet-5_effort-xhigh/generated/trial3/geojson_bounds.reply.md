```python
import json

from shapely.geometry import shape


def _iter_geometries(obj):
    if obj is None:
        return
    geom_type = obj.get("type")
    if geom_type == "FeatureCollection":
        for feature in obj.get("features") or []:
            yield from _iter_geometries(feature)
    elif geom_type == "Feature":
        yield from _iter_geometries(obj.get("geometry"))
    elif geom_type == "GeometryCollection":
        for geometry in obj.get("geometries") or []:
            yield from _iter_geometries(geometry)
    else:
        yield obj


def geojson_bounds(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    min_lon = min_lat = float("inf")
    max_lon = max_lat = float("-inf")

    for geom in _iter_geometries(data):
        minx, miny, maxx, maxy = shape(geom).bounds
        min_lon = min(min_lon, minx)
        min_lat = min(min_lat, miny)
        max_lon = max(max_lon, maxx)
        max_lat = max(max_lat, maxy)

    if min_lon == float("inf"):
        raise ValueError(f"No geometries found in {path!r}")

    min_lon = max(min_lon, -180.0)
    max_lon = min(max_lon, 180.0)

    return (min_lon, min_lat, max_lon, max_lat)
```