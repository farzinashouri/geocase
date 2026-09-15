```python
"""Build WKT ``POINT`` geometry from WGS84 latitude/longitude.

Axis-order note (the whole point of this module):

* Human/API convention — and the argument order here — is **(lat, lon)**.
* WKT is a *Cartesian* format: coordinates are written **X Y**, i.e.
  ``POINT (easting northing)``. For geographic CRSs that means
  ``POINT (lon lat)``.

So the function deliberately swaps its arguments on the way out. Emitting
``POINT (lat lon)`` is the classic bug: it parses fine, then silently plots
Zurich (47.37, 8.54) in the Indian Ocean off Somalia, and for any |lat| > 90
used as an X value it is not even a valid WGS84 position.

The output is plain WKT with no SRID prefix, which is what shapely,
``ogr2ogr``, PostGIS ``ST_GeomFromText``, GeoPandas and QGIS expect; pass
EPSG:4326 separately as the CRS.
"""

from __future__ import annotations

from decimal import Decimal
from math import isfinite

__all__ = ["wkt_from_latlon"]

_MAX_LAT = 90.0
_MAX_LON = 180.0


def _coerce(value: object, name: str) -> float:
    """Return *value* as a finite float, or raise ``TypeError``/``ValueError``."""
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a real number, not bool")
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real number, got {value!r}") from exc
    if not isfinite(number):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return number


def _format(value: float) -> str:
    """Format a coordinate for WKT: round-trippable, never in exponent form.

    ``repr`` gives the shortest string that round-trips to the same float, but
    for small magnitudes it produces ``1e-07``. Some WKT readers choke on
    exponent notation, so re-render that exact value as fixed point.
    """
    text = f"{Decimal(repr(value)):f}"
    return "-0" if text == "-0" else text


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return the WKT ``POINT`` for a WGS84 position given as (lat, lon).

    Parameters
    ----------
    lat:
        Latitude in decimal degrees, -90 to 90 inclusive.
    lon:
        Longitude in decimal degrees, -180 to 180 inclusive.

    Returns
    -------
    str
        ``"POINT (<lon> <lat>)"`` — X first, per the WKT specification.

    Raises
    ------
    TypeError
        If either argument is not a real number.
    ValueError
        If either argument is non-finite or outside its valid range.

    Examples
    --------
    >>> wkt_from_latlon(47.3769, 8.5417)  # Zurich
    'POINT (8.5417 47.3769)'
    >>> wkt_from_latlon(-33.8688, 151.2093)  # Sydney
    'POINT (151.2093 -33.8688)'
    >>> wkt_from_latlon(0, 0)
    'POINT (0 0)'
    """
    latitude = _coerce(lat, "lat")
    longitude = _coerce(lon, "lon")

    if not -_MAX_LAT <= latitude <= _MAX_LAT:
        raise ValueError(
            f"lat must be between -90 and 90 degrees, got {latitude!r} "
            "(arguments are (lat, lon); check you did not swap them)"
        )
    if not -_MAX_LON <= longitude <= _MAX_LON:
        raise ValueError(
            f"lon must be between -180 and 180 degrees, got {longitude!r}"
        )

    return f"POINT ({_format(longitude)} {_format(latitude)})"
```