# split_antimeridian.py
"""
Utility to split a shapely Polygon that may cross the antimeridian
into a list of polygons that do not cross it.
"""

from __future__ import annotations

from shapely.geometry import Polygon, LineString, GeometryCollection
from shapely.ops import split
from typing import List


def _shift_to_360(ring: List[tuple[float, float]]) -> List[tuple[float, float]]:
    """Shift longitudes from [-180, 180] to [0, 360]."""
    return [(lon + 360 if lon < 0 else lon, lat) for lon, lat in ring]


def _shift_back(ring: List[tuple[float, float]]) -> List[tuple[float, float]]:
    """Shift longitudes from [0, 360] back to [-180, 180]."""
    return [(lon - 360 if lon > 180 else lon, lat) for lon, lat in ring]


def _polygon_from_ring(ring: List[tuple[float, float]]) -> Polygon:
    """Create a Polygon from a ring of coordinates."""
    return Polygon(ring)


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """
    Split a polygon that may cross the antimeridian into polygons that
    do not cross it.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        Polygon with coordinates in EPSG:4326 (lon/lat, lon in [-180, 180]).

    Returns
    -------
    List[shapely.geometry.Polygon]
        Polygons covering the same area, each not crossing the antimeridian.
        If the input polygon does not cross the antimeridian, a single-element
        list containing the original polygon is returned.
    """
    # Quick check: does the polygon cross the antimeridian?
    coords = list(polygon.exterior.coords)
    crosses = any(abs(coords[i + 1][0] - coords[i][0]) > 180 for i in range(len(coords) - 1))
    if not crosses:
        return [polygon]

    # Shift all longitudes to [0, 360] to make the polygon continuous
    shell_360 = _shift_to_360(polygon.exterior.coords)
    holes_360 = [_shift_to_360(interior.coords) for interior in polygon.interiors]
    poly_360 = Polygon(shell_360, holes_360)

    # Split the polygon by the antimeridian line at x = 180
    antimeridian = LineString([(180, -90), (180, 90)])
    split_result = split(poly_360, antimeridian)

    # Flatten the result and shift coordinates back to [-180, 180]
    result_polygons: List[Polygon] = []

    def process_geom(geom):
        if isinstance(geom, Polygon):
            shell_back = _shift_back(list(geom.exterior.coords))
            holes_back = [_shift_back(list(interior.coords)) for interior in geom.interiors]
            result_polygons.append(Polygon(shell_back, holes_back))
        elif isinstance(geom, GeometryCollection):
            for sub in geom.geoms:
                process_geom(sub)

    for geom in split_result.geoms:
        process_geom(geom)

    return result_polygons