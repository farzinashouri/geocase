"""Zonal mean of raster pixel values whose centres fall inside a polygon."""

import numpy as np
import rasterio
import shapely


def zonal_mean(raster_path, polygon):
    with rasterio.open(raster_path) as src:
        band = src.read(1)
        nodata = src.nodata
        transform = src.transform

    rows, cols = np.indices(band.shape)
    a, b, c, d, e, f = transform[:6]
    col_centers = cols + 0.5
    row_centers = rows + 0.5
    xs = a * col_centers + b * row_centers + c
    ys = d * col_centers + e * row_centers + f

    inside = shapely.contains_xy(polygon, xs, ys)

    if nodata is not None:
        inside &= band != nodata

    values = band[inside]
    if values.size == 0:
        return None

    return float(values.mean())