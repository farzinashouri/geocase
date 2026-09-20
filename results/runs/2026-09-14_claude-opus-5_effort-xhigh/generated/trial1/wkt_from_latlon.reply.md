WKT axis order is `X Y`, so a lat/lon pair has to be emitted as `POINT(lon lat)` — that swap is the whole substance of this module.

```python
"""Build WKT ``POINT`` geometry from WGS84 latitude/longitude pairs.

The single fact this module exists to get right: WKT is an axis-ordered
format and its axes are ``X Y``.  For geographic coordinates that means
``POINT(lon lat)``.  Callers almost always hold the pair the other way
round -- "lat, lon" is how coordinates are spoken, typed into search boxes,
and returned by geocoders -- so :func:`wkt_from_latlon` accepts ``(lat, lon)``
and performs the swap itself.

Writing ``POINT(lat lon)`` instead is the classic failure here: it yields a
syntactically valid geometry that silently lands in the wrong place once
loaded into PostGIS, QGIS, GDAL/OGR, or shapely -- and for many mid-latitude
locations the transposed longitude still falls inside the valid ``[-90, 90]``
latitude band, so no parser will complain.

The output carries no SRID prefix (plain WKT, per OGC SFA); coordinates are
WGS84 / EPSG:4326 by construction and should be tagged as such by whatever
consumes the string.
"""

from __future__ import annotations

import math

__all__ = ["wkt_from_latlon"]

# Degrees of precision kept in the output.  1e-9 degrees is roughly 0.1 mm at
# the equator -- far finer than any WGS84 fix -- while staying clear of the
# exponent notation (``1e-05``) that repr() would produce for near-zero
# ordinates and that some WKT parsers reject.
_DECIMALS = 9

_MAX_LATITUDE = 90.0
_MAX_LONGITUDE = 180.0


def _as_float(value: object, name: str) -> float:
    """Coerce *value* to a finite float or raise with a pointed message."""
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real number, got {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return number


def _format_ordinate(value: float) -> str:
    """Render *value* in fixed-point notation without trailing noise."""
    text = f"{value:.{_DECIMALS}f}".rstrip("0").rstrip(".")
    # Collapse "-0" (and any negative value rounded down to zero) to "0" so the
    # same location never produces two different strings.
    return "0" if text in ("", "-", "-0") else text


def wkt_from_latlon(lat, lon) -> str:
    """Return the WKT ``POINT`` for a WGS84 location given as latitude, longitude.

    Parameters
    ----------
    lat:
        Latitude in decimal degrees, within ``[-90, 90]``.
    lon:
        Longitude in decimal degrees, within ``[-180, 180]``.

    Returns
    -------
    str
        ``"POINT (<lon> <lat>)"`` -- note the deliberate reordering, since WKT
        stores easting/X before northing/Y.

    Raises
    ------
    TypeError
        If either argument is not a real number.
    ValueError
        If either argument is non-finite or outside its valid range.

    Examples
    --------
    >>> wkt_from_latlon(48.858296, 2.294479)  # Eiffel Tower
    'POINT (2.294479 48.858296)'
    >>> wkt_from_latlon(0, 0)
    'POINT (0 0)'
    >>> wkt_from_latlon(-33.8568, 151.2153)  # Sydney Opera House
    'POINT (151.2153 -33.8568)'
    """
    latitude = _as_float(lat, "lat")
    longitude = _as_float(lon, "lon")

    if not -_MAX_LATITUDE <= latitude <= _MAX_LATITUDE:
        raise ValueError(
            f"lat must be within [-90, 90] degrees, got {latitude!r} "
            "(arguments are (lat, lon) -- check they are not transposed)"
        )
    if not -_MAX_LONGITUDE <= longitude <= _MAX_LONGITUDE:
        raise ValueError(
            f"lon must be within [-180, 180] degrees, got {longitude!r}"
        )

    # X then Y: longitude first.
    return f"POINT ({_format_ordinate(longitude)} {_format_ordinate(latitude)})"
```