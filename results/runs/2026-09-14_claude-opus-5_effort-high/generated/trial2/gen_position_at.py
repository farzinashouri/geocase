"""Estimate a ship's position between GPS fixes.

Positions are interpolated along the WGS84 geodesic connecting the two
bracketing fixes, at a distance proportional to elapsed time.  Linear
interpolation of longitude/latitude is deliberately avoided: it is wrong at
high latitudes, breaks across the antimeridian, and does not follow the path a
vessel actually takes.  Working in geodesic (azimuth, distance) space instead
is correct anywhere on the globe, including across the dateline and near the
poles, and costs nothing extra.

Importing this module has no side effects beyond importing pyproj and
constructing a stateless ``Geod`` object.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from operator import itemgetter
from typing import Sequence, Tuple

from pyproj import Geod

__all__ = ["position_at"]

# Stateless, thread-safe, cheap to construct; shared to avoid per-call setup.
_GEOD = Geod(ellps="WGS84")

_timestamp = itemgetter(0)

Fix = Tuple[float, float, float]


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Return the estimated ``(lon, lat)`` of the ship at time ``t``.

    Args:
        fixes: Chronologically sorted ``(timestamp, lon, lat)`` fixes.
            Timestamps are Unix seconds; positions are WGS84 degrees.
            Duplicate timestamps are tolerated (the last one wins).
        t: Unix timestamp, at or between the first and last fix.

    Returns:
        ``(lon, lat)`` in degrees, with longitude normalized to [-180, 180).

    Raises:
        ValueError: if ``fixes`` is empty, ``t`` is not finite, or ``t`` falls
            outside the time span covered by ``fixes``.

    Note:
        Each pair of consecutive fixes is assumed to be joined by the *shorter*
        geodesic between them, which is the right assumption for realistic fix
        intervals.  It would be wrong for a pair of fixes more than half the
        globe apart, where the true track is ambiguous anyway.
    """
    if not fixes:
        raise ValueError("fixes must contain at least one fix")

    t = float(t)
    if not math.isfinite(t):
        raise ValueError("t must be a finite timestamp")

    t_first = float(_timestamp(fixes[0]))
    t_last = float(_timestamp(fixes[-1]))
    if not (t_first <= t <= t_last):
        raise ValueError(
            f"t={t!r} is outside the fix time span [{t_first!r}, {t_last!r}]"
        )

    # First index whose timestamp is strictly greater than t.
    i = bisect_right(fixes, t, key=_timestamp)

    if i == 0:  # t == t_first (and the first fix is not a duplicate).
        return _clean(fixes[0][1], fixes[0][2])
    if i == len(fixes):  # t == t_last; nothing to interpolate towards.
        return _clean(fixes[-1][1], fixes[-1][2])

    t0, lon0, lat0 = float(fixes[i - 1][0]), float(fixes[i - 1][1]), float(fixes[i - 1][2])
    t1, lon1, lat1 = float(fixes[i][0]), float(fixes[i][1]), float(fixes[i][2])

    dt = t1 - t0
    if dt <= 0.0:  # Defensive: unsorted or duplicated timestamps.
        return _clean(lon0, lat0)

    fraction = (t - t0) / dt
    if fraction <= 0.0:
        return _clean(lon0, lat0)

    # Geodesic azimuth and distance, then walk the matching fraction of it.
    azimuth, _, distance = _GEOD.inv(lon0, lat0, lon1, lat1)
    if not distance:  # Ship is stationary between these two fixes.
        return _clean(lon0, lat0)

    lon, lat, _ = _GEOD.fwd(lon0, lat0, azimuth, distance * fraction)
    return _clean(lon, lat)


def _clean(lon: float, lat: float) -> Tuple[float, float]:
    """Normalize longitude to [-180, 180) and validate the coordinate pair."""
    lon = float(lon)
    lat = float(lat)
    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise ValueError(f"non-finite position: ({lon!r}, {lat!r})")
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"latitude out of range: {lat!r}")
    return (lon + 180.0) % 360.0 - 180.0, lat