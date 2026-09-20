I couldn't get shell approval to run a quick smoke test, so this is written conservatively against the documented shapely 2.x / pyproj 3.x APIs (no untested edge APIs). Design notes are in the module docstring: RFC 7946 pins the CRS to WGS 84 lon/lat (§4), mandates right-hand-rule ring winding (§3.1.6), recommends antimeridian cutting (§3.1.9) and bounded coordinate precision (§11.2).

```python
"""Strict RFC 7946 (GeoJSON) encoding of shapely geometries.

The single public entry point is :func:`to_rfc7946`, which takes a shapely
geometry plus the EPSG code its coordinates are in and returns a plain ``dict``
that is a valid RFC 7946 Geometry object.

Conformance decisions, with the section of RFC 7946 that drives each one:

* **CRS (Section 4).**  RFC 7946 geometries are *always* WGS 84 (EPSG:4326)
  with longitude first, latitude second, so the input is reprojected with
  pyproj whenever ``epsg != 4326``.  The 2008-era ``crs`` member is forbidden
  by the RFC and is never emitted; neither is the optional ``bbox``, since the
  caller asked for ``type``/``coordinates`` only.  Input coordinates are read
  in ``x=easting/longitude, y=northing/latitude`` order (pyproj's
  ``always_xy`` convention, and how shapely geometries are conventionally
  stored) regardless of the authority axis order of ``epsg``.
* **Positions (Section 3.1.1).**  A position is ``[lon, lat]`` or
  ``[lon, lat, alt]``.  Any M (measure) ordinate is dropped, because the RFC
  gives no meaning to a fourth element.  JSON has no ``NaN``/``Infinity``, so
  non-finite output coordinates raise ``ValueError`` instead of producing
  unserialisable output.
* **Linear rings (Section 3.1.6).**  Rings are closed and forced to follow the
  right-hand rule: exterior rings counter-clockwise, holes clockwise.  Winding
  is measured on the *output* coordinates, since a reprojection can reverse
  orientation.
* **Antimeridian (Section 3.1.9).**  Geometries that extend past +/-180 deg of
  longitude after reprojection are cut into pieces that each stay inside
  [-180, 180].  This only engages when the transformed coordinates actually
  fall outside that range, so a geometry authored in EPSG:4326 is never
  silently reinterpreted.  Cutting lines and polygons uses a planar overlay
  and therefore drops Z from the affected geometry; points keep theirs.  A
  polygon that encloses a pole is not special-cased (the RFC's own advice
  there is a SHOULD and needs a spherical treatment).  Pass
  ``split_antimeridian=False`` to disable.
* **Precision (Section 11.2).**  Coordinates are rounded to 7 decimal places
  (~1 cm) and elevations to 3 (1 mm), which also strips floating-point noise
  from the reprojection.  Pass ``xy_precision=None``/``z_precision=None`` to
  keep full precision.
* **Empty geometries (Section 3.1).**  Encoded with empty coordinate arrays,
  which the RFC explicitly permits processors to read as null objects.
* ``LinearRing`` is not a GeoJSON type and is encoded as a ``LineString``;
  ``GeometryCollection`` uses a ``geometries`` member rather than
  ``coordinates``.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from functools import lru_cache
from numbers import Integral
from typing import Any

import numpy as np
import shapely
from pyproj import CRS, Transformer
from pyproj.exceptions import CRSError
from shapely.affinity import translate
from shapely.geometry import LineString, MultiLineString, MultiPolygon, box
from shapely.geometry.base import BaseGeometry

__all__ = ["to_rfc7946"]


WGS84_EPSG = 4326

# Latitudes this far outside [-90, 90] are treated as round-off from the
# reprojection and clamped; anything worse is an error rather than a guess.
_LAT_TOLERANCE = 1e-6

_DIMENSION = {
    "Point": 0,
    "MultiPoint": 0,
    "LineString": 1,
    "LinearRing": 1,
    "MultiLineString": 1,
    "Polygon": 2,
    "MultiPolygon": 2,
}


def to_rfc7946(
    geom: BaseGeometry,
    epsg: int,
    *,
    xy_precision: int | None = 7,
    z_precision: int | None = 3,
    split_antimeridian: bool = True,
) -> dict[str, Any]:
    """Return ``geom`` as an RFC 7946 GeoJSON geometry object.

    Parameters
    ----------
    geom:
        Any shapely geometry.  Its coordinates are read as ``(x, y[, z])``.
    epsg:
        EPSG code of the CRS ``geom`` is expressed in, e.g. ``4326`` or
        ``3857``.  Anything other than 4326 is reprojected to WGS 84.
    xy_precision, z_precision:
        Decimal places kept for longitude/latitude and for elevation.
        ``None`` disables rounding for that component.
    split_antimeridian:
        Cut geometries that reach past +/-180 deg longitude (RFC 7946
        Section 3.1.9).

    Returns
    -------
    dict
        A JSON-serialisable geometry object: ``{"type": ..., "coordinates":
        ...}``, or ``{"type": "GeometryCollection", "geometries": [...]}``.

    Raises
    ------
    TypeError
        ``geom`` is not a shapely geometry, or ``epsg`` is not an integer.
    ValueError
        The EPSG code is unknown, the reprojection produced non-finite or
        out-of-range coordinates, or the geometry cannot be represented (for
        instance a ring left with fewer than four positions).
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"expected a shapely geometry, got {type(geom).__name__}")
    if isinstance(epsg, bool) or not isinstance(epsg, Integral):
        raise TypeError(f"epsg must be an integer EPSG code, got {epsg!r}")

    return _convert(
        geom, int(epsg), xy_precision, z_precision, bool(split_antimeridian)
    )


# --------------------------------------------------------------------------
# reprojection
# --------------------------------------------------------------------------


@lru_cache(maxsize=128)
def _transformer(epsg: int) -> Transformer:
    """Cached ``epsg`` -> EPSG:4326 transformer in longitude/latitude order."""
    try:
        source = CRS.from_epsg(epsg)
    except CRSError as exc:  # pragma: no cover - depends on the PROJ database
        raise ValueError(f"{epsg} is not a known EPSG code") from exc
    return Transformer.from_crs(source, CRS.from_epsg(WGS84_EPSG), always_xy=True)


def _to_wgs84(geom: BaseGeometry, epsg: int) -> BaseGeometry:
    if epsg == WGS84_EPSG:
        return geom

    transformer = _transformer(epsg)

    def _project(coords: np.ndarray) -> np.ndarray:
        if coords.size == 0:
            return coords
        # pyproj transforms buffers in place, so hand it contiguous copies of
        # the strided columns shapely gives us.
        x = np.ascontiguousarray(coords[:, 0], dtype="float64")
        y = np.ascontiguousarray(coords[:, 1], dtype="float64")
        if coords.shape[1] > 2:
            z = np.ascontiguousarray(coords[:, 2], dtype="float64")
            x, y, z = transformer.transform(x, y, z)
            return np.column_stack((x, y, z))
        x, y = transformer.transform(x, y)
        return np.column_stack((x, y))

    return shapely.transform(geom, _project, include_z=bool(shapely.has_z(geom)))


# --------------------------------------------------------------------------
# antimeridian cutting (RFC 7946 Section 3.1.9)
# --------------------------------------------------------------------------


def _wrap_longitudes(coords: np.ndarray) -> np.ndarray:
    if coords.size == 0:
        return coords
    lon = coords[:, 0]
    wrapped = ((lon + 180.0) % 360.0) - 180.0
    out = coords.copy()
    out[:, 0] = np.where((lon >= -180.0) & (lon <= 180.0), lon, wrapped)
    return out


def _leaves(geom: BaseGeometry) -> list[BaseGeometry]:
    """Flatten multi-part and collection geometries into single parts."""
    if geom.is_empty:
        return []
    if hasattr(geom, "geoms"):
        parts: list[BaseGeometry] = []
        for part in geom.geoms:
            parts.extend(_leaves(part))
        return parts
    return [geom]


def _cut_antimeridian(geom: BaseGeometry) -> BaseGeometry:
    """Split ``geom`` so that no part reaches beyond +/-180 deg longitude."""
    if geom.is_empty:
        return geom

    minx, miny, maxx, maxy = geom.bounds
    if minx >= -180.0 and maxx <= 180.0:
        return geom
    if maxx - minx > 360.0:
        raise ValueError(
            "geometry spans more than 360 degrees of longitude and cannot be "
            "represented in RFC 7946 coordinates"
        )

    if geom.geom_type in ("Point", "MultiPoint"):
        return shapely.transform(
            geom, _wrap_longitudes, include_z=bool(shapely.has_z(geom))
        )

    # Lines and areas are cut with a planar overlay, which is 2D only.
    if bool(shapely.has_z(geom)):
        geom = shapely.force_2d(geom)

    dimension = _DIMENSION.get(geom.geom_type, 2)
    # Bands are [-180 + 360k, 180 + 360k]; keep those that overlap the extent.
    k_first = math.floor((minx - 180.0) / 360.0) + 1
    k_last = math.ceil((maxx + 180.0) / 360.0) - 1

    parts: list[BaseGeometry] = []
    for k in range(k_first, k_last + 1):
        band = box(-180.0 + 360.0 * k, miny - 1.0, 180.0 + 360.0 * k, maxy + 1.0)
        clipped = geom.intersection(band)
        if clipped.is_empty:
            continue
        if k:
            clipped = translate(clipped, xoff=-360.0 * k)
        # An overlay can shed lower-dimensional crumbs where the geometry only
        # touches a band edge; keep just the parts of the original dimension.
        parts.extend(
            part
            for part in _leaves(clipped)
            if _DIMENSION.get(part.geom_type) == dimension
        )

    if not parts:
        return geom
    if len(parts) == 1:
        return parts[0]
    return MultiPolygon(parts) if dimension == 2 else MultiLineString(parts)


# --------------------------------------------------------------------------
# coordinate encoding
# --------------------------------------------------------------------------


def _round(value: float, precision: int | None) -> float:
    if precision is not None:
        value = round(value, precision)
    # Adding zero folds -0.0 into 0.0 without touching any other value.
    return value + 0.0


def _position(
    row: np.ndarray, xy_precision: int | None, z_precision: int | None
) -> list[float]:
    lon = float(row[0])
    lat = float(row[1])
    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise ValueError(
            "reprojection produced a non-finite coordinate, which cannot be "
            "represented in JSON; check that the geometry lies inside the area "
            "of use of the source CRS"
        )
    if abs(lat) > 90.0:
        if abs(lat) > 90.0 + _LAT_TOLERANCE:
            raise ValueError(f"latitude {lat} is outside the valid range [-90, 90]")
        lat = math.copysign(90.0, lat)

    position = [_round(lon, xy_precision), _round(lat, xy_precision)]

    if len(row) > 2:
        altitude = float(row[2])
        if not math.isnan(altitude):
            if not math.isfinite(altitude):
                raise ValueError("reprojection produced a non-finite elevation")
            position.append(_round(altitude, z_precision))
    return position


def _positions(
    geom: BaseGeometry, xy_precision: int | None, z_precision: int | None
) -> list[list[float]]:
    coords = shapely.get_coordinates(geom, include_z=bool(shapely.has_z(geom)))
    return [_position(row, xy_precision, z_precision) for row in coords]


def _signed_area(ring: list[list[float]]) -> float:
    """Shoelace area of a closed ring; positive means counter-clockwise."""
    total = 0.0
    for start, end in zip(ring, ring[1:]):
        total += start[0] * end[1] - end[0] * start[1]
    return total / 2.0


def _ring(
    ring: BaseGeometry,
    counter_clockwise: bool,
    xy_precision: int | None,
    z_precision: int | None,
) -> list[list[float]]:
    positions = _positions(ring, xy_precision, z_precision)
    if positions and positions[0] != positions[-1]:
        positions.append(list(positions[0]))
    if len(positions) < 4:
        raise ValueError(
            "a GeoJSON linear ring needs at least four positions, got "
            f"{len(positions)}"
        )
    area = _signed_area(positions)
    if area != 0.0 and (area > 0.0) != counter_clockwise:
        positions.reverse()
    return positions


def _rings(
    polygon: BaseGeometry, xy_precision: int | None, z_precision: int | None
) -> list[list[list[float]]]:
    if polygon.is_empty:
        return []
    rings = [_ring(polygon.exterior, True, xy_precision, z_precision)]
    rings.extend(
        _ring(hole, False, xy_precision, z_precision) for hole in polygon.interiors
    )
    return rings


def _line(
    line: BaseGeometry, xy_precision: int | None, z_precision: int | None
) -> list[list[float]]:
    positions = _positions(line, xy_precision, z_precision)
    if positions and len(positions) < 2:
        raise ValueError("a GeoJSON LineString needs at least two positions")
    return positions


# --------------------------------------------------------------------------
# dispatch
# --------------------------------------------------------------------------


def _convert(
    geom: BaseGeometry,
    epsg: int,
    xy_precision: int | None,
    z_precision: int | None,
    split_antimeridian: bool,
) -> dict[str, Any]:
    geom_type = geom.geom_type

    if geom_type == "GeometryCollection":
        # A collection carries "geometries", not "coordinates"; convert each
        # member independently so mixed 2D/3D members are handled correctly.
        return {
            "type": "GeometryCollection",
            "geometries": [
                _convert(part, epsg, xy_precision, z_precision, split_antimeridian)
                for part in geom.geoms
            ],
        }

    if geom_type == "LinearRing":
        # Not a GeoJSON type: a closed LineString is the faithful encoding.
        geom = LineString(geom.coords)

    if geom_type not in _DIMENSION:
        raise TypeError(f"{geom_type} has no RFC 7946 equivalent")

    geom = _to_wgs84(geom, epsg)
    if split_antimeridian:
        geom = _cut_antimeridian(geom)

    geom_type = geom.geom_type
    coordinates: Any

    if geom_type == "Point":
        positions = _positions(geom, xy_precision, z_precision)
        coordinates = positions[0] if positions else []
    elif geom_type == "MultiPoint":
        coordinates = [
            _positions(part, xy_precision, z_precision)[0]
            for part in geom.geoms
            if not part.is_empty
        ]
    elif geom_type == "LineString":
        coordinates = _line(geom, xy_precision, z_precision)
    elif geom_type == "MultiLineString":
        coordinates = [
            _line(part, xy_precision, z_precision)
            for part in geom.geoms
            if not part.is_empty
        ]
    elif geom_type == "Polygon":
        coordinates = _rings(geom, xy_precision, z_precision)
    elif geom_type == "MultiPolygon":
        coordinates = [
            _rings(part, xy_precision, z_precision)
            for part in geom.geoms
            if not part.is_empty
        ]
    else:  # pragma: no cover - shapely has no other concrete geometry types
        raise TypeError(f"{geom_type} has no RFC 7946 equivalent")

    return {"type": geom_type, "coordinates": coordinates}
```