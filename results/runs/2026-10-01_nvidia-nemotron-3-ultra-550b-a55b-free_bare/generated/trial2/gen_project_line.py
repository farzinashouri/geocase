"""
Module for projecting a geodesic LineString from EPSG:4326 to a projected CRS.

The function `project_line` takes a shapely LineString in WGS84 (EPSG:4326) and an
integer EPSG code of a projected CRS. It returns a LineString in that CRS which
approximates the geodesic (shortest path on the ellipsoid) between each pair of
consecutive input vertices to within 25 km everywhere along the line.
"""

from __future__ import annotations

import numpy as np
import pyproj
from shapely.geometry import LineString


def _densify_segment(
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
    transformer: pyproj.Transformer,
    geod: pyproj.Geod,
    tolerance_crs: float,
    depth: int = 0,
    max_depth: int = 50,
) -> list[tuple[float, float]]:
    """
    Recursively subdivide a geodesic segment until its projection deviates from
    the chord by less than `tolerance_crs` (in target CRS units).

    Returns a list of projected (x, y) coordinates including both endpoints.
    """
    # Project the geographic endpoints
    x1, y1 = transformer.transform(lon1, lat1)
    x2, y2 = transformer.transform(lon2, lat2)

    # If the geographic distance is negligible, return the endpoints directly
    _, _, geo_dist = geod.inv(lon1, lat1, lon2, lat2)
    if geo_dist < 1e-6:  # less than a micrometer
        return [(x1, y1), (x2, y2)]

    # Get the midpoint of the geodesic (on the ellipsoid)
    mid_points = geod.npts(lon1, lat1, lon2, lat2, 1)
    if not mid_points:
        # Antipodal or degenerate case – fall back to endpoints
        return [(x1, y1), (x2, y2)]
    mid_lon, mid_lat = mid_points[0]
    xm, ym = transformer.transform(mid_lon, mid_lat)

    # Perpendicular distance from the projected midpoint to the chord (infinite line)
    dx = x2 - x1
    dy = y2 - y1
    dxm = xm - x1
    dym = ym - y1
    cross = abs(dx * dym - dy * dxm)
    chord_len = np.hypot(dx, dy)
    if chord_len == 0:
        dist_to_chord = np.hypot(dxm, dym)
    else:
        dist_to_chord = cross / chord_len

    # If the deviation is within tolerance or we hit the recursion limit, accept the chord
    if dist_to_chord <= tolerance_crs or depth >= max_depth:
        return [(x1, y1), (x2, y2)]

    # Otherwise, subdivide and combine
    left = _densify_segment(
        lon1, lat1, mid_lon, mid_lat, transformer, geod, tolerance_crs, depth + 1, max_depth
    )
    right = _densify_segment(
        mid_lon, mid_lat, lon2, lat2, transformer, geod, tolerance_crs, depth + 1, max_depth
    )
    # Avoid duplicating the midpoint
    return left[:-1] + right


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """
    Project a LineString from EPSG:4326 (WGS84 lon/lat) to a projected CRS
    (given by `dst_epsg`) such that the resulting line follows the geodesic
    between each pair of consecutive input vertices to within 25 km.

    Parameters
    ----------
    line : shapely.LineString
        Input line in EPSG:4326 (coordinates are longitude, latitude).
    dst_epsg : int
        EPSG code of the target projected coordinate reference system.

    Returns
    -------
    shapely.LineString
        LineString in the target CRS approximating the geodesic path.
    """
    if not isinstance(line, LineString):
        raise TypeError("Input must be a shapely LineString")
    if line.is_empty:
        return LineString()

    # Transformer from geographic (EPSG:4326) to the target projected CRS
    transformer = pyproj.Transformer.from_crs(
        "EPSG:4326", f"EPSG:{dst_epsg}", always_xy=True
    )
    # Geodetic calculator on the WGS84 ellipsoid
    geod = pyproj.Geod(ellps="WGS84")

    # Determine the tolerance in the target CRS units (25 km on the ground)
    crs = pyproj.CRS.from_epsg(dst_epsg)
    conversion_factor = crs.axis_info[0].unit_conversion_factor
    if conversion_factor is None or conversion_factor == 0:
        # Fallback: assume the CRS uses metres
        tolerance_crs = 25000.0
    else:
        # conversion_factor converts CRS units to metres
        tolerance_crs = 25000.0 / conversion_factor

    coords = list(line.coords)
    if len(coords) < 2:
        # Single point – just project it
        projected = [transformer.transform(x, y) for x, y in coords]
        return LineString(projected)

    projected_points: list[tuple[float, float]] = []
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        segment_pts = _densify_segment(
            lon1, lat1, lon2, lat2, transformer, geod, tolerance_crs
        )
        if i == 0:
            projected_points.extend(segment_pts)
        else:
            # Skip the first point of the segment (duplicate of previous end)
            projected_points.extend(segment_pts[1:])

    return LineString(projected_points)


__all__ = ["project_line"]