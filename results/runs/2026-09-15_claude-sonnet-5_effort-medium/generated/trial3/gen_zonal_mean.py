import numpy as np
import rasterio
from rasterio.transform import xy
from shapely.geometry import Point


def zonal_mean(raster_path, polygon):
    with rasterio.open(raster_path) as src:
        band = src.read(1)
        nodata = src.nodata
        transform = src.transform

    minx, miny, maxx, maxy = polygon.bounds
    inv_transform = ~transform

    col_min, row_min = inv_transform * (minx, maxy)
    col_max, row_max = inv_transform * (maxx, miny)

    row_start = max(int(np.floor(min(row_min, row_max))) - 1, 0)
    row_end = min(int(np.ceil(max(row_min, row_max))) + 1, band.shape[0])
    col_start = max(int(np.floor(min(col_min, col_max))) - 1, 0)
    col_end = min(int(np.ceil(max(col_min, col_max))) + 1, band.shape[1])

    values = []
    for row in range(row_start, row_end):
        for col in range(col_start, col_end):
            value = band[row, col]
            if nodata is not None and value == nodata:
                continue
            x, y = xy(transform, row, col)
            if polygon.contains(Point(x, y)):
                values.append(float(value))

    if not values:
        return None

    return float(np.mean(values))