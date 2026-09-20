```python
from shapely.geometry import Polygon, MultiPolygon

def fix_geometry(geom):
    """Fix invalid polygon geometries while preserving enclosed regions."""
    return geom.make_valid()
```