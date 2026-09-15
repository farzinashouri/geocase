"""WGS 84 / UTM EPSG lookup for MGRS grid zones.

``utm_epsg_for(lon, lat)`` maps a WGS 84 geographic coordinate to the EPSG code
of the UTM projected CRS that covers it: ``326xx`` in the northern hemisphere
and ``327xx`` in the southern, where ``xx`` is the grid zone number.

Zone numbers follow the Military Grid Reference System, so both published sets
of irregular zones are honoured:

* Band V (56N-64N): zone 31 is narrowed to 0E-3E and zone 32 is widened to
  3E-12E, keeping south-western Norway in a single zone.
* Band X (72N-84N): zones 32, 34 and 36 are not used; zones 31, 33, 35 and 37
  are widened to span 0E-9E, 9E-21E, 21E-33E and 33E-42E respectively, keeping
  each of the Svalbard islands in a single zone.

Zone bounds are half-open in longitude -- a point exactly on a meridian belongs
to the zone east of it -- and latitude bands are half-open going north, except
that band X is closed at its 84N top edge, the northern limit of UTM.

MGRS grid zones, and UTM with them, stop at 84N and 80S; the poles are covered
by Universal Polar Stereographic instead, so latitudes beyond those limits have
no UTM zone and raise ``ValueError``.
"""

from __future__ import annotations

import math

__all__ = ["utm_epsg_for"]

_NORTH_BASE = 32600
_SOUTH_BASE = 32700

_ZONE_WIDTH = 6.0
_MAX_ZONE = 60

# Latitude extent of the MGRS grid zones (bands C..X), i.e. of UTM itself.
_MIN_LAT = -80.0
_MAX_LAT = 84.0

# Band V, the Norway exception: (west edge, east edge, zone number).
_BAND_V_MIN_LAT = 56.0
_BAND_V_MAX_LAT = 64.0
_BAND_V_EXCEPTIONS = ((3.0, 12.0, 32),)

# Band X, the Svalbard exception. Zones 32, 34 and 36 are absent, their space
# taken by the widened odd zones below.
_BAND_X_MIN_LAT = 72.0
_BAND_X_EXCEPTIONS = (
    (0.0, 9.0, 31),
    (9.0, 21.0, 33),
    (21.0, 33.0, 35),
    (33.0, 42.0, 37),
)


def _as_finite_float(value: object, name: str) -> float:
    """Coerce ``value`` to a finite ``float`` or raise."""
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise TypeError(f"{name} must be a real number, got {value!r}") from None
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return result


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into ``[-180, 180)``."""
    wrapped = (lon + 180.0) % 360.0 - 180.0
    # Longitudes a hair west of -180 can round up to exactly 180.0 here.
    return -180.0 if wrapped >= 180.0 else wrapped


def _zone_number(lon: float, lat: float) -> int:
    """Return the MGRS grid zone number for an already-validated position.

    ``lon`` must be normalized to ``[-180, 180)`` and ``lat`` must lie within
    the grid-zone extent.
    """
    if _BAND_V_MIN_LAT <= lat < _BAND_V_MAX_LAT:
        exceptions = _BAND_V_EXCEPTIONS
    elif lat >= _BAND_X_MIN_LAT:
        exceptions = _BAND_X_EXCEPTIONS
    else:
        exceptions = ()

    for west, east, zone in exceptions:
        if west <= lon < east:
            return zone

    zone = int((lon + 180.0) // _ZONE_WIDTH) + 1
    # Guards the 180th meridian against floating-point drift.
    return min(zone, _MAX_ZONE)


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS covering ``(lon, lat)``.

    Parameters
    ----------
    lon:
        WGS 84 longitude in degrees east. Values outside ``[-180, 180)`` are
        wrapped.
    lat:
        WGS 84 latitude in degrees north, within the UTM extent ``[-80, 84]``.

    Returns
    -------
    int
        ``32600 + zone`` for ``lat >= 0`` and ``32700 + zone`` otherwise, with
        ``zone`` the MGRS grid zone number including the Norway and Svalbard
        exceptions.

    Raises
    ------
    TypeError
        If either coordinate is not a real number.
    ValueError
        If either coordinate is non-finite, if ``lat`` is not a latitude, or if
        ``lat`` is polar and therefore outside every UTM grid zone.

    Examples
    --------
    >>> utm_epsg_for(-73.98, 40.75)      # New York City
    32618
    >>> utm_epsg_for(151.21, -33.86)     # Sydney
    32756
    >>> utm_epsg_for(5.32, 60.39)        # Bergen, widened zone 32V
    32632
    >>> utm_epsg_for(15.65, 78.22)       # Longyearbyen, widened zone 33X
    32633
    """
    lon = _as_finite_float(lon, "lon")
    lat = _as_finite_float(lat, "lat")

    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must lie in [-90, 90], got {lat!r}")
    if not _MIN_LAT <= lat <= _MAX_LAT:
        raise ValueError(
            f"lat {lat!r} is outside the UTM grid-zone extent "
            f"[{_MIN_LAT}, {_MAX_LAT}]; polar locations are covered by UPS "
            "(EPSG:32661 north, EPSG:32761 south), not by a UTM zone"
        )

    zone = _zone_number(_normalize_lon(lon), lat)
    base = _NORTH_BASE if lat >= 0.0 else _SOUTH_BASE
    return base + zone