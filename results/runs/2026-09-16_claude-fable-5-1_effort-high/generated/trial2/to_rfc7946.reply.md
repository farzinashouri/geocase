```python
"""Convert shapely geometries to RFC 7946 GeoJSON geometry objects.

The single public entry point is :func:`to_rfc7946`.

What is enforced (RFC 7946, sections 3.1 and 4):

* Coordinates are reprojected to WGS 84 (EPSG:4326) and emitted in
  longitude, latitude order regardless of the axis order of the source CRS.
* Longitudes are wrapped into [-180, 180]; latitudes must lie in [-90, 90].
* Polygon rings follow the right-hand rule: exterior rings are
  counterclockwise, holes are clockwise.  Rings are closed (shapely
  guarantees this) so the first and last position are identical.
* Positions carry at most three elements (x, y, optional altitude).  A
  measure (M) ordinate, if present, is dropped because GeoJSON has no slot
  for it.
* Nested GeometryCollections are flattened, since the RFC says they
  SHOULD NOT be nested.
* Only the ``type`` and ``coordinates`` (or ``geometries``) members are
  emitted.  No ``crs`` member is written; RFC 7946 removed it.

Not handled: geometries that cross the antimeridian are emitted as-is
rather than being cut in two (the RFC phrases this as a SHOULD).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient

__all__ = ["to_rfc7946"]

_WGS84 = 4326


# --------------------------------------------------------------------------- #
# Reprojection
# --------------------------------------------------------------------------- #


def _transformer(epsg: int) -> Transformer:
    """Build a transformer from ``epsg`` to WGS 84 that takes/returns x, y order."""
    source = CRS.from_epsg(int(epsg))
    target = CRS.from_epsg(_WGS84)
    return Transformer.from_crs(source, target, always_xy=True)


def _normalise_lonlat(coords: np.ndarray) -> np.ndarray:
    """Validate and wrap an (n, 2|3) array of lon/lat[/alt] positions."""
    coords = np.array(coords, dtype=float, copy=True)
    if coords.size == 0:
        return coords
    if not np.all(np.isfinite(coords)):
        raise ValueError(
            "Coordinate transformation produced non-finite values; the "
            "geometry cannot be represented in GeoJSON."
        )
    lon = coords[:, 0]
    lat = coords[:, 1]
    if np.any(lat < -90.0) or np.any(lat > 90.0):
        raise ValueError("Latitude outside [-90, 90] after reprojection.")
    outside = (lon < -180.0) | (lon > 180.0)
    if np.any(outside):
        lon[outside] = ((lon[outside] + 180.0) % 360.0) - 180.0
        coords[:, 0] = lon
    return coords


def _reproject(geom: BaseGeometry, epsg: int) -> BaseGeometry:
    """Return ``geom`` reprojected to WGS 84 with any M ordinate dropped.

    Coordinates are pulled out with ``get_coordinates`` (which never returns
    M) and written back with ``set_coordinates``, so the output geometry is
    2-D or 3-D (XYZ) exactly according to whether the input had Z.
    """
    has_z = bool(shapely.has_z(geom))
    coords = shapely.get_coordinates(geom, include_z=has_z)

    if coords.size == 0:
        # Empty geometry: nothing to transform, but still strip M by
        # rebuilding through the 2-D/3-D coordinate path.
        return shapely.set_coordinates(np.array([geom], dtype=object), coords)[0]

    if int(epsg) == _WGS84:
        out = coords
    else:
        transformer = _transformer(epsg)
        if has_z:
            x, y, z = transformer.transform(coords[:, 0], coords[:, 1], coords[:, 2])
            out = np.column_stack([x, y, z])
        else:
            x, y = transformer.transform(coords[:, 0], coords[:, 1])
            out = np.column_stack([x, y])

    out = _normalise_lonlat(out)
    return shapely.set_coordinates(np.array([geom], dtype=object), out)[0]


# --------------------------------------------------------------------------- #
# Right-hand rule
# --------------------------------------------------------------------------- #


def _orient(geom: BaseGeometry) -> BaseGeometry:
    """Recursively enforce CCW exteriors and CW holes on every polygon."""
    if geom.is_empty:
        return geom
    gtype = geom.geom_type
    if gtype == "Polygon":
        return orient(geom, sign=1.0)
    if gtype == "MultiPolygon":
        return shapely.MultiPolygon([_orient(p) for p in geom.geoms])
    if gtype == "GeometryCollection":
        return shapely.GeometryCollection([_orient(g) for g in geom.geoms])
    return geom


# --------------------------------------------------------------------------- #
# Serialisation
# --------------------------------------------------------------------------- #


def _positions(geom: BaseGeometry, has_z: bool) -> list[list[float]]:
    coords = shapely.get_coordinates(geom, include_z=has_z)
    return [[float(v) for v in row] for row in coords]


def _flatten_collection(geom: BaseGeometry) -> list[BaseGeometry]:
    """Return the non-collection members of a (possibly nested) collection."""
    members: list[BaseGeometry] = []
    for part in geom.geoms:
        if part.geom_type == "GeometryCollection":
            members.extend(_flatten_collection(part))
        else:
            members.append(part)
    return members


def _to_dict(geom: BaseGeometry, has_z: bool) -> dict[str, Any]:
    gtype = geom.geom_type

    if gtype == "Point":
        pts = _positions(geom, has_z)
        return {"type": "Point", "coordinates": pts[0] if pts else []}

    if gtype in ("LineString", "LinearRing"):
        return {"type": "LineString", "coordinates": _positions(geom, has_z)}

    if gtype == "Polygon":
        if geom.is_empty:
            return {"type": "Polygon", "coordinates": []}
        rings = [_positions(geom.exterior, has_z)]
        rings.extend(_positions(ring, has_z) for ring in geom.interiors)
        return {"type": "Polygon", "coordinates": rings}

    if gtype in ("MultiPoint", "MultiLineString", "MultiPolygon"):
        parts = [
            _to_dict(part, has_z)["coordinates"]
            for part in geom.geoms
            if not part.is_empty
        ]
        return {"type": gtype, "coordinates": parts}

    if gtype == "GeometryCollection":
        members = [
            _to_dict(part, has_z)
            for part in _flatten_collection(geom)
            if not part.is_empty
        ]
        return {"type": "GeometryCollection", "geometries": members}

    raise TypeError(f"Unsupported geometry type: {gtype!r}")


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def to_rfc7946(geom: BaseGeometry, epsg: int) -> dict[str, Any]:
    """Return ``geom`` as an RFC 7946 GeoJSON geometry object.

    Parameters
    ----------
    geom:
        Any shapely geometry.  Its coordinates are interpreted in the CRS
        identified by ``epsg`` (x, y order as stored by shapely).
    epsg:
        Integer EPSG code of the coordinate reference system ``geom`` is in,
        for example ``4326`` or ``3857``.

    Returns
    -------
    dict
        A GeoJSON geometry object with ``type`` and ``coordinates`` members
        (``geometries`` for a GeometryCollection).  Coordinates are WGS 84
        longitude/latitude (plus altitude if the input had Z), polygons obey
        the right-hand rule, and no other members are present.

    Raises
    ------
    TypeError
        If ``geom`` is not a shapely geometry.
    ValueError
        If ``epsg`` is not a known EPSG code, or if reprojection yields
        non-finite or out-of-range coordinates.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"Expected a shapely geometry, got {type(geom).__name__}")
    try:
        epsg_code = int(epsg)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"EPSG code must be an integer, got {epsg!r}") from exc

    projected = _reproject(geom, epsg_code)
    oriented = _orient(projected)
    return _to_dict(oriented, bool(shapely.has_z(oriented)))
```