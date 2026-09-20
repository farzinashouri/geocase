import bisect

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def position_at(fixes, t):
    """Estimate a ship's (lon, lat) position at time t via geodesic
    interpolation between the two bracketing GPS fixes."""
    if not fixes:
        raise ValueError("fixes must not be empty")

    timestamps = [f[0] for f in fixes]

    idx = bisect.bisect_left(timestamps, t)

    if idx < len(timestamps) and timestamps[idx] == t:
        _, lon, lat = fixes[idx]
        return (lon, lat)

    if idx <= 0 or idx >= len(fixes):
        raise ValueError("t must be between the first and last fix timestamps")

    t0, lon0, lat0 = fixes[idx - 1]
    t1, lon1, lat1 = fixes[idx]

    if t1 == t0:
        return (lon0, lat0)

    fraction = (t - t0) / (t1 - t0)

    az12, _, distance = _GEOD.inv(lon0, lat0, lon1, lat1)
    lon, lat, _ = _GEOD.fwd(lon0, lat0, az12, distance * fraction)

    return (lon, lat)