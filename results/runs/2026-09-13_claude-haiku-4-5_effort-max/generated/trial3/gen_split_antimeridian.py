from shapely.geometry import Polygon, box


def split_antimeridian(polygon):
    """
    Split a polygon crossing the antimeridian into separate non-crossing polygons.

    Args:
        polygon: A shapely Polygon with coordinates in EPSG:4326 (lon in [-180, 180])

    Returns:
        A list of valid Polygons that together cover the same region and don't cross
        the antimeridian. A polygon that doesn't cross returns as [polygon].
    """

    def has_crossing(coords):
        for i in range(len(coords) - 1):
            if abs(coords[i + 1][0] - coords[i][0]) > 180:
                return True
        return False

    ext_coords = list(polygon.exterior.coords)
    if not has_crossing(ext_coords):
        return [polygon]

    def to_360(lon):
        return lon if lon >= 0 else lon + 360

    def from_360(lon):
        return lon if lon <= 180 else lon - 360

    # Normalize to [0, 360] space where antimeridian is at 180
    normalized_ext = [(to_360(lon), lat) for lon, lat in ext_coords]
    normalized_holes = [[(to_360(lon), lat) for lon, lat in hole.coords]
                        for hole in polygon.interiors]

    poly_360 = Polygon(normalized_ext, normalized_holes)

    # Split at lon=180 using intersection with hemispheres
    western_box = box(0, -90, 180, 90)
    eastern_box = box(180, -90, 360, 90)

    poly_west = poly_360.intersection(western_box)
    poly_east = poly_360.intersection(eastern_box)

    result = []

    # Process western hemisphere [0, 180]
    if not poly_west.is_empty:
        geoms = poly_west.geoms if hasattr(poly_west, 'geoms') else [poly_west]
        for geom in geoms:
            if hasattr(geom, 'exterior'):
                coords = [(from_360(lon), lat) for lon, lat in geom.exterior.coords]
                holes = [[(from_360(lon), lat) for lon, lat in hole.coords]
                         for hole in geom.interiors]
                poly = Polygon(coords, holes)
                if poly.is_valid and poly.area > 0:
                    result.append(poly)

    # Process eastern hemisphere [180, 360] and convert back to [-180, 0]
    if not poly_east.is_empty:
        geoms = poly_east.geoms if hasattr(poly_east, 'geoms') else [poly_east]
        for geom in geoms:
            if hasattr(geom, 'exterior'):
                coords = [(lon - 360, lat) for lon, lat in geom.exterior.coords]
                holes = [[(lon - 360, lat) for lon, lat in hole.coords]
                         for hole in geom.interiors]
                poly = Polygon(coords, holes)
                if poly.is_valid and poly.area > 0:
                    result.append(poly)

    return result if result else [polygon]