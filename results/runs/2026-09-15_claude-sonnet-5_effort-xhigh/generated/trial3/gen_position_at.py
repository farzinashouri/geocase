"""Interpolate a ship's position between chronologically sorted GPS fixes."""
from bisect import bisect_right

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def position_at(fixes, t):
    """Estimate (lon, lat) at time t by geodesic interpolation between the
    two fixes bracketing t, assuming constant speed along the geodesic."""
    if len(fixes) == 1:
        _, lon, lat = fixes[0]
        return (lon, lat)

    timestamps = [f[0] for f in fixes]
    idx = bisect_right(timestamps, t) - 1
    idx = max(0, min(idx, len(fixes) - 2))

    t0, lon0, lat0 = fixes[idx]
    t1, lon1, lat1 = fixes[idx + 1]

    if t1 == t0:
        return (lon0, lat0)

    frac = (t - t0) / (t1 - t0)
    frac = min(1.0, max(0.0, frac))

    az12, _, dist = _GEOD.inv(lon0, lat0, lon1, lat1)
    if dist == 0.0:
        return (lon0, lat0)

    lon, lat, _ = _GEOD.fwd(lon0, lat0, az12, dist * frac)
    return (lon, lat)