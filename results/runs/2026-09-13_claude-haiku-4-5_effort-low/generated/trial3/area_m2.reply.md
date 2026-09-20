```python
from shapely.geometry import Polygon, MultiPolygon
from pyproj import Geod

_GEOD = Geod(ellps='WGS84')

def area_m2(geom):
    """Calculate area of a shapely Polygon or MultiPolygon in square meters."""
    if isinstance(geom, MultiPolygon):
        return sum(area_m2(g) for g in geom.geoms)
    
    if isinstance(geom, Polygon):
        coords = list(geom.exterior.coords)
        lons, lats = zip(*coords)
        area, _ = _GEOD.polygon_area_perimeter(lons, lats)
        
        for interior in geom.interiors:
            coords = list(interior.coords)
            lons, lats = zip(*coords)
            hole_area, _ = _GEOD.polygon_area_perimeter(lons, lats)
            area -= abs(hole_area)
        
        return abs(area)
    
    raise TypeError(f"Expected Polygon or MultiPolygon, got {type(geom)}")
```