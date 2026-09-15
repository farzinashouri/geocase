```python
"""Convert a shapely geometry to an RFC 7946 GeoJSON *geometry object*.

The single public entry point is :func:`to_rfc7946`.  Importing this module has
no side effects (the pyproj transformers are built lazily and cached).

RFC 7946 conformance notes
--------------------------
* **CRS** (section 4): GeoJSON coordinates are always WGS 84 longitude/latitude,
  so the input geometry is reprojected from ``epsg`` to EPSG:4326.  The
  transformer is built with ``always_xy=True`` so the output is ordered
  ``[longitude, latitude]`` regardless of the authority axis order of either CRS.
* **Positions** (section 3.1.1): emitted as ``[lon, lat]``, or ``[lon, lat, alt]``
  when the input geometry carries a Z value.  Z passes through the transformer
  unchanged unless the source CRS is 3D/compound; no vertical datum shift is
  invented.  M values are dropped - GeoJSON has no place for them.
* **Ring winding** (section 3.1.6): exterior rings are emitted counterclockwise
  and interior rings clockwise, and every ring is explicitly closed.
* **Antimeridian** (section 3.1.9): geometries whose longitudes fall outside
  [-180, 180] after reprojection are cut at the antimeridian into the
  equivalent multi-geometry rather than being naively wrapped (which would
  otherwise draw a segment right across the globe).  Geometries already inside
  the range are left untouched, since RFC 7946 interprets segments as straight
  Cartesian lines in longitude/latitude space.
* **GeometryCollection** (section 3.1.8): supported, returning a ``geometries``
  member instead of ``coordinates``.  Nested collections, which the RFC says
  SHOULD NOT be produced, are flattened into the parent.
* **Empty geometries**: emitted with an empty ``coordinates`` array, which
  section 3.1 explicitly allows processors to treat as a null object.
* **Precision** (section 11.2): no rounding is applied by default so the
  conversion is lossless; pass ``precision=6`` for the ~10 cm resolution the RFC
  suggests is usually sufficient.

All returned values are plain ``dict``/``list``/``float`` objects, directly
usable with ``json.dumps``.
"""

from __future__ import annotations

import math
import numbers
from functools import lru_cache
from typing import Any, Dict, Iterator, List, Optional, Sequence

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.affinity import translate
from shapely.errors import GEOSException
from shapely.geometry import MultiLineString, MultiPolygon, box
from shapely.geometry.base import BaseGeometry

__all__ = ["to_rfc7946"]

WGS84_EPSG = 4326

# Round-off slack (in degrees) allowed before an out-of-range coordinate is
# treated as an error rather than snapped back onto the valid domain.
_LAT_TOL = 1e-6
_LON_TOL = 1e-6

_COLLECTION_TYPES = frozenset(
    {"MultiPoint", "MultiLineString", "MultiPolygon", "GeometryCollection"}
)


def to_rfc7946(
    geom: BaseGeometry, epsg: int, *, precision: Optional[int] = None
) -> Dict[str, Any]:
    """Return ``geom`` as an RFC 7946 GeoJSON geometry object.

    Parameters
    ----------
    geom:
        A shapely geometry whose coordinates are expressed in ``epsg``.
    epsg:
        Integer EPSG code of the geometry's coordinate reference system
        (e.g. ``4326``, ``3857``, ``27700``).
    precision:
        Optional number of decimal places to round the output coordinates to.
        ``None`` (the default) keeps full precision.

    Returns
    -------
    dict
        A GeoJSON geometry object with ``type`` and ``coordinates`` members
        (``geometries`` for a GeometryCollection).

    Raises
    ------
    TypeError
        If ``geom`` is not a shapely geometry, ``epsg`` is not an integer, or
        the geometry type has no GeoJSON equivalent.
    ValueError
        If the coordinates cannot be transformed to WGS 84, fall impossibly far
        outside the valid longitude/latitude domain, or form a linear ring with
        fewer than four positions.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"geom must be a shapely geometry, got {type(geom).__name__}")
    if isinstance(epsg, bool) or not isinstance(epsg, numbers.Integral):
        raise TypeError(f"epsg must be an integer EPSG code, got {epsg!r}")
    if precision is not None:
        if isinstance(precision, bool) or not isinstance(precision, numbers.Integral):
            raise TypeError(f"precision must be an integer or None, got {precision!r}")
        if precision < 0:
            raise ValueError("precision must be non-negative")
        precision = int(precision)

    return _convert(geom, int(epsg), precision)


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
def _convert(geom: BaseGeometry, epsg: int, precision: Optional[int]) -> Dict[str, Any]:
    if geom.geom_type == "GeometryCollection":
        # RFC 7946 3.1.8: a GeometryCollection SHOULD NOT contain other
        # GeometryCollections, so nested ones are flattened away.
        return {
            "type": "GeometryCollection",
            "geometries": [
                _convert(part, epsg, precision) for part in _flatten_collection(geom)
            ],
        }

    wgs84 = _to_wgs84(geom, epsg)
    wgs84 = _clamp_latitude(wgs84)
    wgs84 = _cut_antimeridian(wgs84)
    return _emit(wgs84, precision)


def _flatten_collection(geom: BaseGeometry) -> Iterator[BaseGeometry]:
    for part in geom.geoms:
        if part.geom_type == "GeometryCollection":
            yield from _flatten_collection(part)
        else:
            yield part


@lru_cache(maxsize=64)
def _transformer(epsg: int) -> Transformer:
    """Build (once per EPSG code) a transformer to WGS 84 in lon/lat order."""
    return Transformer.from_crs(
        CRS.from_epsg(epsg), CRS.from_epsg(WGS84_EPSG), always_xy=True
    )


def _to_wgs84(geom: BaseGeometry, epsg: int) -> BaseGeometry:
    if epsg == WGS84_EPSG or geom.is_empty:
        return geom

    transformer = _transformer(epsg)
    has_z = bool(geom.has_z)

    def _apply(coords: np.ndarray) -> np.ndarray:
        columns = [coords[:, i] for i in range(coords.shape[1])]
        result = np.column_stack(transformer.transform(*columns, errcheck=False))
        if not np.isfinite(result[:, :2]).all():
            raise ValueError(
                f"coordinates could not be transformed from EPSG:{epsg} to "
                f"EPSG:{WGS84_EPSG}; they lie outside the domain of the "
                "transformation"
            )
        return result

    return shapely.transform(geom, _apply, include_z=has_z)


def _clamp_latitude(geom: BaseGeometry) -> BaseGeometry:
    """Snap latitudes nudged past a pole by round-off back onto [-90, 90]."""
    if geom.is_empty:
        return geom

    _, miny, _, maxy = geom.bounds
    if miny >= -90.0 and maxy <= 90.0:
        return geom
    if miny < -90.0 - _LAT_TOL or maxy > 90.0 + _LAT_TOL:
        raise ValueError(
            f"latitudes [{miny}, {maxy}] fall outside the valid range [-90, 90]"
        )

    def _apply(coords: np.ndarray) -> np.ndarray:
        clamped = coords.copy()
        np.clip(clamped[:, 1], -90.0, 90.0, out=clamped[:, 1])
        return clamped

    return shapely.transform(geom, _apply, include_z=bool(geom.has_z))


def _cut_antimeridian(geom: BaseGeometry) -> BaseGeometry:
    """Cut a geometry that leaves [-180, 180] into pieces per RFC 7946 3.1.9."""
    if geom.is_empty:
        return geom

    minx, _, maxx, _ = geom.bounds
    if minx >= -180.0 and maxx <= 180.0:
        return geom

    dimension = int(shapely.get_dimensions(geom))
    if dimension == 0:
        # Points carry no segments, so wrapping the longitude is lossless.
        return geom

    # Tile k spans longitudes [-180 + 360k, 180 + 360k].
    k_lo = math.ceil((minx - 180.0) / 360.0)
    k_hi = math.floor((maxx + 180.0) / 360.0)

    parts: List[BaseGeometry] = []
    for k in range(k_lo, k_hi + 1):
        clip = box(-180.0 + 360.0 * k, -90.0, 180.0 + 360.0 * k, 90.0)
        try:
            piece = geom.intersection(clip)
        except GEOSException as exc:  # pragma: no cover - depends on input
            raise ValueError(
                "geometry crosses the antimeridian but is topologically "
                "invalid, so it cannot be cut; repair it first (e.g. with "
                "shapely.make_valid)"
            ) from exc
        if piece.is_empty:
            continue
        if k:
            piece = translate(piece, xoff=-360.0 * k)
        # Tiles that only touch the geometry yield lower-dimensional slivers.
        parts.extend(p for p in _explode(piece) if shapely.get_dimensions(p) == dimension)

    if not parts:
        return geom
    if len(parts) == 1 and geom.geom_type not in _COLLECTION_TYPES:
        return parts[0]
    return MultiLineString(parts) if dimension == 1 else MultiPolygon(parts)


def _explode(geom: BaseGeometry) -> Iterator[BaseGeometry]:
    if geom.is_empty:
        return
    if geom.geom_type in _COLLECTION_TYPES:
        for part in geom.geoms:
            yield from _explode(part)
    else:
        yield geom


# --------------------------------------------------------------------------- #
# Emission
# --------------------------------------------------------------------------- #
def _emit(geom: BaseGeometry, precision: Optional[int]) -> Dict[str, Any]:
    geom_type = geom.geom_type

    if geom_type == "Point":
        coordinates: Any = [] if geom.is_empty else _position(geom.coords[0], precision)
        return {"type": "Point", "coordinates": coordinates}

    if geom_type in ("LineString", "LinearRing"):
        # GeoJSON has no LinearRing; a closed LineString is the faithful form.
        return {
            "type": "LineString",
            "coordinates": _positions(geom.coords, precision, minimum=2),
        }

    if geom_type == "Polygon":
        return {"type": "Polygon", "coordinates": _rings(geom, precision)}

    if geom_type == "MultiPoint":
        return {
            "type": "MultiPoint",
            "coordinates": [
                _position(part.coords[0], precision)
                for part in geom.geoms
                if not part.is_empty
            ],
        }

    if geom_type == "MultiLineString":
        return {
            "type": "MultiLineString",
            "coordinates": [
                _positions(part.coords, precision, minimum=2)
                for part in geom.geoms
                if not part.is_empty
            ],
        }

    if geom_type == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [
                _rings(part, precision) for part in geom.geoms if not part.is_empty
            ],
        }

    raise TypeError(f"{geom_type} has no RFC 7946 equivalent")


def _rings(polygon: BaseGeometry, precision: Optional[int]) -> List[List[List[float]]]:
    if polygon.is_empty:
        return []
    rings = [_ring(polygon.exterior, precision, counterclockwise=True)]
    rings.extend(
        _ring(interior, precision, counterclockwise=False)
        for interior in polygon.interiors
    )
    return rings


def _ring(
    ring: BaseGeometry, precision: Optional[int], counterclockwise: bool
) -> List[List[float]]:
    coordinates = _positions(ring.coords, precision, minimum=4)
    if len(coordinates) < 4:
        raise ValueError(
            "a linear ring requires at least four positions, "
            f"got {len(coordinates)}"
        )
    if coordinates[0] != coordinates[-1]:
        coordinates.append(list(coordinates[0]))

    # RFC 7946 3.1.6: right-hand rule - exteriors counterclockwise, holes
    # clockwise. Checked on the emitted values so the output is what conforms.
    area = _signed_area(coordinates)
    if area and (area > 0.0) != counterclockwise:
        coordinates.reverse()
    return coordinates


def _signed_area(ring: Sequence[Sequence[float]]) -> float:
    total = 0.0
    for (x1, y1, *_), (x2, y2, *_) in zip(ring, ring[1:]):
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _positions(
    coords: Sequence[Sequence[float]], precision: Optional[int], minimum: int
) -> List[List[float]]:
    positions = [_position(coord, precision) for coord in coords]
    if positions and len(positions) < minimum:
        raise ValueError(
            f"expected at least {minimum} positions, got {len(positions)}"
        )
    return positions


def _position(coord: Sequence[float], precision: Optional[int]) -> List[float]:
    position = [
        _number(_normalize_longitude(coord[0]), precision),
        _number(_normalize_latitude(coord[1]), precision),
    ]
    if len(coord) > 2:
        altitude = float(coord[2])
        if not math.isnan(altitude):
            position.append(_number(altitude, precision))
    return position


def _normalize_longitude(value: float) -> float:
    longitude = float(value)
    if not math.isfinite(longitude):
        raise ValueError("longitude must be a finite number")
    if -180.0 <= longitude <= 180.0:
        return longitude
    # Snap tiny overshoots from the antimeridian cut, wrap anything genuinely
    # outside a single revolution.
    if longitude - 180.0 <= _LON_TOL and longitude > 180.0:
        return 180.0
    if -180.0 - longitude <= _LON_TOL and longitude < -180.0:
        return -180.0
    return ((longitude + 180.0) % 360.0) - 180.0


def _normalize_latitude(value: float) -> float:
    latitude = float(value)
    if not math.isfinite(latitude):
        raise ValueError("latitude must be a finite number")
    if -90.0 <= latitude <= 90.0:
        return latitude
    if abs(latitude) - 90.0 <= _LAT_TOL:
        return math.copysign(90.0, latitude)
    raise ValueError(f"latitude {latitude} falls outside the valid range [-90, 90]")


def _number(value: float, precision: Optional[int]) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("coordinates must be finite numbers")
    if precision is not None:
        number = round(number, precision)
    if number == 0.0:
        number = 0.0  # normalise -0.0
    return number
```