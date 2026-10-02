```python
from shapely.geometry import Polygon, LineString
from shapely.ops import transform, split

def split_antimeridian(polygon: Polygon) -> list[Polygon]:
    """
    Split a polygon that crosses the antimeridian (longitude 180/-180) into
    a list of polygons that do not cross the antimeridian.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        A polygon in EPSG:4326 (longitude/latitude) with longitudes in [-180, 180].

    Returns
    -------
    list[shapely.geometry.Polygon]
        A list of polygons covering the same region. If the input does not cross
        the antimeridian, a single-element list containing the original polygon
        is returned. The resulting polygons have longitudes in [-180, 180] and
        none crosses the antimeridian; they may touch it at their edges.
    """
    # Transform longitudes from [-180, 180] to [0, 360]
    def to_360(x, y):
        if x < 0:
            x += 360.0
        return (x, y)

    # Transform back from [0, 360] to [-180, 180]
    def to_180(x, y):
        if x > 180.0:
            x -= 360.0
        return (x, y)

    # Work in 0-360 space where the antimeridian is the line x=180
    polygon_360 = transform(to_360, polygon)

    # Check if the polygon actually crosses the antimeridian
    minx, miny, maxx, maxy = polygon_360.bounds
    if not (minx < 180.0 and maxx > 180.0):
        return [polygon]

    # Splitting line along the antimeridian, extended slightly beyond the polygon's latitude range
    split_line = LineString([(180.0, miny - 1.0), (180.0, maxy + 1.0)])

    # Perform the split
    result = split(polygon_360, split_line)

    # Collect the resulting polygons (ignore any non-polygon or empty parts)
    split_polygons_360 = [
        geom for geom in result.geoms
        if geom.geom_type == 'Polygon' and not geom.is_empty
    ]

    # Transform back to [-180, 180]
    split_polygons = [transform(to_180, p) for p in split_polygons_360]

    return split_polygons

__all__ = ['split_antimeridian']
```