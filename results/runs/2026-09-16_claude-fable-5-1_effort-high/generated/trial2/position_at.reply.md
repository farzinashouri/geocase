Here is the module. Interpolation is along the WGS84 geodesic between the two bracketing fixes, so it handles the antimeridian and polar regions correctly.

```python
"""Estimate a ship's position at a given time from a sorted list of GPS fixes.

Interpolation is performed along the WGS84 geodesic between the two fixes that
bracket the requested time, so results are correct across the antimeridian and
near the poles. Importing this module has no side effects; the geodesic
calculator is created lazily on first use.
"""

from bisect import bisect_right

from pyproj import Geod

_GEOD = None


def _geod():
    """Return a lazily constructed WGS84 Geod instance."""
    global _GEOD
    if _GEOD is None:
        _GEOD = Geod(ellps="WGS84")
    return _GEOD


def _normalize_lon(lon):
    """Wrap a longitude into the range [-180, 180)."""
    return (lon + 180.0) % 360.0 - 180.0


def position_at(fixes, t):
    """Return the estimated (lon, lat) of the ship at Unix time ``t``.

    ``fixes`` is a chronologically sorted list of ``(timestamp, lon, lat)``
    tuples in WGS84. ``t`` must lie between the first and last timestamp
    (inclusive). If ``t`` coincides with a fix, that fix's position is returned
    (the last one, if several fixes share the timestamp). Otherwise the position
    is interpolated along the geodesic between the bracketing fixes,
    proportionally to elapsed time.
    """
    if not fixes:
        raise ValueError("fixes must contain at least one fix")

    timestamps = [fix[0] for fix in fixes]
    if t < timestamps[0] or t > timestamps[-1]:
        raise ValueError(
            f"t={t} is outside the fix range [{timestamps[0]}, {timestamps[-1]}]"
        )

    # Index of the last fix whose timestamp is <= t.
    lo = bisect_right(timestamps, t) - 1
    t0, lon0, lat0 = fixes[lo]

    if t0 == t or lo == len(fixes) - 1:
        return (_normalize_lon(float(lon0)), float(lat0))

    t1, lon1, lat1 = fixes[lo + 1]
    if t1 == t0:
        # Degenerate segment; nothing to interpolate.
        return (_normalize_lon(float(lon0)), float(lat0))

    fraction = (t - t0) / (t1 - t0)

    geod = _geod()
    azimuth, _, distance = geod.inv(lon0, lat0, lon1, lat1)
    if distance == 0.0:
        return (_normalize_lon(float(lon0)), float(lat0))

    lon, lat, _ = geod.fwd(lon0, lat0, azimuth, distance * fraction)
    return (_normalize_lon(lon), lat)
```