"""Build WKT ``POINT`` strings from WGS84 latitude/longitude pairs.

The single trap this module exists to hide: WKT — like every OGC geometry
encoding, and like the geometry readers in GEOS/shapely, PostGIS, GDAL and
QGIS — is ordered ``x y``, i.e. ``POINT (longitude latitude)``, whereas
user-facing APIs conventionally accept ``(lat, lon)``.  Feeding a
``POINT (lat lon)`` string to those tools does not fail loudly; it silently
places the point somewhere else on the planet (or off it).  So
``wkt_from_latlon`` takes the human order and emits the machine order.

Only the standard library is used, and importing the module has no side
effects.

Coordinates outside the WGS84 domain raise ``ValueError`` rather than being
silently wrapped or clamped: normalizing e.g. 0..360 longitudes is the
caller's decision, not this function's.
"""

from __future__ import annotations

import math
from decimal import Decimal

__all__ = ["wkt_from_latlon"]

_LAT_LIMIT = 90.0
_LON_LIMIT = 180.0


def _as_finite_float(value: object, name: str) -> float:
    """Coerce ``value`` to a finite ``float`` or raise."""
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real number, got {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return result


def _format_ordinate(value: float) -> str:
    """Return the shortest round-tripping decimal text for ``value``.

    ``repr`` gives the shortest string that reads back as the same double,
    but switches to exponent form for magnitudes below 1e-4 (``'1e-07'``).
    Exponent notation is legal in most WKT parsers yet not universally
    accepted, so the value is re-rendered as plain decimal via ``Decimal``.
    Negative zero collapses to ``'0'``.
    """
    if value == 0.0:
        return "0"
    text = format(Decimal(repr(value)), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return the WKT ``POINT`` for a WGS84 location given as ``(lat, lon)``.

    Parameters
    ----------
    lat:
        Latitude in decimal degrees, within ``[-90, 90]``.
    lon:
        Longitude in decimal degrees, within ``[-180, 180]``.

    Returns
    -------
    str
        ``"POINT (<lon> <lat>)"`` — axis-swapped into the ``x y`` order that
        WKT requires, with full double precision preserved.

    Raises
    ------
    TypeError
        If an argument is not a real number.
    ValueError
        If an argument is not finite or falls outside its valid range.

    Examples
    --------
    >>> wkt_from_latlon(45.5152, -122.6784)   # Portland, OR
    'POINT (-122.6784 45.5152)'
    >>> wkt_from_latlon(0, 0)
    'POINT (0 0)'
    >>> wkt_from_latlon(1e-7, -1e-7)
    'POINT (-0.0000001 0.0000001)'
    """
    latitude = _as_finite_float(lat, "lat")
    longitude = _as_finite_float(lon, "lon")

    if abs(latitude) > _LAT_LIMIT:
        # A latitude past the poles is most often a swapped-argument bug.
        hint = (
            " — arguments are (lat, lon); they may be swapped"
            if abs(longitude) <= _LAT_LIMIT
            else ""
        )
        raise ValueError(
            f"lat must be within [-90, 90], got {latitude!r}{hint}"
        )
    if abs(longitude) > _LON_LIMIT:
        raise ValueError(f"lon must be within [-180, 180], got {longitude!r}")

    return f"POINT ({_format_ordinate(longitude)} {_format_ordinate(latitude)})"