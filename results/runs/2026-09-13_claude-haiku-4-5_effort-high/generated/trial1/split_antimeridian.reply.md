```python
from shapely.geometry import Polygon, box


def split_antimeridian(polygon):
    """
    Split a polygon that may cross the antimeridian into valid polygons.
    
    Args:
        polygon: A shapely Polygon with coordinates in EPSG:4326 (lon/lat, [-180, 180])
    
    Returns:
        A list of valid shapely Polygons that don't cross the antimeridian
    """
    coords = list(polygon.exterior.coords)
    
    # Check if polygon crosses antimeridian by looking for jumps > 180 degrees
    crosses = any(abs(coords[i][0] - coords[i+1][0]) > 180 
                  for i in range(len(coords) - 1))
    
    if not crosses:
        return [polygon]
    
    # Shift all coordinates by +180 to move antimeridian from ±180 to 0/360
    def shift_coords(ring):
        return [(lon + 180, lat) for lon, lat in ring]
    
    shifted_exterior = shift_coords(coords)
    shifted_interiors = [shift_coords(list(ring.coords)) for ring in polygon.interiors]
    shifted_poly = Polygon(shifted_exterior, shifted_interiors)
    
    # Clip to western part [180, 360] (originally [0, 180])
    # and eastern part [0, 180] (originally [-180, 0])
    western_box = box(180, -90, 360, 90)
    eastern_box = box(0, -90, 180, 90)
    
    western_clipped = shifted_poly.intersection(western_box)
    eastern_clipped = shifted_poly.intersection(eastern_box)
    
    # Unshift back by -180
    def unshift_coords(ring):
        return [(lon - 180, lat) for lon, lat in ring]
    
    result = []
    
    for clipped in [western_clipped, eastern_clipped]:
        if clipped.is_empty:
            continue
        
        geoms = clipped.geoms if hasattr(clipped, 'geoms') else [clipped]
        
        for geom in geoms:
            if isinstance(geom, Polygon):
                exterior = unshift_coords(list(geom.exterior.coords))
                interiors = [unshift_coords(list(ring.coords)) for ring in geom.interiors]
                try:
                    unshifted = Polygon(exterior, interiors)
                    if unshifted.is_valid:
                        result.append(unshifted)
                except:
                    pass
    
    return result if result else [polygon]
```