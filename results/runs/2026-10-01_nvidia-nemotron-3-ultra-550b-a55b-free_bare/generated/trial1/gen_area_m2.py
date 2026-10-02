import pyproj

# Create a single Geod instance for WGS84 ellipsoid to avoid repeated initialization.
_GEOD = pyproj.Geod(ellps="WGS84")


def area_m2(geom) -> float:
    """
    Return the area of a shapely Polygon or MultiPolygon in square meters.

    The input geometry must have coordinates in EPSG:4326 (longitude/latitude, WGS84).
    The calculation uses the WGS84 ellipsoid via pyproj.Geod.geometry_area_perimeter,
    which correctly handles polygons with holes and multipolygons anywhere on Earth.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Geometry in WGS84 (EPSG:4326).

    Returns
    -------
    float
        Area in square meters (always non-negative).
    """
    # pyproj.Geod.geometry_area_perimeter returns (area, perimeter).
    # The area is signed according to ring orientation (positive for counter-clockwise).
    # For polygons with holes, the holes are expected to have opposite orientation,
    # so the returned area is the net area (exterior minus interiors).
    # For MultiPolygon, the areas of all parts are summed.
    # We take the absolute value to guarantee a non-negative result.
    area, _ = _GEOD.geometry_area_perimeter(geom)
    return abs(area)