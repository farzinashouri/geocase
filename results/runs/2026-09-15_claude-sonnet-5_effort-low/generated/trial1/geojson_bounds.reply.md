```python
import json

from shapely.geometry import shape
from shapely.ops import unary_union


def geojson_bounds(path):
    with open(path) as f:
        data = json.load(f)

    geometries = []
    if data.get("type") == "FeatureCollection":
        for feature in data["features"]:
            geometries.append(shape(feature["geometry"]))
    elif data.get("type") == "Feature":
        geometries.append(shape(data["geometry"]))
    else:
        geometries.append(shape(data))

    min_lon, min_lat, max_lon, max_lat = unary_union(geometries).bounds

    min_lon = max(-180.0, min(180.0, min_lon))
    max_lon = max(-180.0, min(180.0, max_lon))

    return (float(min_lon), float(min_lat), float(max_lon), float(max_lat))
```