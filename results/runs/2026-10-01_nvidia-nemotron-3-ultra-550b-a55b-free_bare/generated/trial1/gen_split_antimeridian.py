import shapely
from shapely.geometry import Polygon, LineString
from shapely.ops import split, transform
from shapely import make_valid
import pyproj
import numpy as np

def split_antimeridian(polygon: Polygon) -> list[Polygon]:
    """
    Split a polygon that crosses the antimeridian (longitude 180/-180) into
    a list of polygons that do not cross the antimeridian.

    Parameters
    ----------
    polygon : shapely.Polygon
        A polygon in EPSG:4326 (longitudes in [-180, 180]). The polygon may
        cross the antimeridian, which appears as a jump between longitudes
        near +180 and -180 in consecutive vertices.

    Returns
    -------
    list[shapely.Polygon]
        A list of valid polygons covering the same region, none of which
        crosses or touches the antimeridian except at its edge. If the input
        does not cross the antimeridian, a single-element list containing the
        original polygon is returned.
    """
    # ------------------------------------------------------------------
    # Helper: detect if any ring has an edge that jumps across the antimeridian
    # ------------------------------------------------------------------
    def crosses_antimeridian(geom: Polygon) -> bool:
        for ring in [geom.exterior] + list(geom.interiors):
            coords = list(ring.coords)
            for i in range(len(coords) - 1):
                lon1, _ = coords[i]
                lon2, _ = coords[i + 1]
                if abs(lon1 - lon2) > 180:
                    return True
        return False

    # If the polygon does not cross the antimeridian, return it unchanged.
    if not crosses_antimeridian(polygon):
        return [polygon]

    # ------------------------------------------------------------------
    # Choose a projection center on the antimeridian (lon=180) at the mean
    # latitude of the polygon. An Azimuthal Equidistant projection centered
    # there makes the antimeridian a straight line (the central meridian) and
    # keeps the polygon continuous.
    # ------------------------------------------------------------------
    all_lats = []
    for ring in [polygon.exterior] + list(polygon.interiors):
        all_lats.extend([c[1] for c in ring.coords])
    mean_lat = float(np.mean(all_lats)) if all_lats else 0.0

    aeqd_crs = pyproj.CRS.from_proj4(
        f"+proj=aeqd +lat_0={mean_lat} +lon_0=180 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )
    wgs84_crs = pyproj.CRS.from_epsg(4326)
    transformer_to_aeqd = pyproj.Transformer.from_crs(wgs84_crs, aeqd_crs, always_xy=True)
    transformer_to_wgs84 = pyproj.Transformer.from_crs(aeqd_crs, wgs84_crs, always_xy=True)

    # ------------------------------------------------------------------
    # Project the polygon to the Azimuthal Equidistant CRS.
    # ------------------------------------------------------------------
    projected_poly = transform(transformer_to_aeqd.transform, polygon)

    # ------------------------------------------------------------------
    # The antimeridian in WGS84 is the meridian at 180°. In the chosen
    # projection this meridian becomes a straight vertical line through the
    # origin. A two-point LineString from pole to pole is sufficient.
    # ------------------------------------------------------------------
    antimeridian_wgs84 = LineString([(180.0, -90.0), (180.0, 90.0)])
    projected_antimeridian = transform(transformer_to_aeqd.transform, antimeridian_wgs84)

    # ------------------------------------------------------------------
    # Split the projected polygon by the projected antimeridian line.
    # ------------------------------------------------------------------
    split_result = split(projected_poly, projected_antimeridian)

    # ------------------------------------------------------------------
    # Transform the resulting pieces back to WGS84 and wrap longitudes to
    # the canonical [-180, 180] range. Use make_valid to clean up any
    # topological artifacts.
    # ------------------------------------------------------------------
    def wrap_coords(coords):
        return [((lon + 180) % 360 - 180, lat) for lon, lat in coords]

    result = []
    if split_result.geom_type == 'GeometryCollection':
        for geom in split_result.geoms:
            if geom.geom_type == 'Polygon' and not geom.is_empty:
                poly_wgs84 = transform(transformer_to_wgs84.transform, geom)
                new_ext = wrap_coords(list(poly_wgs84.exterior.coords))
                new_ints = [wrap_coords(list(interior.coords)) for interior in poly_wgs84.interiors]
                result.append(make_valid(Polygon(new_ext, new_ints)))
    elif split_result.geom_type == 'Polygon' and not split_result.is_empty:
        poly_wgs84 = transform(transformer_to_wgs84.transform, split_result)
        new_ext = wrap_coords(list(poly_wgs84.exterior.coords))
        new_ints = [wrap_coords(list(interior.coords)) for interior in poly_wgs84.interiors]
        result.append(make_valid(Polygon(new_ext, new_ints)))

    # Fallback (should not occur for valid input)
    if not result:
        return [polygon]

    return result