import numpy as np
import rasterio
from rasterio.transform import xy


def zonal_mean(raster_path, polygon):
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        nodata = src.nodata
        transform = src.transform

    rows, cols = np.indices(data.shape)
    xs, ys = xy(transform, rows.ravel(), cols.ravel())
    xs = np.asarray(xs)
    ys = np.asarray(ys)

    from shapely import vectorized

    inside = vectorized.contains(polygon, xs, ys).reshape(data.shape)

    if nodata is not None:
        valid = inside & (data != nodata)
    else:
        valid = inside

    if not np.any(valid):
        return None

    return float(data[valid].mean())