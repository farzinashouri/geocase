import rasterio
from pyproj import Transformer


def sample_at(raster_path, lon, lat):
    with rasterio.open(raster_path) as src:
        transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
        x, y = transformer.transform(lon, lat)

        row, col = src.index(x, y)
        if row < 0 or row >= src.height or col < 0 or col >= src.width:
            return None

        band = src.read(1, window=((row, row + 1), (col, col + 1)))
        value = band[0, 0]

        nodata = src.nodata
        if nodata is not None and value == nodata:
            return None

        return float(value)