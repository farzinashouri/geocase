```python
import json
from typing import Iterator, Tuple, List, Any

def _extract_coords(geom: dict) -> Iterator[Tuple[float, float]]:
    """Yield (longitude, latitude) pairs from a GeoJSON geometry object."""
    if geom is None:
        return
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if gtype == "GeometryCollection":
        for g in geom.get("geometries", []):
            yield from _extract_coords(g)
    elif gtype == "Point":
        if coords and len(coords) >= 2:
            yield coords[0], coords[1]
    elif gtype in ("MultiPoint", "LineString"):
        for coord in coords:
            if len(coord) >= 2:
                yield coord[0], coord[1]
    elif gtype in ("MultiLineString", "Polygon"):
        for ring in coords:
            for coord in ring:
                if len(coord) >= 2:
                    yield coord[0], coord[1]
    elif gtype == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                for coord in ring:
                    if len(coord) >= 2:
                        yield coord[0], coord[1]
    # Other types (e.g., Feature, FeatureCollection) are handled at the top level.

def geojson_bounds(path: str) -> Tuple[float, float, float, float]:
    """
    Return the bounding box of all features in a GeoJSON file as
    (min_lon, min_lat, max_lon, max_lat).

    The input file must contain coordinates in EPSG:4326 (longitude/latitude).
    Longitudes in the output are guaranteed to be within [-180, 180].
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_coords: List[Tuple[float, float]] = []

    # Handle FeatureCollection, Feature, or bare geometry.
    if data.get("type") == "FeatureCollection":
        for feature in data.get("features", []):
            geom = feature.get("geometry")
            if geom:
                all_coords.extend(_extract_coords(geom))
    elif data.get("type") == "Feature":
        geom = data.get("geometry")
        if geom:
            all_coords.extend(_extract_coords(geom))
    else:
        # Assume it's a geometry object.
        all_coords.extend(_extract_coords(data))

    if not all_coords:
        raise ValueError("No valid coordinates found in the GeoJSON file.")

    lons, lats = zip(*all_coords)
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    # Ensure longitudes are within [-180, 180] (input should already comply).
    min_lon = max(-180.0, min(180.0, min_lon))
    max_lon = max(-180.0, min(180.0, max_lon))

    return (min_lon, min_lat, max_lon, max_lat)


if __name__ == "__main__":
    # Example usage (not executed on import)
    import sys
    if len(sys.argv) > 1:
        try:
            bounds = geojson_bounds(sys.argv[1])
            print(f"Bounds: {bounds}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
```