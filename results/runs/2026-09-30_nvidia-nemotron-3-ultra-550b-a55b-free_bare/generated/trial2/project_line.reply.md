```python
import math
from typing import List, Tuple

from shapely.geometry import LineString
import pyproj


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """
    Project a LineString from EPSG:4326 (lon/lat) to a projected CRS (dst_epsg),
    densifying the geodesic segments so that the resulting line in the projected
    CRS approximates the true geodesic to within 25 km everywhere.

    Parameters
    ----------
    line : shapely.LineString
        Input line in EPSG:4326 (coordinates are longitude, latitude).
    dst_epsg : int
        EPSG code of the target projected coordinate reference system.

    Returns
    -------
    shapely.LineString
        LineString in the target CRS (coordinates are easting, northing) that
        traces the geodesic between each pair of consecutive input vertices
        with a maximum deviation of 25 km.
    """
    if not isinstance(line, LineString):
        raise TypeError("Input must be a shapely LineString")
    coords = list(line.coords)
    if len(coords) < 2:
        raise ValueError("LineString must have at least two vertices")

    # Geodetic calculator for WGS84 (EPSG:4326)
    geod = pyproj.Geod(ellps="WGS84")
    # Transformer from geographic to target projected CRS
    transformer = pyproj.Transformer.from_crs(4326, dst_epsg, always_xy=True)

    TOLERANCE = 25000.0  # 25 km in meters
    MAX_DEPTH = 20

    def point_line_distance(px: float, py: float,
                            x1: float, y1: float,
                            x2: float, y2: float) -> float:
        """Perpendicular distance from point (px,py) to line through (x1,y1)-(x2,y2)."""
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        cross = abs(dx * (py - y1) - dy * (px - x1))
        return cross / math.hypot(dx, dy)

    def densify_segment(lon1: float, lat1: float,
                        lon2: float, lat2: float,
                        depth: int = 0) -> List[Tuple[float, float]]:
        """Recursively densify a geodesic segment in the projected CRS."""
        x1, y1 = transformer.transform(lon1, lat1)
        x2, y2 = transformer.transform(lon2, lat2)

        if depth >= MAX_DEPTH:
            return [(x1, y1)]

        # Geographic midpoint of the geodesic
        mid_lon, mid_lat = geod.npts(lon1, lat1, lon2, lat2, 1)[0]
        xm, ym = transformer.transform(mid_lon, mid_lat)

        # Deviation of midpoint from the chord in projected CRS
        dev = point_line_distance(xm, ym, x1, y1, x2, y2)

        if dev <= TOLERANCE:
            return [(x1, y1)]
        else:
            left = densify_segment(lon1, lat1, mid_lon, mid_lat, depth + 1)
            right = densify_segment(mid_lon, mid_lat, lon2, lat2, depth + 1)
            return left + right

    projected_points: List[Tuple[float, float]] = []
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        segment_points = densify_segment(lon1, lat1, lon2, lat2)
        projected_points.extend(segment_points)

    # Add the final vertex
    last_lon, last_lat = coords[-1]
    x_last, y_last = transformer.transform(last_lon, last_lat)
    projected_points.append((x_last, y_last))

    return LineString(projected_points)
```