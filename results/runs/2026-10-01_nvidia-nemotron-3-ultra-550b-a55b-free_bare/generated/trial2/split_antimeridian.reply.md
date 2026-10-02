```python
"""Module for splitting polygons that cross the antimeridian."""

from shapely.geometry import Polygon, LineString
from shapely.ops import split, transform

try:
    from shapely import make_valid
except ImportError:  # fallback for older shapely versions
    def make_valid(geom):
        return geom.buffer(0)


def _crosses_antimeridian(ring):
    """Check if a LinearRing crosses the antimeridian."""
    coords = list(ring.coords)
    for i in range(len(coords) - 1):
        lon1, _ = coords[i]
        lon2, _ = coords[i + 1]
        if abs(lon2 - lon1) > 180:
            return True
    return False


def split_antimeridian(polygon):
    """
    Split a polygon that crosses the antimeridian into one or more polygons
    that do not cross the antimeridian.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        A polygon in EPSG:4326 (longitude/latitude) with longitudes in [-180, 180].

    Returns
    -------
    list[shapely.geometry.Polygon]
        A list of polygons covering the same region, none of which cross the
        antimeridian. If the input does not cross the antimeridian, a single-element
        list containing the original polygon is returned.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError("Input must be a shapely Polygon")
    if polygon.is_empty:
        return []

    # Check if the polygon (exterior or any interior) crosses the antimeridian
    crosses = _crosses_antimeridian(polygon.exterior)
    if not crosses:
        for interior in polygon.interiors:
            if _crosses_antimeridian(interior):
                crosses = True
                break

    if not crosses:
        return [polygon]

    # Shift negative longitudes by +360 so that the antimeridian becomes the line x=180
    def shift_forward(x, y, z=None):
        if x < 0:
            return x + 360, y
        return x, y

    shifted = transform(shift_forward, polygon)

    # Create a vertical split line at x=180 that spans the polygon's latitude range
    minx, miny, maxx, maxy = shifted.bounds
    eps = 1e-9  # small extension to guarantee a clean split at the edges
    split_line = LineString([(180, miny - eps), (180, maxy + eps)])

    # Perform the split
    result = split(shifted, split_line)

    # Transform back: longitudes > 180 become negative (subtract 360)
    def shift_back(x, y, z=None):
        if x > 180:
            return x - 360, y
        return x, y

    polygons = []
    for geom in result.geoms:
        if geom.geom_type == "Polygon" and not geom.is_empty:
            transformed = transform(shift_back, geom)
            valid_geom = make_valid(transformed)
            if not valid_geom.is_empty:
                polygons.append(valid_geom)

    return polygons
```