```python
from shapely.geometry import Polygon, MultiPolygon


def fix_geometry(geom):
    """
    Fix an invalid Polygon or MultiPolygon.
    
    Takes a potentially self-intersecting or otherwise invalid geometry
    and returns a valid geometry covering the same enclosed region.
    
    Args:
        geom: A shapely Polygon or MultiPolygon (possibly invalid)
        
    Returns:
        A valid shapely Polygon or MultiPolygon covering the same region
        
    Raises:
        ValueError: If input is not a Polygon or MultiPolygon
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise ValueError("Input must be a Polygon or MultiPolygon")
    
    return geom.make_valid()
```