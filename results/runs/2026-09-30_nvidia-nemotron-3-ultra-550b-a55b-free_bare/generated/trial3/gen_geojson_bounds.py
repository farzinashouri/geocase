import json
from typing import Tuple, List, Any, Optional
from shapely.geometry import shape, BaseGeometry

def geojson_bounds(path: str) -> Tuple[float, float, float, float]:
    """
    Compute the bounding box of all features in a GeoJSON file.

    Args:
        path: Path to a GeoJSON file with coordinates in EPSG:4326 (WGS84).

    Returns:
        A 4-tuple (min_lon, min_lat, max_lon, max_lat) describing the
        extent of all geometries. Longitudes are clamped to [-180, 180],
        latitudes to [-90, 90].
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    geometries: List[BaseGeometry] = []

    def extract_geometries(obj: Any) -> None:
        if obj is None:
            return
        obj_type = obj.get("type")
        if obj_type == "FeatureCollection":
            for feature in obj.get("features", []):
                extract_geometries(feature)
        elif obj_type == "Feature":
            geom = obj.get("geometry")
            if geom:
                extract_geometries(geom)
        elif obj_type == "GeometryCollection":
            for geom in obj.get("geometries", []):
                extract_geometries(geom)
        elif obj_type in {
            "Point", "MultiPoint", "LineString", "MultiLineString",
            "Polygon", "MultiPolygon"
        }:
            try:
                geometries.append(shape(obj))
            except Exception:
                # Skip invalid geometries
                pass
        # Ignore other types

    extract_geometries(data)

    if not geometries:
        return (0.0, 0.0, 0.0, 0.0)

    min_lon = float("inf")
    min_lat = float("inf")
    max_lon = float("-inf")
    max_lat = float("-inf")

    for geom in geometries:
        if geom.is_empty:
            continue
        b = geom.bounds  # (minx, miny, maxx, maxy)
        min_lon = min(min_lon, b[0])
        min_lat = min(min_lat, b[1])
        max_lon = max(max_lon, b[2])
        max_lat = max(max_lat, b[3])

    # Clamp to valid WGS84 ranges
    min_lon = max(-180.0, min(180.0, min_lon))
    max_lon = max(-180.0, min(180.0, max_lon))
    min_lat = max(-90.0, min(90.0, min_lat))
    max_lat = max(-90.0, min(90.0, max_lat))

    return (min_lon, min_lat, max_lon, max_lat)