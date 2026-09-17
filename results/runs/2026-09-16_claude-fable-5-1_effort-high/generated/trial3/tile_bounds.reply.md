Writing a pure-stdlib module: TMS rows count from the south, so row `y` maps to Mercator span `[-π + 2πy/n, -π + 2π(y+1)/n]`, which I invert with `atan(sinh(·))` for latitude.

```python
"""Geographic bounds of a Web Mercator tile addressed with the TMS scheme.

The TMS tiling scheme (OSGeo Tile Map Service) numbers columns from west to
east and rows from *south to north*, i.e. row 0 is the bottom row.  This is
the vertical flip of the "XYZ"/Slippy-map convention used by OSM and Google,
where row 0 is the top row.  Converting between the two is
``y_xyz = 2**z - 1 - y_tms``.

The tile grid is the standard Web Mercator (EPSG:3857) square grid covering
longitudes -180..180 and latitudes roughly -85.0511..85.0511 degrees.
"""

from __future__ import annotations

import math
from typing import Tuple

__all__ = ["tile_bounds"]


def _mercator_y_to_lat(mercator_y: float) -> float:
    """Inverse spherical Mercator: normalised y in [-pi, pi] -> latitude (deg)."""
    return math.degrees(math.atan(math.sinh(mercator_y)))


def tile_bounds(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
    """Return ``(west, south, east, north)`` in WGS84 degrees for a TMS tile.

    Parameters
    ----------
    z : int
        Zoom level (>= 0).  There are ``2**z`` tiles along each axis.
    x : int
        Tile column, 0 at the western edge (-180 deg), increasing eastward.
    y : int
        Tile row in the TMS convention, 0 at the *southern* edge, increasing
        northward.

    Returns
    -------
    tuple of four floats
        ``(west, south, east, north)``.

    Raises
    ------
    TypeError
        If any argument is not an integer.
    ValueError
        If ``z`` is negative or ``x``/``y`` fall outside ``0 <= v < 2**z``.

    Examples
    --------
    >>> tile_bounds(0, 0, 0)
    (-180.0, -85.0511287798066, 180.0, 85.0511287798066)
    >>> tile_bounds(1, 0, 0)          # south-west quadrant under TMS
    (-180.0, -85.0511287798066, 0.0, 0.0)
    """
    # Accept numpy / other integral types but reject bools and floats such as
    # 1.0, whose fractional-tile semantics are undefined here.
    for name, value in (("z", z), ("x", x), ("y", y)):
        if isinstance(value, bool) or not isinstance(value, (int,)) and not (
            hasattr(value, "__index__")
        ):
            raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
    z = int(z)
    x = int(x)
    y = int(y)

    if z < 0:
        raise ValueError(f"zoom must be >= 0, got {z}")
    n = 1 << z  # number of tiles along each axis at this zoom
    if not 0 <= x < n:
        raise ValueError(f"x must satisfy 0 <= x < {n} at zoom {z}, got {x}")
    if not 0 <= y < n:
        raise ValueError(f"y must satisfy 0 <= y < {n} at zoom {z}, got {y}")

    # Longitude is linear in x.
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0

    # Latitude: TMS row y spans normalised Mercator y from
    # -pi + 2*pi*y/n (south edge) to -pi + 2*pi*(y+1)/n (north edge).
    south = _mercator_y_to_lat(-math.pi + 2.0 * math.pi * y / n)
    north = _mercator_y_to_lat(-math.pi + 2.0 * math.pi * (y + 1) / n)

    # Pin the outer edges exactly so callers get clean world bounds and the
    # equator/antimeridian are not perturbed by floating-point noise.
    if x == 0:
        west = -180.0
    if x + 1 == n:
        east = 180.0
    if 2 * y == n:
        south = 0.0
    if 2 * (y + 1) == n:
        north = 0.0

    return (float(west), float(south), float(east), float(north))
```