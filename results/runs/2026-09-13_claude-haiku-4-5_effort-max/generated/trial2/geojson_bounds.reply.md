```python
import json

def geojson_bounds(path):
    with open(path) as f:
        geojson = json.load(f)
    
    coords = []
    
    def extract_coords(geom):
        geom_type = geom.get('type')
        coords_data = geom.get('coordinates', [])
        
        if geom_type == 'Point':
            coords.append(coords_data)
        elif geom_type in ('LineString', 'MultiPoint'):
            coords.extend(coords_data)
        elif geom_type in ('Polygon', 'MultiLineString'):
            for ring in coords_data:
                coords.extend(ring)
        elif geom_type == 'MultiPolygon':
            for polygon in coords_data:
                for ring in polygon:
                    coords.extend(ring)
        elif geom_type == 'GeometryCollection':
            for sub_geom in geom.get('geometries', []):
                extract_coords(sub_geom)
    
    if geojson.get('type') == 'FeatureCollection':
        for feature in geojson.get('features', []):
            if feature.get('geometry'):
                extract_coords(feature['geometry'])
    elif 'type' in geojson:
        extract_coords(geojson)
    
    if not coords:
        return (0.0, 0.0, 0.0, 0.0)
    
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    
    min_lat = min(lats)
    max_lat = max(lats)
    min_lon = min(lons)
    max_lon = max(lons)
    
    if max_lon - min_lon > 180:
        sorted_lons = sorted(lons)
        max_gap = 0
        gap_idx = -1
        
        for i in range(len(sorted_lons) - 1):
            gap = sorted_lons[i + 1] - sorted_lons[i]
            if gap > max_gap:
                max_gap = gap
                gap_idx = i
        
        if gap_idx >= 0:
            min_lon = sorted_lons[gap_idx + 1]
            max_lon = sorted_lons[gap_idx]
    
    return (min_lon, min_lat, max_lon, max_lat)
```