```python
from shapely.constructive import make_valid
from shapely.geometry import Polygon, MultiPolygon


def fix_geometry(geom):
    """
    Fix an invalid Polygon or MultiPolygon to a valid one.
    
    Converts an invalid geometry (e.g., self-intersecting polygon) into a valid
    Polygon or MultiPolygon covering exactly the region enclosed by the input's
    boundary rings. Already-valid input is returned unchanged.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError(f"Expected Polygon or MultiPolygon, got {type(geom).__name__}")
    
    result = make_valid(geom)
    
    if not isinstance(result, (Polygon, MultiPolygon)):
        raise ValueError(
            f"make_valid returned unexpected type {type(result).__name__} "
            f"for input {type(geom).__name__}"
        )
    
    return result
```