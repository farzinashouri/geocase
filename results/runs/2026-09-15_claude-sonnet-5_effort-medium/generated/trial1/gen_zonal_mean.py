import numpy as np
import rasterio
from rasterio.transform import xy
from shapely.geometry import Point


def zonal_mean(raster_path, polygon):
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        nodata = src.nodata
        transform = src.transform

        rows, cols = data.shape
        minx, miny, maxx, maxy = polygon.bounds

        col_start, row_start = ~transform * (minx, maxy)
        col_end, row_end = ~transform * (maxx, miny)

        row_start = max(int(np.floor(row_start)) - 1, 0)
        row_end = min(int(np.ceil(row_end)) + 1, rows)
        col_start = max(int(np.floor(col_start)) - 1, 0)
        col_end = min(int(np.ceil(col_end)) + 1, cols)

        values = []
        for r in range(row_start, row_end):
            for c in range(col_start, col_end):
                value = data[r, c]
                if nodata is not None and value == nodata:
                    continue
                x, y = xy(transform, r, c)
                if polygon.contains(Point(x, y)):
                    values.append(float(value))

        if not values:
            return None

        return float(np.mean(values))