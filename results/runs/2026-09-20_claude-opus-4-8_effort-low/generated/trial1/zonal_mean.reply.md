```python
"""Zonal statistics for a single-band raster over a shapely polygon."""

import numpy as np
import rasterio
from rasterio.transform import xy


def zonal_mean(raster_path, polygon):
    """Return the mean of pixel values whose centres fall inside ``polygon``.

    The polygon is expressed in the raster's own CRS. Pixels equal to the
    raster's nodata value are excluded. Returns ``None`` if no valid pixel
    centre lies inside the polygon.
    """
    from shapely.prepared import prep
    from shapely.geometry import box, Point

    with rasterio.open(raster_path) as src:
        band = src.read(1)
        transform = src.transform
        nodata = src.nodata

        # Restrict work to the window covering the polygon's bounds.
        minx, miny, maxx, maxy = polygon.bounds
        rows, cols = band.shape

        # Compute the pixel index range whose centres could fall in the bounds.
        # Invert the affine transform to map bounds corners to pixel space.
        inv = ~transform
        cand = []
        for px, py in ((minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy)):
            c, r = inv * (px, py)
            cand.append((r, c))
        rs = [rc[0] for rc in cand]
        cs = [rc[1] for rc in cand]
        r0 = max(0, int(np.floor(min(rs))) - 1)
        r1 = min(rows, int(np.ceil(max(rs))) + 1)
        c0 = max(0, int(np.floor(min(cs))) - 1)
        c1 = min(cols, int(np.ceil(max(cs))) + 1)

        if r0 >= r1 or c0 >= c1:
            return None

        prepared = prep(polygon)
        total = 0.0
        count = 0

        for row in range(r0, r1):
            for col in range(c0, c1):
                value = band[row, col]
                if nodata is not None and value == nodata:
                    continue
                if np.isnan(value):
                    continue
                x, y = xy(transform, row, col, offset="center")
                if prepared.contains(Point(x, y)):
                    total += float(value)
                    count += 1

    if count == 0:
        return None
    return total / count
```