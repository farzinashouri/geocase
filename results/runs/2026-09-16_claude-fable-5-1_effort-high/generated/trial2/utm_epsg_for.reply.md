```python
"""WGS 84 / UTM EPSG code lookup using Military Grid Reference System zones.

The MGRS assigns longitude zones in 6-degree strips numbered 1..60 from
180 W eastwards, with two published exceptions:

* Zone 32V is widened to cover south-western Norway
  (56 N to 64 N, 3 E to 12 E), so zone 31 is narrowed there.
* In latitude band X (72 N to 84 N) around Svalbard, zones 32, 34 and 36
  are dropped and zones 31, 33, 35 and 37 are widened:
  31X = 0 E to 9 E, 33X = 9 E to 21 E, 35X = 21 E to 33 E, 37X = 33 E to 42 E.

The EPSG code of the matching UTM projection is 32600 + zone in the
northern hemisphere and 32700 + zone in the southern hemisphere.
"""

from __future__ import annotations

import math

__all__ = ["utm_epsg_for", "mgrs_zone_number"]

_UTM_MIN_LAT = -80.0
_UTM_MAX_LAT = 84.0


def _normalize_lon(lon: float) -> float:
    """Wrap longitude into the half-open interval [-180, 180)."""
    return ((lon + 180.0) % 360.0) - 180.0


def mgrs_zone_number(lon: float, lat: float) -> int:
    """Return the MGRS/UTM longitude zone number (1..60) for a location.

    Includes the Norway (32V) and Svalbard (31X/33X/35X/37X) exceptions.
    ``lon`` may be any finite longitude; it is wrapped into [-180, 180).
    """
    lon = _normalize_lon(float(lon))
    lat = float(lat)

    zone = int((lon + 180.0) // 6.0) + 1
    zone = min(max(zone, 1), 60)

    # Norway exception: band V (56-64 N), zone 32 widened to 3 E .. 12 E.
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        return 32

    # Svalbard exception: band X (72-84 N).
    if 72.0 <= lat <= 84.0 and 0.0 <= lon < 42.0:
        if lon < 9.0:
            return 31
        if lon < 21.0:
            return 33
        if lon < 33.0:
            return 35
        return 37

    return zone


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS containing ``(lon, lat)``.

    Parameters
    ----------
    lon : float
        WGS 84 longitude in decimal degrees (east positive).
    lat : float
        WGS 84 latitude in decimal degrees (north positive).

    Returns
    -------
    int
        ``326xx`` for the northern hemisphere (latitude >= 0) or ``327xx``
        for the southern hemisphere, where ``xx`` is the MGRS zone number.

    Raises
    ------
    ValueError
        If either coordinate is not a finite number, or if the latitude lies
        outside the UTM/MGRS grid-zone extent of 80 S to 84 N (those areas
        are covered by the polar stereographic UPS grid, not UTM).
    """
    try:
        lon_f = float(lon)
        lat_f = float(lat)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"lon/lat must be numeric, got {lon!r}, {lat!r}") from exc

    if not (math.isfinite(lon_f) and math.isfinite(lat_f)):
        raise ValueError(f"lon/lat must be finite, got {lon!r}, {lat!r}")

    if not (_UTM_MIN_LAT <= lat_f <= _UTM_MAX_LAT):
        raise ValueError(
            f"latitude {lat_f} is outside the UTM grid-zone extent "
            f"[{_UTM_MIN_LAT}, {_UTM_MAX_LAT}]; use UPS for polar regions"
        )

    zone = mgrs_zone_number(lon_f, lat_f)
    base = 32600 if lat_f >= 0.0 else 32700
    return base + zone
```