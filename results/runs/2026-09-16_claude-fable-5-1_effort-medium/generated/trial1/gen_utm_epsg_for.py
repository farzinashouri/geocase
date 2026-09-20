"""UTM EPSG code lookup following Military Grid Reference System zone rules.

Provides :func:`utm_epsg_for`, which maps a WGS84 longitude/latitude to the
EPSG code of the matching "WGS 84 / UTM zone NNx" coordinate reference system.
Zone assignment follows the MGRS convention, including the two published grid
exceptions (southern Norway in zone 32V and the Svalbard zones 31X, 33X, 35X,
37X). Locations poleward of 84 N or 80 S fall in the MGRS Universal Polar
Stereographic area, which has no UTM zone, so they raise ``ValueError``.

Importing this module has no side effects.
"""

from __future__ import annotations

import math

__all__ = ["utm_epsg_for"]

_UTM_MIN_LAT = -80.0
_UTM_MAX_LAT = 84.0
_EPSG_NORTH_BASE = 32600
_EPSG_SOUTH_BASE = 32700


def _normalize_longitude(lon: float) -> float:
    """Wrap a longitude into the half-open interval [-180, 180)."""
    wrapped = (lon + 180.0) % 360.0 - 180.0
    # Python's modulo keeps the result in [0, 360), so wrapped is in [-180, 180).
    return wrapped


def _mgrs_zone_number(lon: float, lat: float) -> int:
    """Return the MGRS/UTM grid zone number (1..60) for a location.

    ``lon`` must already be normalised to [-180, 180) and ``lat`` must lie in
    the UTM latitude range [-80, 84].
    """
    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    zone = min(max(zone, 1), 60)

    # Exception 1: latitude band V (56 N to 64 N). Zone 32 is widened to cover
    # 3 E to 12 E so that all of southern Norway sits in one zone; zone 31 is
    # correspondingly narrowed to 0 E to 3 E.
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        return 32

    # Exception 2: latitude band X (72 N to 84 N) around Svalbard. Zones 32,
    # 34 and 36 are removed and their width is absorbed by 31, 33, 35 and 37.
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
    """Return the EPSG code of the WGS 84 / UTM CRS for the MGRS grid zone at (lon, lat).

    Parameters
    ----------
    lon:
        WGS84 longitude in decimal degrees. Any finite value is accepted and is
        wrapped into [-180, 180); 180 E is treated as 180 W (zone 1 is on the
        west side of the antimeridian, zone 60 on the east).
    lat:
        WGS84 latitude in decimal degrees, in [-90, 90].

    Returns
    -------
    int
        ``326NN`` for the northern hemisphere (lat >= 0) or ``327NN`` for the
        southern hemisphere (lat < 0), where ``NN`` is the two-digit zone.

    Raises
    ------
    TypeError
        If ``lon`` or ``lat`` is not a real number.
    ValueError
        If either coordinate is NaN or infinite, if ``lat`` is outside
        [-90, 90], or if the location lies in the MGRS polar (UPS) regions
        north of 84 N or south of 80 S, which have no UTM zone.
    """
    if isinstance(lon, bool) or isinstance(lat, bool):
        raise TypeError("lon and lat must be real numbers, not bool")
    try:
        lon_f = float(lon)
        lat_f = float(lat)
    except (TypeError, ValueError) as exc:
        raise TypeError("lon and lat must be real numbers") from exc

    if not (math.isfinite(lon_f) and math.isfinite(lat_f)):
        raise ValueError("lon and lat must be finite")
    if not (-90.0 <= lat_f <= 90.0):
        raise ValueError(f"latitude {lat_f!r} is outside [-90, 90]")
    if lat_f > _UTM_MAX_LAT or lat_f < _UTM_MIN_LAT:
        raise ValueError(
            f"latitude {lat_f!r} lies in the MGRS polar (UPS) region; "
            "no UTM zone exists between 84 N and the North Pole or "
            "between 80 S and the South Pole"
        )

    lon_n = _normalize_longitude(lon_f)
    zone = _mgrs_zone_number(lon_n, lat_f)
    base = _EPSG_NORTH_BASE if lat_f >= 0.0 else _EPSG_SOUTH_BASE
    return base + zone