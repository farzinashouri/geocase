import json
from typing import Tuple, List, Any

try:
    from shapely.geometry import shape
except ImportError:
    shape = None


def geojson_bounds(path: str) -> Tuple[float, float, float, float]:
    """
    Compute the bounding box of all features in a GeoJSON file.

    Args:
        path: Path to the GeoJSON file (coordinates in EPSG:4326).

    Returns:
        A tuple (min_lon, min_lat, max_lon, max_lat) with longitudes clamped to [-180, 180]
        and latitudes clamped to [-90, 90].
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    min_lon = min_lat = max_lon = max_lat = None

    def _update_from_shapely(geom: dict) -> None:
        nonlocal min_lon, min_lat, max_lon, max_lat
        if shape is None:
            return
        try:
            shapely_geom = shape(geom)
        except Exception:
            return
        if shapely_geom.is_empty:
            return
        b = shapely_geom.bounds  # (minx, miny, maxx, maxy)
        if min_lon is None:
            min_lon, min_lat, max_lon, max_lat = b
        else:
            min_lon = min(min_lon, b[0])
            min_lat = min(min_lat, b[1])
            max_lon = max(max_lon, b[2])
            max_lat = max(max_lat, b[3])

    def _extract_coords(geom: dict) -> List[Tuple[float, float]]:
        """Fallback coordinate extraction without shapely."""
        coords: List[Tuple[float, float]] = []
        gtype = geom.get("type")
        if gtype in ("Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"):
            def extract(arr: Any) -> None:
                if isinstance(arr[0], (int, float)):
                    # Assume [lon, lat, ...]
                    coords.append((float(arr[0]), float(arr[1])))
                else:
                    for item in arr:
                        extract(item)
            extract(geom["coordinates"])
        elif gtype == "GeometryCollection":
            for g in geom.get("geometries", []):
                coords.extend(_extract_coords(g))
        return coords

    def _update_from_coords(geom: dict) -> None:
        nonlocal min_lon, min_lat, max_lon, max_lat
        for lon, lat in _extract_coords(geom):
            if min_lon is None:
                min_lon = max_lon = lon
                min_lat = max_lat = lat
            else:
                if lon < min_lon:
                    min_lon = lon
                if lon > max_lon:
                    max_lon = lon
                if lat < min_lat:
                    min_lat = lat
                if lat > max_lat:
                    max_lat = lat

    def process_geometry(geom: dict) -> None:
        if shape is not None:
            _update_from_shapely(geom)
        else:
            _update_from_coords(geom)

    # Dispatch based on GeoJSON type
    if data.get("type") == "FeatureCollection":
        for feature in data.get("features", []):
            geom = feature.get("geometry")
            if geom:
                process_geometry(geom)
    elif data.get("type") == "Feature":
        geom = data.get("geometry")
        if geom:
            process_geometry(geom)
    else:
        # Assume it's a geometry object
        process_geometry(data)

    if min_lon is None:
        # No valid geometry found; return a neutral bbox
        return (0.0, 0.0, 0.0, 0.0)

    # Clamp to valid WGS84 ranges
    min_lon = max(-180.0, min(180.0, min_lon))
    max_lon = max(-180.0, min(180.0, max_lon))
    min_lat = max(-90.0, min(90.0, min_lat))
    max_lat = max(-90.0, min(90.0, max_lat))

    return (float(min_lon), float(min_lat), float(max_lon), float(max_lat))