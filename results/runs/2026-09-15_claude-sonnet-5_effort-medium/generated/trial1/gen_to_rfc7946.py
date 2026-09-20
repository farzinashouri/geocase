"""Convert shapely geometries to RFC 7946 compliant GeoJSON geometry dicts."""

from pyproj import CRS, Transformer
from shapely.geometry import mapping
from shapely.ops import transform as shapely_transform

_WGS84 = CRS.from_epsg(4326)


def _to_nested_lists(coords):
    if not coords:
        return list(coords)
    if isinstance(coords[0], (int, float)):
        return [round(c, 7) for c in coords]
    return [_to_nested_lists(c) for c in coords]


def to_rfc7946(geom, epsg):
    """Return geom (in the CRS identified by epsg) as an RFC 7946 GeoJSON geometry dict."""
    source_crs = CRS.from_epsg(epsg)

    if not source_crs.equals(_WGS84):
        transformer = Transformer.from_crs(source_crs, _WGS84, always_xy=True)
        geom = shapely_transform(lambda x, y, z=None: transformer.transform(x, y, z), geom)

    mapped = mapping(geom)

    if mapped["type"] == "GeometryCollection":
        geometries = [
            {"type": g["type"], "coordinates": _to_nested_lists(g["coordinates"])}
            for g in mapped["geometries"]
        ]
        return {"type": "GeometryCollection", "geometries": geometries}

    return {
        "type": mapped["type"],
        "coordinates": _to_nested_lists(mapped["coordinates"]),
    }