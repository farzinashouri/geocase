import json
from shapely.geometry import shape

def geojson_bounds(path):
    """
    Compute the bounding box of all features in a GeoJSON file.

    Parameters
    ----------
    path : str
        Path to a GeoJSON file with coordinates in EPSG:4326 (WGS84).

    Returns
    -------
    tuple of float
        (min_lon, min_lat, max_lon, max_lat) describing the geographic extent.
        Longitudes are clamped to the range [-180, 180].
    """
    with open(path, 'r') as f:
        data = json.load(f)

    min_lon = float('inf')
    min_lat = float('inf')
    max_lon = float('-inf')
    max_lat = float('-inf')

    def update_bounds(geom):
        nonlocal min_lon, min_lat, max_lon, max_lat
        if geom is None:
            return
        try:
            shapely_geom = shape(geom)
        except Exception:
            return
        if shapely_geom.is_empty:
            return
        b = shapely_geom.bounds
        min_lon = min(min_lon, b[0])
        min_lat = min(min_lat, b[1])
        max_lon = max(max_lon, b[2])
        max_lat = max(max_lat, b[3])

    # Dispatch based on GeoJSON type
    geojson_type = data.get('type')
    if geojson_type == 'FeatureCollection':
        for feature in data.get('features', []):
            update_bounds(feature.get('geometry'))
    elif geojson_type == 'Feature':
        update_bounds(data.get('geometry'))
    else:
        # Assume it is a Geometry object
        update_bounds(data)

    if min_lon == float('inf'):
        raise ValueError("No valid geometries found in GeoJSON")

    # Ensure longitudes stay within [-180, 180]
    min_lon = max(min_lon, -180.0)
    max_lon = min(max_lon, 180.0)

    return (min_lon, min_lat, max_lon, max_lat)