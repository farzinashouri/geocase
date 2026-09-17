"""Estimate a ship's position at an arbitrary time from a track of GPS fixes.

The position between two consecutive fixes is interpolated along the WGS84
geodesic joining them (pyproj's ``Geod``): the fraction of the geodesic
travelled equals the fraction of the time interval elapsed. Interpolating on
the ellipsoid rather than in raw lon/lat space keeps the answer correct across
the antimeridian (e.g. 179.9E -> 179.9W) and near the poles, where straight
lon/lat interpolation is wrong.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Sequence, Tuple

from pyproj import Geod

__all__ = ["position_at"]

Fix = Tuple[float, float, float]  # (timestamp, lon, lat)


@lru_cache(maxsize=None)
def _wgs84() -> Geod:
    # Built lazily so importing the module does no work.
    return Geod(ellps="WGS84")


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180]."""
    return (float(lon) + 180.0) % 360.0 - 180.0


def _first_index_at_or_after(fixes: Sequence[Fix], t: float) -> int:
    """Binary search: smallest ``i`` such that ``fixes[i][0] >= t``."""
    lo, hi = 0, len(fixes)
    while lo < hi:
        mid = (lo + hi) // 2
        if fixes[mid][0] < t:
            lo = mid + 1
        else:
            hi = mid
    return lo


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Return the ship's estimated ``(lon, lat)`` at Unix time ``t``.

    Parameters
    ----------
    fixes
        Chronologically sorted sequence of ``(timestamp, lon, lat)`` fixes.
        Timestamps are Unix seconds; positions are WGS84 degrees.
    t
        Timestamp to query. Must lie within ``[fixes[0][0], fixes[-1][0]]``.

    Raises
    ------
    ValueError
        If ``fixes`` is empty or ``t`` is outside the track's time span.
    """
    if len(fixes) == 0:
        raise ValueError("fixes must contain at least one fix")

    t_first, t_last = fixes[0][0], fixes[-1][0]
    if not (t_first <= t <= t_last):
        raise ValueError(
            f"t={t!r} is outside the track's time span [{t_first!r}, {t_last!r}]"
        )

    i = _first_index_at_or_after(fixes, t)
    ts, lon, lat = fixes[i]
    if ts == t:
        return (_normalize_lon(lon), float(lat))

    # Here fixes[i-1][0] < t < fixes[i][0], so i >= 1 and the gap is non-zero.
    t_a, lon_a, lat_a = fixes[i - 1]
    t_b, lon_b, lat_b = fixes[i]
    frac = (t - t_a) / (t_b - t_a)

    geod = _wgs84()
    azimuth, _, dist = geod.inv(lon_a, lat_a, lon_b, lat_b)
    if dist == 0.0:
        # Ship did not move between the two fixes.
        return (_normalize_lon(lon_a), float(lat_a))

    lon_t, lat_t, _ = geod.fwd(lon_a, lat_a, azimuth, dist * frac)
    return (_normalize_lon(lon_t), float(lat_t))