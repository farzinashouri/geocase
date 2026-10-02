import json

def geojson_bounds(path):
    """
    Compute the bounding box of all features in a GeoJSON file.

    Args:
        path (str): Path to the GeoJSON file.

    Returns:
        tuple: (min_lon, min_lat, max_lon, max_lat) as floats.
               Longitudes are normalized to the range [-180, 180].

    Raises:
        ValueError: If no coordinates are found in the GeoJSON.
    """
    with open(path, 'r') as f:
        data = json.load(f)

    min_lon = float('inf')
    max_lon = float('-inf')
    min_lat = float('inf')
    max_lat = float('-inf')

    def update_bounds(lon, lat):
        nonlocal min_lon, max_lon, min_lat, max_lat
        # Normalize longitude to [-180, 180)
        lon = (lon + 180) % 360 - 180
        if lon < min_lon:
            min_lon = lon
        if lon > max_lon:
            max_lon = lon
        if lat < min_lat:
            min_lat = lat
        if lat > max_lat:
            max_lat = lat

    def flatten_coords(coords):
        """Yield (lon, lat) pairs from a nested coordinate array."""
        if isinstance(coords, list):
            if len(coords) >= 2 and all(isinstance(x, (int, float)) for x in coords):
                # This is a coordinate pair (or triplet)
                yield (coords[0], coords[1])
            else:
                for item in coords:
                    yield from flatten_coords(item)

    def extract_coords(obj):
        """Recursively extract coordinates from a GeoJSON object."""
        if obj is None:
            return
        if isinstance(obj, dict):
            # Process geometry coordinates
            if 'coordinates' in obj:
                coords = obj['coordinates']
                if coords is not None:
                    for lon, lat in flatten_coords(coords):
                        update_bounds(lon, lat)
            # Recurse into containers
            for key in ('features', 'geometry', 'geometries'):
                if key in obj:
                    val = obj[key]
                    if isinstance(val, list):
                        for item in val:
                            extract_coords(item)
                    else:
                        extract_coords(val)
        elif isinstance(obj, list):
            for item in obj:
                extract_coords(item)

    extract_coords(data)

    if min_lon == float('inf'):
        raise ValueError("No coordinates found in GeoJSON")

    return (min_lon, min_lat, max_lon, max_lat)