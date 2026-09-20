```python
"""Compute the geographic bounding box of a GeoJSON file."""

import json

from shapely.geometry import shape


def geojson_bounds(path):
    """Return (min_lon, min_lat, max_lon, max_lat) covering all features in the GeoJSON file at `path`."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    geometries = []
    gtype = data.get("type")
    if gtype == "FeatureCollection":
        for feature in data.get("features", []):
            geom = feature.get("geometry")
            if geom is not None:
                geometries.append(geom)
    elif gtype == "Feature":
        geom = data.get("geometry")
        if geom is not None:
            geometries.append(geom)
    else:
        geometries.append(data)

    if not geometries:
        raise ValueError(f"No geometries found in {path!r}")

    min_lon = min_lat = float("inf")
    max_lon = max_lat = float("-inf")

    for geom in geometries:
        minx, miny, maxx, maxy = shape(geom).bounds
        min_lon = min(min_lon, minx)
        min_lat = min(min_lat, miny)
        max_lon = max(max_lon, maxx)
        max_lat = max(max_lat, maxy)

    return (min_lon, min_lat, max_lon, max_lat)
```