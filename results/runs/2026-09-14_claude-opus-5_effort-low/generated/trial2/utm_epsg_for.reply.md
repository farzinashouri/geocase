```python
"""WGS 84 / UTM EPSG lookup for a longitude/latitude, using MGRS grid zones.

MGRS zone numbering follows the standard 6-degree zones with the two published
exception areas: the widened zone 32 off south-west Norway, and the four
widened odd zones covering Svalbard.
"""

from __future__ import annotations

__all__ = ["utm_epsg_for"]


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    return (lon + 180.0) % 360.0 - 180.0


def _zone_number(lon: float, lat: float) -> int:
    """MGRS grid zone number for a normalized longitude and a latitude."""
    zone = int((lon + 180.0) // 6.0) + 1

    # South-west Norway: zone 32 is widened westward to 3 deg E, at the
    # expense of zone 31, for latitude band V (56 deg N to 64 deg N).
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        return 32

    # Svalbard: in latitude band X (72 deg N to 84 deg N) zone 32, 34 and 36
    # are absorbed by their widened odd-numbered neighbours.
    if 72.0 <= lat < 84.0 and 0.0 <= lon < 42.0:
        if lon < 9.0:
            return 31
        if lon < 21.0:
            return 33
        if lon < 33.0:
            return 35
        return 37

    return zone


def utm_epsg_for(lon: float, lat: float) -> int:
    """Return the EPSG code of the WGS 84 / UTM CRS containing (lon, lat).

    Args:
        lon: Longitude in degrees on WGS 84. Values outside [-180, 180) are
            wrapped.
        lat: Latitude in degrees on WGS 84, in [-90, 90].

    Returns:
        326xx for northern-hemisphere zones, 327xx for southern ones, where
        xx is the MGRS grid zone number.

    Raises:
        ValueError: If the coordinates are not finite or the latitude is out
            of range.
    """
    lon = float(lon)
    lat = float(lat)

    if lon != lon or lat != lat or lon in (float("inf"), float("-inf")) or lat in (
        float("inf"),
        float("-inf"),
    ):
        raise ValueError("lon and lat must be finite numbers")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude out of range: {lat}")

    lon = _normalize_lon(lon)
    zone = _zone_number(lon, lat)
    return (32600 if lat >= 0.0 else 32700) + zone
```