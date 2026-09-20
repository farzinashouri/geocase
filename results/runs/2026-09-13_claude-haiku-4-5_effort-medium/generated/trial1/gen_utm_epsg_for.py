from pyproj import CRS

def utm_epsg_for(lon, lat):
    """
    Returns the EPSG code for the WGS 84 / UTM zone containing the given location.
    
    Follows the Military Grid Reference System zone assignments with standard exceptions.
    
    Args:
        lon: Longitude in WGS84 (-180 to 180)
        lat: Latitude in WGS84 (-90 to 90)
    
    Returns:
        EPSG code as int (326xx for northern hemisphere, 327xx for southern)
    """
    wgs84_crs = CRS.from_epsg(4326)
    utm_crs = wgs84_crs.get_utm_crs(lat, lon)
    return utm_crs.to_epsg()