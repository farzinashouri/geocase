"""Interpolate a ship's position from a sequence of GPS fixes."""

from bisect import bisect_left
from typing import Sequence, Tuple

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def position_at(
    fixes: Sequence[Tuple[float, float, float]], t: float
) -> Tuple[float, float]:
    """Estimate (lon, lat) at time t.

    Finds the two fixes bracketing t and interpolates along the geodesic
    (great-circle path on the WGS84 ellipsoid) between them, assuming
    constant speed. This stays accurate across the antimeridian and near
    the poles, unlike naive linear interpolation of raw lon/lat values.
    """
    timestamps = [f[0] for f in fixes]
    i = bisect_left(timestamps, t)

    if i < len(timestamps) and timestamps[i] == t:
        _, lon, lat = fixes[i]
        return (lon, lat)

    t0, lon0, lat0 = fixes[i - 1]
    t1, lon1, lat1 = fixes[i]

    if t1 == t0:
        return (lon0, lat0)

    fraction = (t - t0) / (t1 - t0)

    az12, _, distance = _GEOD.inv(lon0, lat0, lon1, lat1)
    lon, lat, _ = _GEOD.fwd(lon0, lat0, az12, distance * fraction)
    return (lon, lat)