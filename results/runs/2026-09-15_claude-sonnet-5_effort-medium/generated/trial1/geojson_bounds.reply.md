```python
import json

from shapely.geometry import shape
from shapely.ops import unary_union


def geojson_bounds(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    geometries = []

    def collect(obj):
        obj_type = obj.get("type")
        if obj_type == "FeatureCollection":
            for feature in obj.get("features", []):
                collect(feature)
        elif obj_type == "Feature":
            geom = obj.get("geometry")
            if geom is not None:
                collect(geom)
        elif obj_type == "GeometryCollection":
            for geom in obj.get("geometries", []):
                collect(geom)
        else:
            geometries.append(shape(obj))

    collect(data)

    combined = unary_union(geometries)
    min_lon, min_lat, max_lon, max_lat = combined.bounds

    min_lon = max(-180.0, min(180.0, min_lon))
    max_lon = max(-180.0, min(180.0, max_lon))

    return (float(min_lon), float(min_lat), float(max_lon), float(max_lat))
```