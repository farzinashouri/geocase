"""Build WKT ``POINT`` geometries from WGS84 latitude/longitude pairs.

Axis order is the whole point of this module, so it is worth stating twice:

* The **public API** takes ``(lat, lon)`` — the order used by human-facing
  inputs (GPS readouts, map URLs, address geocoders, EPSG:4326's own
  authority-defined axis order).
* The **WKT output** is ``POINT (x y)`` — that is, ``POINT (lon lat)``.
  Every mainstream WKT consumer (PostGIS, GDAL/OGR, shapely, GeoPandas,
  QGIS, BigQuery GIS) reads the first ordinate as easting/longitude.

Swapping these is the classic silent failure: ``POINT (37.77 -122.42)``
parses without complaint and quietly places San Francisco in Kazakhstan, or
throws the geometry off the globe entirely once |lat| > 90 lands in the
longitude slot. Hence the conversion happens in exactly one place, here.

Importing this module has no side effects and requires only the standard
library.
"""

from __future__ import annotations

import math
from typing import Union

__all__ = ["wkt_from_latlon"]

Number = Union[float, int, str]

# 12 decimal degrees is well under a micrometre at the equator, i.e. far
# beyond any real WGS84 measurement, and is only used as a fallback when a
# value would otherwise be rendered in scientific notation.
_FALLBACK_DECIMALS = 12


def _coerce(name: str, value: Number) -> float:
    """Return ``value`` as a finite float, or raise a descriptive error."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real number, got {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number, got {number!r}")
    return number


def _format_ordinate(value: float) -> str:
    """Render one ordinate in a form every WKT parser accepts.

    ``repr`` gives the shortest round-trippable decimal, but for very small
    magnitudes it produces exponent notation (``1e-07``), which the OGC WKT
    grammar does not include and which several parsers reject. Those cases
    fall back to plain fixed-point.
    """
    text = repr(value)
    if "e" in text or "E" in text:
        text = f"{value:.{_FALLBACK_DECIMALS}f}"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
    if text in ("-0", "-0.0"):  # negative zero is noise, not information
        return "0"
    return text


def wkt_from_latlon(lat: Number, lon: Number) -> str:
    """Return the WGS84 WKT ``POINT`` for a latitude/longitude pair.

    Args:
        lat: Latitude in decimal degrees, in ``[-90, 90]``.
        lon: Longitude in decimal degrees, in ``[-180, 180]``.

    Returns:
        A WKT point string in GIS axis order, e.g.
        ``wkt_from_latlon(37.7749, -122.4194)`` -> ``'POINT (-122.4194 37.7749)'``.

    Raises:
        TypeError: If an argument is not convertible to a float.
        ValueError: If an argument is non-finite or outside its valid range.

    Note:
        Longitudes are validated, not wrapped: ``190`` is treated as a caller
        error rather than silently normalised to ``-170``, since an
        out-of-range value far more often means the arguments were swapped or
        the units were wrong than that a deliberate wrap was intended.
    """
    latitude = _coerce("lat", lat)
    longitude = _coerce("lon", lon)

    if not -90.0 <= latitude <= 90.0:
        raise ValueError(
            f"lat must be within [-90, 90] degrees, got {latitude!r} "
            "(arguments are (lat, lon) — check whether they were swapped)"
        )
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(
            f"lon must be within [-180, 180] degrees, got {longitude!r}"
        )

    # WKT is x-first: longitude precedes latitude.
    return f"POINT ({_format_ordinate(longitude)} {_format_ordinate(latitude)})"