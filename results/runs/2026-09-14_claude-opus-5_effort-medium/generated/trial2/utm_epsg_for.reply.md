```python
"""Map a WGS84 (longitude, latitude) position to the EPSG code of its
WGS 84 / UTM coordinate reference system.

Grid zones follow the Military Grid Reference System, which includes the two
published zone-numbering exceptions:

* South-west Norway (band 32V): zone 32 is widened westwards to 3 deg E, at
  the expense of zone 31.
* Svalbard (band X): zones 32, 34 and 36 are not used; zones 31, 33, 35 and
  37 are widened to cover 0-9, 9-21, 21-33 and 33-42 deg E respectively.

The only public name is :func:`utm_epsg_for`.  Importing this module has no
side effects.
"""

from __future__ import annotations

__all__ = ["utm_epsg_for"]

# Latitude limits of the UTM grid-zone system (MGRS bands C through X).
_MIN_LAT = -80.0
_MAX_LAT = 84.0

# Western edges of the widened Svalbard zones, paired with their zone numbers.
_SVALBARD = ((0.0, 31), (9.0, 33), (21.0, 35), (33.0, 37))
_SVALBARD_EAST = 42.0


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    lon = (lon + 180.0) % 360.0 - 180.0
    # ``%`` on a tiny negative input can round up to exactly 360.0.
    if lon >= 180.0:
        lon -= 360.0
    return lon


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM zone containing ``(lon, lat)``.

    Parameters
    ----------
    lon, lat:
        Longitude and latitude in degrees on WGS 84.  Longitude is wrapped
        into [-180, 180); latitude must lie within the UTM grid, i.e. between
        80 deg S and 84 deg N inclusive.

    Returns
    -------
    int
        ``326zz`` for northern-hemisphere zones and ``327zz`` for southern
        ones, where ``zz`` is the MGRS grid-zone number.

    Raises
    ------
    ValueError
        If either coordinate is not finite, or the latitude falls outside the
        area covered by UTM (the polar regions use UPS instead).
    """
    lon = float(lon)
    lat = float(lat)

    if lon != lon or lon in (float("inf"), float("-inf")):
        raise ValueError(f"longitude must be a finite number, got {lon!r}")
    if lat != lat or lat in (float("inf"), float("-inf")):
        raise ValueError(f"latitude must be a finite number, got {lat!r}")
    if not (_MIN_LAT <= lat <= _MAX_LAT):
        raise ValueError(
            f"latitude {lat!r} is outside the UTM grid "
            f"({_MIN_LAT} to {_MAX_LAT} degrees); use a polar (UPS) CRS"
        )

    lon = _normalize_lon(lon)

    zone = int((lon + 180.0) // 6.0) + 1
    if zone > 60:  # only reachable through floating-point edge cases
        zone = 60
    elif zone < 1:
        zone = 1

    # Exception 1: south-west Norway, band 32V.
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone = 32

    # Exception 2: Svalbard, band X (which tops out at 84 deg N).
    elif 72.0 <= lat <= _MAX_LAT and 0.0 <= lon < _SVALBARD_EAST:
        for west_edge, svalbard_zone in _SVALBARD:
            if lon >= west_edge:
                zone = svalbard_zone

    return (32600 if lat >= 0.0 else 32700) + zone
```