"""
A small module that converts a Shapely geometry to a GeoJSON geometry
object conforming to RFC 7946, reprojecting it to WGS84 (EPSG:4326).

Usage:
    from module_name import to_rfc7946
    geojson_geom = to_rfc7946(shapely_geom, epsg_code)
"""

from __future__ import annotations

from typing import Any, Dict, List

import pyproj
from shapely.geometry import GeometryCollection, MultiLineString, MultiPoint, MultiPolygon, Point, Polygon, LineString
from shapely.ops import transform


def _geom_to_dict(g: Any) -> Dict[str, Any]:
    """
    Recursively convert a Shapely geometry to a GeoJSON geometry dict.
    """
    if g.is_empty:
        return {"type": g.geom_type, "coordinates": []}

    geom_type = g.geom_type

    if geom_type == "Point":
        return {"type": "Point", "coordinates": [g.x, g.y]}

    if geom_type == "MultiPoint":
        return {
            "type": "MultiPoint",
            "coordinates": [[pt.x, pt.y] for pt in g.geoms],
        }

    if geom_type == "LineString":
        return {"type": "LineString", "coordinates": [[pt.x, pt.y] for pt in g.coords]}

    if geom_type == "MultiLineString":
        return {
            "type": "MultiLineString",
            "coordinates": [
                [[pt.x, pt.y] for pt in line.coords] for line in g.geoms
            ],
        }

    if geom_type == "Polygon":
        exterior = [[pt.x, pt.y] for pt in g.exterior.coords]
        interiors = [
            [[pt.x, pt.y] for pt in ring.coords] for ring in g.interiors
        ]
        return {"type": "Polygon", "coordinates": [exterior] + interiors}

    if geom_type == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [[pt.x, pt.y] for pt in poly.exterior.coords]
                    + [
                        [[pt.x, pt.y] for pt in ring.coords]
                        for ring in poly.interiors
                    ]
                ]
                for poly in g.geoms
            ],
        }

    if geom_type == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [_geom_to_dict(sub) for sub in g.geoms],
        }

    raise ValueError(f"Unsupported geometry type: {geom_type}")


def to_rfc7946(geom: Any, epsg: int) -> Dict[str, Any]:
    """
    Convert a Shapely geometry to a GeoJSON geometry dict conforming to RFC 7946.
    The geometry is reprojected from the given EPSG code to WGS84 (EPSG:4326).

    Parameters
    ----------
    geom : shapely.geometry.base.BaseGeometry
        The input geometry.
    epsg : int
        The EPSG code of the coordinate reference system of the input geometry.

    Returns
    -------
    dict
        A GeoJSON geometry object with keys "type" and "coordinates" (or
        "geometries" for a GeometryCollection).
    """
    source_crs = pyproj.CRS.from_epsg(epsg)
    target_crs = pyproj.CRS.from_epsg(4326)
    transformer = pyproj.Transformer.from_crs(
        source_crs, target_crs, always_xy=True
    )

    # Transform the geometry to WGS84
    wgs84_geom = transform(transformer.transform, geom)

    # Convert to GeoJSON dict
    return _geom_to_dict(wgs84_geom)