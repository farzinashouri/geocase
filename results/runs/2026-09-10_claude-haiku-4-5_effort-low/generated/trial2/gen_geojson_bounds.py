import json
from typing import Tuple

def geojson_bounds(path: str) -> Tuple[float, float, float, float]:
    """
    Return the bounding box of all features in a GeoJSON file.
    
    Args:
        path: Path to a GeoJSON file with WGS84 coordinates.
    
    Returns:
        A 4-tuple of floats (min_lon, min_lat, max_lon, max_lat).
    """
    with open(path) as f:
        geojson = json.load(f)
    
    lons = []
    lats = []
    
    def extract_coords(coords):
        if not coords:
            return
        if isinstance(coords[0], (int, float)):
            lons.append(coords[0])
            lats.append(coords[1])
        else:
            for item in coords:
                extract_coords(item)
    
    def process_geom(geom):
        if not geom:
            return
        if geom.get('type') == 'GeometryCollection':
            for g in geom.get('geometries', []):
                process_geom(g)
        else:
            extract_coords(geom.get('coordinates', []))
    
    if 'features' in geojson:
        features = geojson['features']
    elif 'type' in geojson and geojson['type'] in ['Point', 'LineString', 'Polygon', 'MultiPoint', 'MultiLineString', 'MultiPolygon', 'GeometryCollection']:
        features = [{'geometry': geojson}]
    else:
        features = []
    
    for feature in features:
        process_geom(feature.get('geometry'))
    
    return (min(lons), min(lats), max(lons), max(lats)) if lons else (0.0, 0.0, 0.0, 0.0)