```python
import math
from shapely.geometry import Polygon, LineString
from shapely.ops import split, transform

def split_antimeridian(polygon):
    """
    Split a shapely Polygon (EPSG:4326, longitudes in [-180, 180]) that may cross the antimeridian
    into a list of polygons that do not cross the antimeridian.

    A polygon crosses the antimeridian if any of its rings has an edge where the longitude
    difference between consecutive vertices exceeds 180 degrees (indicating a jump across
    the 180°/-180° boundary). The returned polygons cover exactly the same region on the
    Earth's surface and none of them crosses or touches the antimeridian except at their edges.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        Input polygon in EPSG:4326 (longitude/latitude).

    Returns
    -------
    list[shapely.geometry.Polygon]
        List of polygons resulting from the split. If the input does not cross the
        antimeridian, a single-element list containing the original polygon is returned.
    """
    # ----------------------------------------------------------------------
    # Helper: check if a ring (exterior or interior) crosses the antimeridian.
    # ----------------------------------------------------------------------
    def ring_crosses_antimeridian(ring):
        coords = list(ring.coords)
        for i in range(len(coords) - 1):
            lon1, _ = coords[i]
            lon2, _ = coords[i + 1]
            if abs(lon1 - lon2) > 180:
                return True
        return False

    # ----------------------------------------------------------------------
    # Early exit if no ring crosses the antimeridian.
    # ----------------------------------------------------------------------
    crosses = ring_crosses_antimeridian(polygon.exterior)
    if not crosses:
        for interior in polygon.interiors:
            if ring_crosses_antimeridian(interior):
                crosses = True
                break
    if not crosses:
        return [polygon]

    # ----------------------------------------------------------------------
    # Unwrap all rings into a continuous coordinate system.
    # Use the first vertex of the exterior ring as the reference longitude.
    # ----------------------------------------------------------------------
    ref_lon = polygon.exterior.coords[0][0]

    def unwrap_ring(ring):
        coords = list(ring.coords)
        new_coords = []
        for lon, lat in coords:
            # Shift longitude by multiples of 360 so that it lies within 180° of ref_lon.
            while lon - ref_lon > 180:
                lon -= 360
            while lon - ref_lon < -180:
                lon += 360
            new_coords.append((lon, lat))
        # Ensure the ring is closed (first vertex == last vertex).
        if new_coords[0] != new_coords[-1]:
            new_coords.append(new_coords[0])
        return new_coords

    ext_coords = unwrap_ring(polygon.exterior)
    int_coords = [unwrap_ring(interior) for interior in polygon.interiors]

    unwrapped_poly = Polygon(ext_coords, int_coords)

    # ----------------------------------------------------------------------
    # Determine the antimeridian line in the unwrapped coordinate system.
    # It will be either at x = 180 or x = -180.
    # ----------------------------------------------------------------------
    minx, miny, maxx, maxy = unwrapped_poly.bounds
    split_x = None
    if minx < 180 < maxx:
        split_x = 180
    elif minx < -180 < maxx:
        split_x = -180
    else:
        # This should not happen for a polygon that crosses the antimeridian,
        # but fall back to 180.
        split_x = 180

    # ----------------------------------------------------------------------
    # Split the unwrapped polygon by the vertical line at split_x.
    # The splitter line spans the full latitude range to guarantee intersection.
    # ----------------------------------------------------------------------
    splitter = LineString([(split_x, -90), (split_x, 90)])
    result = split(unwrapped_poly, splitter)

    # ----------------------------------------------------------------------
    # Extract Polygon objects from the split result.
    # ----------------------------------------------------------------------
    if result.geom_type == 'GeometryCollection':
        polygons = [geom for geom in result.geoms if geom.geom_type == 'Polygon']
    elif result.geom_type == 'Polygon':
        polygons = [result]
    else:
        polygons = []

    # ----------------------------------------------------------------------
    # Wrap longitudes of the resulting polygons back into the standard [-180, 180] range.
    # ----------------------------------------------------------------------
    def wrap_lon(lon):
        # Map to [-180, 180). Note: 180 becomes -180.
        return (lon + 180) % 360 - 180

    def wrap_polygon(poly):
        def transformer(x, y, z=None):
            return wrap_lon(x), y
        return transform(transformer, poly)

    wrapped_polygons = [wrap_polygon(p) for p in polygons]

    # ----------------------------------------------------------------------
    # Discard any empty or invalid geometries that might have been created.
    # ----------------------------------------------------------------------
    final_polygons = [p for p in wrapped_polygons if not p.is_empty and p.is_valid]

    return final_polygons
```