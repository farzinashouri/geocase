"""
A small module that splits a Shapely Polygon crossing the antimeridian
into one or more polygons that do not cross the antimeridian.
"""

from __future__ import annotations

from typing import List

from shapely.geometry import LineString, Polygon
from shapely.ops import split


def _shift_longitude(lon: float, shift: float) -> float:
    """
    Shift a longitude by `shift` degrees, keeping it in the range [-180, 180].
    """
    return lon - shift if lon > 180 else lon


def _shift_polygon_coords(coords: List[tuple[float, float]], shift: float) -> List[tuple[float, float]]:
    """
    Shift a list of (lon, lat) coordinates by `shift` degrees.
    """
    return [(lon + shift if lon < 0 else lon, lat) for lon, lat in coords]


def _shift_polygon_back(poly: Polygon, shift: float) -> Polygon:
    """
    Shift the exterior and interior rings of a polygon back by `shift` degrees.
    """
    exterior = _shift_longitude_coords(poly.exterior.coords, shift)
    interiors = [_shift_longitude_coords(ring.coords, shift) for ring in poly.interiors]
    return Polygon(exterior, interiors)


def _shift_longitude_coords(coords: List[tuple[float, float]], shift: float) -> List[tuple[float, float]]:
    """
    Shift a list of coordinates back by `shift` degrees.
    """
    return [(_shift_longitude(lon, shift), lat) for lon, lat in coords]


def split_antimeridian(polygon: Polygon) -> List[Polygon]:
    """
    Split a Shapely Polygon that may cross the antimeridian into
    one or more polygons that do not cross or touch the antimeridian
    except at its edge.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        Polygon with longitude/latitude coordinates in EPSG:4326
        and longitudes in the range [-180, 180].

    Returns
    -------
    List[shapely.geometry.Polygon]
        A list of polygons that together cover exactly the same
        region as the input polygon.  If the input polygon does not
        cross the antimeridian, the list contains the input polygon
        unchanged.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError("Input must be a shapely Polygon")

    # Detect if the polygon crosses the antimeridian
    coords = list(polygon.exterior.coords)
    crosses = any(abs(lon1 - lon2) > 180 for (lon1, _), (lon2, _) in zip(coords, coords[1:]))

    if not crosses:
        return [polygon]

    # Shift negative longitudes by +360 to unwrap the polygon
    shifted_coords = _shift_polygon_coords(coords, 360)
    shifted_polygon = Polygon(shifted_coords, [list(ring.coords) for ring in polygon.interiors])

    # Create a vertical line at the antimeridian (lon=180)
    antimeridian = LineString([(180, -90), (180, 90)])

    # Split the shifted polygon along the antimeridian
    split_result = split(shifted_polygon, antimeridian)

    # Shift the resulting polygons back to the original longitude range
    result_polygons = []
    for geom in split_result.geoms:
        if isinstance(geom, Polygon):
            # Shift back coordinates > 180 to negative values
            exterior = _shift_longitude_coords(geom.exterior.coords, 360)
            interiors = [_shift_longitude_coords(ring.coords, 360) for ring in geom.interiors]
            result_polygons.append(Polygon(exterior, interiors))

    return result_polygons