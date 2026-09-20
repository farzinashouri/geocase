```python
"""WGS 84 / UTM EPSG codes for Military Grid Reference System grid zones.

A point's UTM zone is normally just its 6-degree-wide longitude band, numbered
1-60 eastwards from the antimeridian.  MGRS keeps that numbering everywhere
except inside two published grid exceptions, both in the far north:

* Band V (56N-64N), south-west Norway: zone 31V is narrowed to 0E-3E and
  zone 32V is widened to 3E-12E, so that southern Norway stays in one zone.
* Band X (72N-84N), Svalbard: zones 32X, 34X and 36X do not exist.  Zone 31X
  covers 0E-9E, 33X covers 9E-21E, 35X covers 21E-33E and 37X covers 33E-42E.

Each zone has two CRSs -- EPSG:326nn north of the equator and EPSG:327nn south
of it -- which is what this module returns.

    >>> utm_epsg_for(-73.98, 40.75)   # New York City, zone 18N
    32618
    >>> utm_epsg_for(151.21, -33.87)  # Sydney, zone 56S
    32756
    >>> utm_epsg_for(4.5, 60.0)       # Norway exception: 32V, not 31V
    32632
    >>> utm_epsg_for(7.0, 78.0)       # Svalbard exception: 31X, not 32X
    32631

Zone and band edges are treated as belonging to the zone or band they open, so
a point at exactly 6E is in zone 32 and a point on the equator is northern.
Longitudes are wrapped into [-180, 180), which puts the antimeridian itself in
zone 1.  Latitudes beyond the MGRS band range (north of 84N or south of 80S)
lie in the polar UPS regions and so have no MGRS grid zone at all; they are
given their plain UTM zone, which is unambiguous because neither exception
reaches those latitudes.
"""

from __future__ import annotations

import math

__all__ = ["utm_epsg_for"]

_EPSG_NORTH_BASE = 32600
_EPSG_SOUTH_BASE = 32700

_ZONE_WIDTH_DEG = 6.0
_ZONE_COUNT = 60

# Band V, the south-west Norway exception.
_NORWAY_LAT_RANGE = (56.0, 64.0)
_NORWAY_LON_RANGE = (3.0, 12.0)
_NORWAY_ZONE = 32

# Band X, the Svalbard exception: (eastern edge of the zone, zone number).
_SVALBARD_LAT_RANGE = (72.0, 84.0)  # upper bound inclusive: band X ends UTM
_SVALBARD_ZONES = ((9.0, 31), (21.0, 33), (33.0, 35), (42.0, 37))


def _wrapped_lon(lon: float) -> float:
    """Wrap ``lon`` into [-180, 180); +180 maps onto -180, i.e. zone 1."""
    return (lon + 180.0) % 360.0 - 180.0


def _zone_number(lon: float, lat: float) -> int:
    """MGRS zone number for a wrapped longitude and an in-range latitude."""
    norway_lat_min, norway_lat_max = _NORWAY_LAT_RANGE
    norway_lon_min, norway_lon_max = _NORWAY_LON_RANGE
    if norway_lat_min <= lat < norway_lat_max and norway_lon_min <= lon < norway_lon_max:
        return _NORWAY_ZONE

    svalbard_lat_min, svalbard_lat_max = _SVALBARD_LAT_RANGE
    if svalbard_lat_min <= lat <= svalbard_lat_max and 0.0 <= lon < _SVALBARD_ZONES[-1][0]:
        for eastern_edge, zone in _SVALBARD_ZONES:
            if lon < eastern_edge:
                return zone

    return int((lon + 180.0) // _ZONE_WIDTH_DEG) % _ZONE_COUNT + 1


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS covering (``lon``, ``lat``).

    Args:
        lon: WGS84 longitude in degrees east.  Values outside [-180, 180) are
            wrapped, so 190 is read as -170.
        lat: WGS84 latitude in degrees north, within [-90, 90].

    Returns:
        32601-32660 for northern-hemisphere zones 1-60, or 32701-32760 for
        their southern-hemisphere counterparts.

    Raises:
        ValueError: if either coordinate is not finite, or ``lat`` lies outside
            [-90, 90].
    """
    lon = float(lon)
    lat = float(lat)
    if not math.isfinite(lon) or not math.isfinite(lat):
        raise ValueError(f"lon and lat must be finite, got ({lon!r}, {lat!r})")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must be within [-90, 90] degrees, got {lat!r}")

    base = _EPSG_NORTH_BASE if lat >= 0.0 else _EPSG_SOUTH_BASE
    return base + _zone_number(_wrapped_lon(lon), lat)
```