```python
# -*- coding: utf-8 -*-
"""
A small self‑contained module that projects a LineString from WGS84
(EPSG:4326) to any projected CRS, approximating the geodesic
between each pair of vertices to within 1 km.
"""

from __future__ import annotations

import math
from typing import Iterable, Tuple

from pyproj import Geod, Transformer
from shapely.geometry import LineString


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """
    Project a LineString from EPSG:4326 to a projected CRS, approximating
    the geodesic between each pair of consecutive vertices to within
    1 km everywhere along the line.

    Parameters
    ----------
    line : shapely.geometry.LineString
        Input line in WGS84 (lon/lat).
    dst_epsg : int
        Target EPSG code for the projected CRS.

    Returns
    -------
    shapely.geometry.LineString
        Projected line in the target CRS.
    """
    if not isinstance(line, LineString):
        raise TypeError("`line` must be a shapely.geometry.LineString")

    coords: list[Tuple[float, float]] = list(line.coords)

    # Empty or single‑point line: just transform the coordinates.
    if len(coords) < 2:
        transformer = Transformer.from_crs(4326, dst_epsg, always_xy=True)
        projected = [transformer.transform(lon, lat) for lon, lat in coords]
        return LineString(projected)

    geod = Geod(ellps="WGS84")
    transformer = Transformer.from_crs(4326, dst_epsg, always_xy=True)

    projected_coords: list[Tuple[float, float]] = []

    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]

        # Geodesic distance in meters.
        _, _, dist = geod.inv(lon1, lat1, lon2, lat2)

        # Number of intermediate points needed to keep spacing <= 1 km.
        n_intermediate = max(math.ceil(dist / 1000.0) - 1, 0)

        # Intermediate points along the geodesic.
        inter_points = geod.npts(lon1, lat1, lon2, lat2, n_intermediate)

        # Build the full list of points for this segment.
        segment_points = [(lon1, lat1)] + inter_points + [(lon2, lat2)]

        # Avoid duplicate vertices between consecutive segments.
        if i > 0:
            segment_points = segment_points[1:]

        # Transform to the target CRS and append.
        for lon, lat in segment_points:
            x, y = transformer.transform(lon, lat)
            projected_coords.append((x, y))

    return LineString(projected_coords)
```