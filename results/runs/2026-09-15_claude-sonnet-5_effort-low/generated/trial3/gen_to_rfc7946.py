from __future__ import annotations

from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry
from pyproj import Transformer


def _round_coords(coords):
    if isinstance(coords[0], (int, float)):
        return [round(c, 7) for c in coords]
    return [_round_coords(c) for c in coords]


def to_rfc7946(geom: BaseGeometry, epsg: int) -> dict:
    transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)

    def transform_coords(coords):
        if isinstance(coords[0], (int, float)):
            x, y = coords[0], coords[1]
            lon, lat = transformer.transform(x, y)
            return [lon, lat]
        return [transform_coords(c) for c in coords]

    def convert(g: BaseGeometry) -> dict:
        m = mapping(g)
        gtype = m["type"]

        if gtype == "GeometryCollection":
            return {
                "type": "GeometryCollection",
                "geometries": [convert(part) for part in g.geoms],
            }

        coords = transform_coords(m["coordinates"])
        coords = _round_coords(coords)
        return {"type": gtype, "coordinates": coords}

    return convert(geom)