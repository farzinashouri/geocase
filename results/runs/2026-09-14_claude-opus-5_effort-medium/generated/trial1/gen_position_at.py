"""Estimate a ship's position at an arbitrary time from sorted GPS fixes.

Positions are interpolated *along the geodesic* between the two bracketing
fixes on the WGS84 ellipsoid, not linearly in (lon, lat).  Linear interpolation
of coordinates is wrong everywhere except over very short east-west hops: it
cuts corners at high latitudes, breaks completely across the antimeridian
(interpolating +179 -> -179 sends the ship the long way around the world), and
misbehaves near the poles.  Geodesic interpolation is correct anywhere on the
ocean, including polar and antimeridian crossings.

Importing this module has no side effects; the pyproj Geod object is built on
first use and cached.
"""

from __future__ import annotations

from bisect import bisect_right
from typing import List, Sequence, Tuple

from pyproj import Geod

__all__ = ["position_at"]

_GEOD: Geod | None = None


def _geod() -> Geod:
    """Return a cached WGS84 Geod, constructed on first use."""
    global _GEOD
    if _GEOD is None:
        _GEOD = Geod(ellps="WGS84")
    return _GEOD


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180)."""
    return (lon + 180.0) % 360.0 - 180.0


def position_at(
    fixes: Sequence[Tuple[float, float, float]], t: float
) -> Tuple[float, float]:
    """Estimate the ship's position at time ``t``.

    Args:
        fixes: Chronologically sorted ``(timestamp, lon, lat)`` tuples.
            Timestamps are Unix seconds; ``lon``/``lat`` are WGS84 degrees.
        t: Unix timestamp, between the first and last fix (inclusive).

    Returns:
        ``(lon, lat)`` in WGS84 degrees, with longitude wrapped to [-180, 180).

    Raises:
        ValueError: If ``fixes`` is empty, not chronologically sorted, or if
            ``t`` lies outside the covered time span.
    """
    if not fixes:
        raise ValueError("fixes must contain at least one fix")

    times: List[float] = [float(f[0]) for f in fixes]
    for earlier, later in zip(times, times[1:]):
        if later < earlier:
            raise ValueError("fixes must be sorted by non-decreasing timestamp")

    t = float(t)
    if t < times[0] or t > times[-1]:
        raise ValueError(
            f"t={t!r} is outside the fix time span [{times[0]!r}, {times[-1]!r}]"
        )

    # Index of the last fix at or before t.  bisect_right lands past any run of
    # duplicate timestamps, so an exact hit on a repeated timestamp resolves to
    # the last fix carrying it -- and the endpoints fall out without a special
    # case.
    i = bisect_right(times, t) - 1
    if i < 0:
        i = 0
    if i >= len(times) - 1:
        # t is at (or numerically at) the final fix.
        _, lon, lat = fixes[-1]
        return (_normalize_lon(float(lon)), float(lat))

    t0, lon0, lat0 = (float(v) for v in fixes[i])
    t1, lon1, lat1 = (float(v) for v in fixes[i + 1])

    span = t1 - t0
    if span <= 0.0:
        # Duplicate timestamps: nothing to interpolate over.
        return (_normalize_lon(lon0), lat0)

    frac = (t - t0) / span
    if frac <= 0.0:
        return (_normalize_lon(lon0), lat0)
    if frac >= 1.0:
        return (_normalize_lon(lon1), lat1)

    g = _geod()
    azimuth, _back_azimuth, distance = g.inv(lon0, lat0, lon1, lat1)
    if distance == 0.0:
        # Stationary between the two fixes; azimuth is undefined.
        return (_normalize_lon(lon0), lat0)

    lon, lat, _ = g.fwd(lon0, lat0, azimuth, distance * frac)
    return (_normalize_lon(lon), lat)