from shapely import ops
from pyproj import CRS, Transformer


def area_m2(geom):
    """
    Calculate area in square meters for a polygon in WGS84 (EPSG:4326).
    
    Args:
        geom: shapely Polygon or MultiPolygon with coordinates in EPSG:4326 (lon/lat)
    
    Returns:
        float: Area in square meters
    """
    # Get centroid for projection center
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y
    
    # Create Azimuthal Equal-Area projection centered on geometry centroid
    # This preserves area and works accurately for polygons anywhere on Earth
    aeqd_crs = CRS.from_proj4(f'+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0')
    
    # Transformer from WGS84 to equal-area projection
    transformer = Transformer.from_crs(CRS.from_epsg(4326), aeqd_crs, always_xy=True)
    
    # Apply transformation and calculate area
    transformed_geom = ops.transform(transformer.transform, geom)
    
    return float(transformed_geom.area)