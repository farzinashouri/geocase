```python
"""Convert shapely geometries to RFC 7946 compliant GeoJSON geometry objects.

Importing this module has no side effects.
"""

from shapely.geometry import mapping
from shapely.geometry.polygon import orient
from shapely.ops import transform as shapely_transform
from pyproj import Transformer


def _reproject(geom, epsg):
    """Return ``geom`` with coordinates transformed to EPSG:4326 (WGS 84).

    RFC 7946 mandates that coordinates use the WGS 84 datum with
    longitude, latitude (, altitude) axis order.  ``always_xy=True``
    guarantees the (lon, lat) output order regardless of the CRS'
    native axis order.
    """
    if int(epsg) == 4326:
        return geom
    transformer = Transformer.from_crs(
        "EPSG:%d" % int(epsg), "EPSG:4326", always_xy=True
    )
    return shapely_transform(transformer.transform, geom)


def _orient(geom):
    """Enforce RFC 7946 §3.1.6 winding order on any (multi)polygon.

    Exterior rings must be counterclockwise, interior rings (holes)
    clockwise.  ``shapely.geometry.polygon.orient(..., sign=1.0)``
    produces exactly that.  Other geometry types are returned as-is;
    a GeometryCollection is oriented member by member.
    """
    gtype = geom.geom_type
    if gtype == "Polygon":
        return orient(geom, sign=1.0)
    if gtype == "MultiPolygon":
        from shapely.geometry import MultiPolygon

        return MultiPolygon([orient(p, sign=1.0) for p in geom.geoms])
    if gtype == "GeometryCollection":
        from shapely.geometry import GeometryCollection

        return GeometryCollection([_orient(g) for g in geom.geoms])
    return geom


def _to_lists(obj):
    """Recursively convert coordinate tuples to JSON-style lists.

    ``shapely.geometry.mapping`` yields nested tuples; a valid GeoJSON
    object represents positions and coordinate arrays as JSON arrays,
    so we normalize everything to plain ``list``/``float`` values.
    """
    if isinstance(obj, dict):
        return {k: _to_lists(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_lists(v) for v in obj]
    if isinstance(obj, (int, float)):
        return float(obj)
    return obj


def to_rfc7946(geom, epsg):
    """Return ``geom`` as an RFC 7946 GeoJSON geometry object.

    Parameters
    ----------
    geom : shapely geometry
        The input geometry whose coordinates are expressed in the CRS
        identified by ``epsg``.
    epsg : int
        The EPSG code of the geometry's coordinate reference system
        (e.g. 4326 or 3857).

    Returns
    -------
    dict
        A GeoJSON geometry object (``type`` + ``coordinates``, or
        ``type`` + ``geometries`` for a GeometryCollection) with
        coordinates in WGS 84 longitude/latitude order and polygon
        rings wound per RFC 7946 §3.1.6.
    """
    geom = _reproject(geom, epsg)
    geom = _orient(geom)
    return _to_lists(mapping(geom))
```