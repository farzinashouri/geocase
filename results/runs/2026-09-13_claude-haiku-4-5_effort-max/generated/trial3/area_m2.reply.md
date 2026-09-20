```python
from pyproj import Geod

def area_m2(geom):
    """Calculate the area of a WGS84 polygon in square meters."""
    geod = Geod(ellps='WGS84')
    area, _ = geod.geometry_area_perimeter(geom)
    return area
```