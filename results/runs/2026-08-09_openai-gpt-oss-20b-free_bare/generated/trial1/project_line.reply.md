```python
"""
geodesic_projector.py

Provides a function to project a LineString from EPSG:4326 to a projected CRS,
approximating geodesic segments within a 1 km tolerance.
"""

from __future__ import annotations

import math

from shapely.geometry import LineString
from pyproj import Geod, Transformer

# Earth's radius in meters (WGS84)
EARTH_RADIUS = 6371000.0
# Maximum chord length that guarantees a sagitta ≤ 1 km
MAX_CHORD_LENGTH = math.sqrt(8 * EARTH_RADIUS * 1000.0)  # ≈ 225 700 m

# Geodesic calculator for WGS84
GEOD = Geod(ellps="WGS84")


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """
    Project a LineString from EPSG:4326 to the CRS specified by *dst_epsg*.
    The resulting line follows the geodesic between each pair of consecutive
    input vertices to within 1 km everywhere along the line.

    Parameters
    ----------
    line : shapely.geometry.LineString
        Input line in EPSG:4326 (lon/lat).
    dst_epsg : int
        EPSG code of the target projected CRS.

    Returns
    -------
    shapely.geometry.LineString
        The projected line in the target CRS.
    """
    if line.is_empty:
        return LineString()

    coords = list(line.coords)
    n_points = len(coords)

    # If the line has only one point, just transform it.
    if n_points == 1:
        lon, lat = coords[0]
        transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{dst_epsg}", always_xy=True)
        x, y = transformer.transform(lon, lat)
        return LineString([(x, y)])

    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{dst_epsg}", always_xy=True)
    projected_coords: list[tuple[float, float]] = []

    for i in range(n_points - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]

        # Geodesic distance in meters
        _, _, dist = GEOD.inv(lon1, lat1, lon2, lat2)

        # Number of segments needed to keep sagitta ≤ 1 km
        n_segments = math.ceil(dist / MAX_CHORD_LENGTH)

        # Add the start point of the first segment
        if i == 0:
            x, y = transformer.transform(lon1, lat1)
            projected_coords.append((x, y))

        # Interpolate intermediate points if needed
        if n_segments > 1:
            inter_pts = GEOD.npts(lon1, lat1, lon2, lat2, n_segments - 1)
            for lon, lat in inter_pts:
                x, y = transformer.transform(lon, lat)
                projected_coords.append((x, y))

        # Add the end point of the segment
        x, y = transformer.transform(lon2, lat2)
        projected_coords.append((x, y))

    return LineString(projected_coords)
```