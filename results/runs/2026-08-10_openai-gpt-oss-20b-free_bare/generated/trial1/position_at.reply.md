```python
"""
gps_interpolator.py

A small self‑contained module that provides a single function
`position_at(fixes, t)` for estimating a ship's position at an
arbitrary timestamp between two GPS fixes.

The function uses great‑circle interpolation on the WGS84 ellipsoid
via `pyproj.Geod`.  It is accurate anywhere on the ocean and
requires only the standard library and the `pyproj` package.

Author: OpenAI ChatGPT
"""

from __future__ import annotations

from typing import Iterable, Tuple

from pyproj import Geod

__all__ = ["position_at"]


def position_at(
    fixes: Iterable[Tuple[int, float, float]], t: int
) -> Tuple[float, float]:
    """
    Estimate the ship's position at time ``t`` by interpolating
    between the two GPS fixes that bound ``t``.

    Parameters
    ----------
    fixes : Iterable[Tuple[int, float, float]]
        A chronologically sorted iterable of GPS fixes.
        Each fix is a tuple ``(timestamp, lon, lat)`` where
        *timestamp* is a Unix epoch integer (seconds),
        *lon* and *lat* are in decimal degrees (WGS84).
    t : int
        Unix timestamp (seconds) between the first and last fix.

    Returns
    -------
    Tuple[float, float]
        Estimated longitude and latitude at time ``t`` in decimal degrees.

    Raises
    ------
    ValueError
        If ``t`` is outside the range of the provided fixes,
        or if the input data is insufficient for interpolation.
    """
    # Convert to a list to allow indexing
    fix_list = list(fixes)

    if len(fix_list) < 2:
        raise ValueError("At least two GPS fixes are required for interpolation.")

    # Ensure the list is sorted by timestamp
    if any(fix_list[i][0] > fix_list[i + 1][0] for i in range(len(fix_list) - 1)):
        raise ValueError("GPS fixes must be sorted chronologically by timestamp.")

    t0, lon0, lat0 = fix_list[0]
    t_last, lon_last, lat_last = fix_list[-1]

    if not (t0 <= t <= t_last):
        raise ValueError("Timestamp t is outside the range of the GPS fixes.")

    # If t matches an existing fix, return it directly
    for ts, lon, lat in fix_list:
        if ts == t:
            return lon, lat

    # Find the interval containing t
    for i in range(len(fix_list) - 1):
        ts0, lon0, lat0 = fix_list[i]
        ts1, lon1, lat1 = fix_list[i + 1]
        if ts0 <= t <= ts1:
            # Fraction of the way between the two fixes
            frac = (t - ts0) / (ts1 - ts0)

            # Geodesic interpolation on WGS84 ellipsoid
            geod = Geod(ellps="WGS84")
            az12, az21, dist = geod.inv(lon0, lat0, lon1, lat1)
            interp_dist = dist * frac
            lon_interp, lat_interp, _ = geod.fwd(lon0, lat0, az12, interp_dist)
            return lon_interp, lat_interp

    # Should never reach here
    raise RuntimeError("Failed to interpolate position.")
```