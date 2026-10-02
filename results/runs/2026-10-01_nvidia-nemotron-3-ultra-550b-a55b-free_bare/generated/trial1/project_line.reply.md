```python
"""Module for projecting a geographic LineString to a projected CRS along geodesics."""

from shapely.geometry import LineString
import pyproj


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """
    Project a LineString from EPSG:4326 (lon/lat) to a projected CRS (dst_epsg)
    by tracing the geodesic (shortest path on the WGS84 ellipsoid) between
    consecutive vertices. The returned LineString in the target CRS approximates
    the geodesic to within 25 km everywhere.

    Parameters
    ----------
    line : shapely.geometry.LineString
        Input line in EPSG:4326 (coordinates are longitude, latitude).
    dst_epsg : int
        EPSG code of the target projected coordinate reference system.

    Returns
    -------
    shapely.geometry.LineString
        LineString in the target CRS (coordinates in projected units, typically meters).
    """
    if line.is_empty:
        return LineString()

    transformer = pyproj.Transformer.from_crs(4326, dst_epsg, always_xy=True)
    geod = pyproj.Geod(ellps="WGS84")
    TOLERANCE = 25000.0  # 25 km in meters

    coords = list(line.coords)
    if len(coords) < 2:
        # A LineString must have at least 2 points; if not, return empty.
        return LineString()

    def _segment_points(lon1, lat1, lon2, lat2, x1, y1, x2, y2):
        """Return list of projected points for a single segment, including both endpoints."""
        # Recursive subdivision based on midpoint deviation in projected space
        def _recurse(lon_a, lat_a, lon_b, lat_b, x_a, y_a, x_b, y_b):
            # Get geographic midpoint of the geodesic
            mid_points = geod.npts(lon_a, lat_a, lon_b, lat_b, 1)
            if not mid_points:
                # Points are coincident or antipodal (npts returns empty for antipodal).
                return [(x_a, y_a), (x_b, y_b)]
            lon_m, lat_m = mid_points[0]
            x_m, y_m = transformer.transform(lon_m, lat_m)

            # Midpoint of the chord in projected space
            x_cm = (x_a + x_b) * 0.5
            y_cm = (y_a + y_b) * 0.5

            # Deviation of the projected geodesic midpoint from the chord midpoint
            dx = x_m - x_cm
            dy = y_m - y_cm
            dev = (dx * dx + dy * dy) ** 0.5

            if dev <= TOLERANCE:
                return [(x_a, y_a), (x_b, y_b)]
            else:
                left = _recurse(lon_a, lat_a, lon_m, lat_m, x_a, y_a, x_m, y_m)
                right = _recurse(lon_m, lat_m, lon_b, lat_b, x_m, y_m, x_b, y_b)
                # Combine, avoiding duplicate midpoint
                return left[:-1] + right

        return _recurse(lon1, lat1, lon2, lat2, x1, y1, x2, y2)

    all_points = []
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        x1, y1 = transformer.transform(lon1, lat1)
        x2, y2 = transformer.transform(lon2, lat2)

        seg_pts = _segment_points(lon1, lat1, lon2, lat2, x1, y1, x2, y2)
        if i == 0:
            all_points.extend(seg_pts)
        else:
            # Skip the first point of this segment (duplicate of previous segment's end)
            all_points.extend(seg_pts[1:])

    return LineString(all_points)
```