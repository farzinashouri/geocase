```python
import json

from shapely.geometry import shape
from shapely.ops import unary_union


def geojson_bounds(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    geoms = []
    if data.get("type") == "FeatureCollection":
        for feature in data.get("features", []):
            geom = feature.get("geometry")
            if geom is not None:
                geoms.append(shape(geom))
    elif data.get("type") == "Feature":
        geom = data.get("geometry")
        if geom is not None:
            geoms.append(shape(geom))
    else:
        geoms.append(shape(data))

    combined = unary_union(geoms)
    min_lon, min_lat, max_lon, max_lat = combined.bounds

    min_lon = max(-180.0, min(180.0, min_lon))
    max_lon = max(-180.0, min(180.0, max_lon))

    return (float(min_lon), float(min_lat), float(max_lon), float(max_lat))
```