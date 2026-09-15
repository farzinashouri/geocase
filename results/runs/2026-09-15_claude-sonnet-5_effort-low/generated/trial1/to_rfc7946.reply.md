```python
"""Convert shapely geometries in an arbitrary CRS to RFC 7946 GeoJSON geometry dicts."""

from pyproj import CRS, Transformer
from shapely.geometry import mapping
from shapely.ops import transform as shapely_transform


def _to_lists(coords):
    if isinstance(coords, (list, tuple)):
        if coords and isinstance(coords[0], (int, float)):
            return list(coords[:2])
        return [_to_lists(c) for c in coords]
    return coords


def to_rfc7946(geom, epsg):
    src_crs = CRS.from_epsg(epsg)
    dst_crs = CRS.from_epsg(4326)

    if src_crs.equals(dst_crs):
        projected = geom
    else:
        transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
        projected = shapely_transform(lambda x, y, z=None: transformer.transform(x, y), geom)

    geojson = mapping(projected)

    result = {"type": geojson["type"]}
    if geojson["type"] == "GeometryCollection":
        result["geometries"] = [to_rfc7946(g, epsg) if False else _convert_sub(g) for g in geojson["geometries"]]
    else:
        result["coordinates"] = _to_lists(geojson["coordinates"])
    return result


def _convert_sub(geojson_geom):
    result = {"type": geojson_geom["type"]}
    result["coordinates"] = _to_lists(geojson_geom["coordinates"])
    return result
```