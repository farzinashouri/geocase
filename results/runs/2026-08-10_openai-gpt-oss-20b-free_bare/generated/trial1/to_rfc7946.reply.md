```python
# rfc7946.py
"""
Utility to convert a Shapely geometry to a GeoJSON geometry object
strictly conforming to RFC 7946.

The function `to_rfc7946` transforms the geometry from the supplied
EPSG coordinate reference system to WGS84 (EPSG:4326) and removes any
Z or M values, producing a dictionary with the keys `type` and
`coordinates` (or `geometries` for GeometryCollection).
"""

from __future__ import annotations

from pyproj import Transformer
from shapely.geometry import mapping
from shapely.ops import transform


def to_rfc7946(geom, epsg: int) -> dict:
    """
    Convert a Shapely geometry to a GeoJSON geometry object
    conforming to RFC 7946.

    Parameters
    ----------
    geom : shapely.geometry.base.BaseGeometry
        The input geometry.  Its coordinates are assumed to be in the
        coordinate reference system identified by `epsg`.
    epsg : int
        EPSG code of the geometry's current coordinate reference system.

    Returns
    -------
    dict
        A dictionary representing the geometry in GeoJSON format,
        with coordinates expressed in longitude/latitude (EPSG:4326)
        and without any Z or M values.
    """
    # Create a transformer from the source CRS to WGS84
    transformer = Transformer.from_crs(epsg, 4326, always_xy=True)

    # Transform the geometry
    transformed = transform(transformer.transform, geom)

    # Convert to a GeoJSON-like mapping
    geojson = mapping(transformed)

    # Recursively strip Z/M values from coordinates
    def _strip_z(obj):
        if isinstance(obj, dict):
            if "coordinates" in obj:
                obj["coordinates"] = _strip_z(obj["coordinates"])
            if "geometries" in obj:
                obj["geometries"] = [_strip_z(g) for g in obj["geometries"]]
            return obj
        elif isinstance(obj, (list, tuple)):
            if all(isinstance(x, (int, float)) for x in obj):
                return obj[:2]  # drop Z/M
            return [_strip_z(x) for x in obj]
        return obj

    return _strip_z(geojson)
```