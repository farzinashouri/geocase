```python
from shapely.geometry import Polygon, MultiPolygon

def fix_geometry(geom):
    return geom.make_valid()
```