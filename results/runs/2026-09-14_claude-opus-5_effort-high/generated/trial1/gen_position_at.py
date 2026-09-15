"""Estimate a ship's position at an arbitrary time from sorted GPS fixes.

Positions are interpolated along the WGS84 geodesic connecting the two fixes
that bracket the requested time, at the distance fraction implied by elapsed
time (i.e. constant speed over the segment). Working in azimuth/distance space
rather than interpolating longitude and latitude componentwise means
antimeridian crossings and high-latitude segments are handled correctly: a
track running from 179.9E to 179.9W is a short hop east, not a near-circumnavigation
westward.

Importing this module performs no I/O and builds no global state; the geodesic
helper is created on first use and cached.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Sequence, Tuple

__all__ = ["position_at"]

Fix = Tuple[float, float, float]  # (timestamp, lon, lat)


@lru_cache(maxsize=1)
def _geod():
    """Return a cached WGS84 Geod. Built lazily so import stays side-effect free."""
    from pyproj import Geod

    return Geod(ellps="WGS84")


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    return (lon + 180.0) % 360.0 - 180.0


def _bracket(fixes: Sequence[Fix], t: float) -> int:
    """Index of the rightmost fix whose timestamp is <= t.

    Plain binary search rather than bisect(key=...) so the module works on
    Python releases before 3.10.
    """
    lo, hi = 0, len(fixes) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if fixes[mid][0] <= t:
            lo = mid
        else:
            hi = mid - 1
    return lo


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Estimate the ship's position at time ``t``.

    Args:
        fixes: Chronologically sorted ``(timestamp, lon, lat)`` fixes. Timestamps
            are Unix seconds; ``lon``/``lat`` are WGS84 degrees. Duplicate
            timestamps are permitted; the last fix at a given instant wins.
        t: Unix timestamp, within ``[fixes[0][0], fixes[-1][0]]``.

    Returns:
        ``(lon, lat)`` in WGS84 degrees, longitude wrapped into [-180, 180).

    Raises:
        ValueError: if ``fixes`` is empty or ``t`` falls outside the track's
            time span. Extrapolating a ship's position beyond its observed
            track is guesswork, so it is refused rather than silently clamped.
    """
    if not fixes:
        raise ValueError("fixes must contain at least one fix")

    t0_track, t1_track = fixes[0][0], fixes[-1][0]
    if not t0_track <= t <= t1_track:
        raise ValueError(
            f"t={t!r} is outside the track span [{t0_track!r}, {t1_track!r}]"
        )

    i = _bracket(fixes, t)

    # t lands on (or past, for trailing duplicate timestamps) the final fix.
    if i == len(fixes) - 1:
        _, lon, lat = fixes[-1]
        return (_normalize_lon(lon), lat)

    t_a, lon_a, lat_a = fixes[i]
    t_b, lon_b, lat_b = fixes[i + 1]

    # _bracket guarantees t_a <= t < t_b, so the span is strictly positive.
    frac = (t - t_a) / (t_b - t_a)
    if frac == 0.0:
        return (_normalize_lon(lon_a), lat_a)

    geod = _geod()
    az, _, dist = geod.inv(lon_a, lat_a, lon_b, lat_b)

    # Stationary segment (anchored, or repeated fix): azimuth is meaningless.
    if dist == 0.0:
        return (_normalize_lon(lon_a), lat_a)

    lon, lat, _ = geod.fwd(lon_a, lat_a, az, dist * frac)
    return (_normalize_lon(lon), lat)