Here's the module.

```python
"""Convert shapely geometries into RFC 7946 (GeoJSON) geometry objects.

RFC 7946 fixes the coordinate reference system to WGS 84 with longitude,
latitude ordering, so geometries are reprojected from their source CRS to
EPSG:4326 before being serialized.  The returned value is a plain ``dict``
built from JSON-native types only (``str``, ``list``, ``float``), so it can be
handed straight to ``json.dumps``.

Conformance notes
-----------------
* Coordinates are emitted as ``[longitude, latitude]`` or, when the source
  geometry is 3D, ``[longitude, latitude, altitude]`` (RFC 7946 §3.1.1).
  M values are dropped: the RFC permits at most three elements per position.
* Polygon rings follow the right-hand rule -- exterior rings counterclockwise,
  interior rings clockwise (§3.1.6) -- and are explicitly closed.
* ``LinearRing`` has no GeoJSON counterpart and is emitted as a ``LineString``.
* Longitudes that fall outside ``[-180, 180]`` after reprojection (common when
  coming from a projected CRS such as EPSG:3857, which extends past the
  antimeridian) are wrapped back into range.  Antimeridian *cutting* of lines
  and polygons (§3.1.9, a SHOULD) is deliberately not performed, since it
  changes the topology of the geometry; cut such geometries beforehand if you
  need it.
* Empty ``Point`` and ``LineString`` geometries have no conforming
  representation and raise ``ValueError``; use a ``null`` GeoJSON geometry for
  an unlocated feature instead.  Empty polygons and empty collections are
  representable and produce an empty ``coordinates``/``geometries`` array.
"""

from __future__ import annotations

import threading
from typing import Any

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry

__all__ = ["to_rfc7946"]

_WGS84_EPSG = 4326

# Tolerance for latitudes that overshoot the poles purely through floating
# point error during reprojection; anything larger is a real problem.
_LAT_TOL = 1e-9

# pyproj Transformer objects are not documented as thread-safe, so the cache is
# per thread rather than global.
_local = threading.local()


def to_rfc7946(
    geom: BaseGeometry, epsg: int, *, precision: int | None = None
) -> dict[str, Any]:
    """Return ``geom`` as an RFC 7946 GeoJSON geometry object.

    Parameters
    ----------
    geom:
        Any shapely geometry.  Its coordinates are interpreted in easting,
        northing (equivalently longitude, latitude) order, which is shapely's
        convention regardless of the authority axis order of ``epsg``.
    epsg:
        Integer EPSG code of the CRS ``geom``'s coordinates are expressed in,
        e.g. ``4326`` or ``3857``.
    precision:
        Optional number of decimal places to round the output coordinates to
        (RFC 7946 §11.2 asks that precision not exceed the accuracy of the
        data).  ``None``, the default, keeps full precision.

    Returns
    -------
    dict
        A GeoJSON geometry object: ``{"type": ..., "coordinates": ...}``, or
        ``{"type": "GeometryCollection", "geometries": [...]}``.
    """
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"geom must be a shapely geometry, got {type(geom).__name__}")
    if isinstance(epsg, bool) or not isinstance(epsg, (int, np.integer)):
        raise TypeError(f"epsg must be an integer EPSG code, got {epsg!r}")
    if precision is not None:
        if isinstance(precision, bool) or not isinstance(precision, (int, np.integer)):
            raise TypeError("precision must be an integer or None")
        precision = int(precision)
        if precision < 0:
            raise ValueError("precision must be non-negative")

    return _encode(geom, _transformer(int(epsg)), precision)


def _transformer(epsg: int) -> Transformer | None:
    """Transformer from ``epsg`` to WGS 84 lon/lat, or None if already there."""
    if epsg == _WGS84_EPSG:
        return None
    cache = getattr(_local, "transformers", None)
    if cache is None:
        cache = _local.transformers = {}
    transformer = cache.get(epsg)
    if transformer is None:
        source = CRS.from_epsg(epsg)  # raises CRSError for unknown codes
        transformer = Transformer.from_crs(
            source, CRS.from_epsg(_WGS84_EPSG), always_xy=True
        )
        cache[epsg] = transformer
    return transformer


def _encode(
    geom: BaseGeometry, transformer: Transformer | None, precision: int | None
) -> dict[str, Any]:
    kind = geom.geom_type

    if kind == "Point":
        positions = _positions(geom, transformer, precision)
        if not positions:
            raise ValueError(
                "an empty Point has no RFC 7946 representation; a GeoJSON "
                "Point requires a position"
            )
        return {"type": "Point", "coordinates": positions[0]}

    if kind in ("LineString", "LinearRing"):
        positions = _positions(geom, transformer, precision)
        if len(positions) < 2:
            raise ValueError(
                "a GeoJSON LineString requires at least two positions; got "
                f"{len(positions)}"
            )
        return {"type": "LineString", "coordinates": positions}

    if kind == "Polygon":
        return {"type": "Polygon", "coordinates": _rings(geom, transformer, precision)}

    if kind == "MultiPoint":
        return {
            "type": "MultiPoint",
            "coordinates": [
                _encode(part, transformer, precision)["coordinates"]
                for part in geom.geoms
            ],
        }

    if kind == "MultiLineString":
        return {
            "type": "MultiLineString",
            "coordinates": [
                _encode(part, transformer, precision)["coordinates"]
                for part in geom.geoms
            ],
        }

    if kind == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [_rings(part, transformer, precision) for part in geom.geoms],
        }

    if kind == "GeometryCollection":
        return {
            "type": "GeometryCollection",
            "geometries": [_encode(part, transformer, precision) for part in geom.geoms],
        }

    raise TypeError(f"unsupported geometry type: {kind}")


def _rings(
    polygon: BaseGeometry, transformer: Transformer | None, precision: int | None
) -> list[list[list[float]]]:
    if polygon.is_empty:
        return []
    rings = [_ring(polygon.exterior, transformer, precision, ccw=True)]
    rings.extend(
        _ring(interior, transformer, precision, ccw=False)
        for interior in polygon.interiors
    )
    return rings


def _ring(
    ring: BaseGeometry,
    transformer: Transformer | None,
    precision: int | None,
    *,
    ccw: bool,
) -> list[list[float]]:
    positions = _positions(ring, transformer, precision)
    if len(positions) < 4:
        raise ValueError(
            "a GeoJSON linear ring requires at least four positions; got "
            f"{len(positions)}"
        )
    # Reprojection and rounding can both break the closure shapely guarantees.
    if positions[0] != positions[-1]:
        positions[-1] = list(positions[0])

    area = _signed_area(positions)
    if (area > 0.0 and not ccw) or (area < 0.0 and ccw):
        positions.reverse()
    return positions


def _signed_area(ring: list[list[float]]) -> float:
    """Shoelace area of a closed ring; positive means counterclockwise."""
    total = 0.0
    for (x1, y1), (x2, y2) in zip(
        ((p[0], p[1]) for p in ring[:-1]), ((p[0], p[1]) for p in ring[1:])
    ):
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _positions(
    geom: BaseGeometry, transformer: Transformer | None, precision: int | None
) -> list[list[float]]:
    """Reproject a single coordinate sequence into RFC 7946 positions."""
    coords = shapely.get_coordinates(geom, include_z=True)  # (N, 3); M ignored
    if coords.size == 0:
        return []
    if not shapely.has_z(geom):
        coords = np.array(coords[:, :2])
    if not np.isfinite(coords).all():
        raise ValueError("geometry contains non-finite coordinate values")

    if transformer is not None:
        if coords.shape[1] == 3:
            x, y, z = transformer.transform(
                coords[:, 0], coords[:, 1], coords[:, 2], errcheck=True
            )
            coords = np.column_stack((x, y, z))
        else:
            x, y = transformer.transform(coords[:, 0], coords[:, 1], errcheck=True)
            coords = np.column_stack((x, y))
        if not np.isfinite(coords).all():
            raise ValueError(
                "reprojection to EPSG:4326 produced non-finite coordinates; the "
                "input may fall outside the area of use of the source CRS"
            )

    lon = coords[:, 0]
    outside = np.abs(lon) > 180.0
    if outside.any():
        coords[:, 0] = np.where(outside, ((lon + 180.0) % 360.0) - 180.0, lon)

    lat = coords[:, 1]
    if (np.abs(lat) > 90.0 + _LAT_TOL).any():
        raise ValueError("latitude outside [-90, 90] after reprojection to EPSG:4326")
    coords[:, 1] = np.clip(lat, -90.0, 90.0)

    if precision is not None:
        coords = np.round(coords, precision)
        # -0.0 is legal JSON but round-trips badly through some parsers.
        coords = coords + 0.0

    return [[float(value) for value in position] for position in coords]
```