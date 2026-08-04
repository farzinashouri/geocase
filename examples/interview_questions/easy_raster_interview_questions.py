"""Raster-specific easy geospatial interview coding questions.

Twenty short, raster-focused exercises. Only the "simple" reference
implementation is provided for each one (a "perfect", hardened variant can be
added later, mirroring easy_geospatial_interview_questions.py).

All functions rely on GDAL and NumPy, the two libraries you can assume are
available in a typical raster-processing interview.
"""

from __future__ import annotations

import numpy as np
from osgeo import gdal, osr
from pyproj import CRS, Transformer

gdal.UseExceptions()


# =========================================================
# 1. Read basic raster metadata
# =========================================================

def raster_info(path: str) -> dict:
    """Return width, height, band count and CRS (EPSG) of a raster."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {path}")

    proj = ds.GetProjection()
    epsg = CRS.from_wkt(proj).to_epsg() if proj else None

    return {
        "width": ds.RasterXSize,
        "height": ds.RasterYSize,
        "bands": ds.RasterCount,
        "epsg": epsg,
    }


# =========================================================
# 2. Compute the geographic extent of a raster
# =========================================================

def raster_extent(path: str) -> tuple[float, float, float, float]:
    """Return (minx, miny, maxx, maxy) of a north-up raster."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {path}")

    gt = ds.GetGeoTransform()
    width, height = ds.RasterXSize, ds.RasterYSize

    minx = gt[0]
    maxy = gt[3]
    maxx = gt[0] + width * gt[1]
    miny = gt[3] + height * gt[5]
    return min(minx, maxx), min(miny, maxy), max(minx, maxx), max(miny, maxy)


# =========================================================
# 3. Get the pixel (ground) resolution of a raster
# =========================================================

def pixel_size(path: str) -> tuple[float, float]:
    """Return (x_resolution, y_resolution) as positive values."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {path}")

    gt = ds.GetGeoTransform()
    return abs(gt[1]), abs(gt[5])


# =========================================================
# 4. Convert world (map) coordinates to pixel row/col
# =========================================================

def world_to_pixel(path: str, x: float, y: float) -> tuple[int, int]:
    """Return the (row, col) index containing world coordinate (x, y)."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {path}")

    gt = ds.GetGeoTransform()
    col = int((x - gt[0]) / gt[1])
    row = int((y - gt[3]) / gt[5])
    return row, col


# =========================================================
# 5. Read a single band into a NumPy array
# =========================================================

def read_band(path: str, band_index: int = 1) -> np.ndarray:
    """Read the given 1-based band into a NumPy array."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {path}")

    band = ds.GetRasterBand(band_index)
    return band.ReadAsArray()


# =========================================================
# 6. Compute basic band statistics (ignoring nodata)
# =========================================================

def band_statistics(path: str, band_index: int = 1) -> dict:
    """Return min, max, mean and std of a band, ignoring nodata."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {path}")

    band = ds.GetRasterBand(band_index)
    arr = band.ReadAsArray().astype("float64")

    nodata = band.GetNoDataValue()
    if nodata is not None:
        arr = arr[arr != nodata]

    return {
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
    }


# =========================================================
# 7. Count valid (non-nodata) pixels
# =========================================================

def count_valid_pixels(path: str, band_index: int = 1) -> int:
    """Return the number of pixels that are not nodata."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {path}")

    band = ds.GetRasterBand(band_index)
    arr = band.ReadAsArray()
    nodata = band.GetNoDataValue()

    if nodata is None:
        return int(arr.size)
    return int(np.count_nonzero(arr != nodata))


# =========================================================
# 8. Replace a nodata value
# =========================================================

def replace_nodata(arr: np.ndarray, old_nodata: float, new_value: float) -> np.ndarray:
    """Return a copy of arr with old_nodata replaced by new_value."""
    out = arr.copy()
    out[out == old_nodata] = new_value
    return out


# =========================================================
# 9. Compute NDVI from red and near-infrared bands
# =========================================================

def ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """Return the Normalized Difference Vegetation Index."""
    red = red.astype("float64")
    nir = nir.astype("float64")
    denom = nir + red
    with np.errstate(divide="ignore", invalid="ignore"):
        result = (nir - red) / denom
    result[denom == 0] = 0.0
    return result


# =========================================================
# 10. Write a NumPy array to a GeoTIFF
# =========================================================

def write_geotiff(
    path: str,
    array: np.ndarray,
    geotransform: tuple[float, float, float, float, float, float],
    epsg: int,
) -> None:
    """Write a single-band array to a GeoTIFF with the given georeference."""
    height, width = array.shape
    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(path, width, height, 1, gdal.GDT_Float32)

    out_ds.SetGeoTransform(geotransform)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)
    out_ds.SetProjection(srs.ExportToWkt())

    out_ds.GetRasterBand(1).WriteArray(array)
    out_ds.FlushCache()
    out_ds = None


# =========================================================
# 11. Resample a raster to a new pixel size
# =========================================================

def resample_raster(input_path: str, output_path: str, x_res: float, y_res: float) -> None:
    """Resample a raster to the requested pixel size using bilinear interpolation."""
    ds = gdal.Open(input_path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {input_path}")

    gdal.Warp(
        output_path,
        ds,
        xRes=x_res,
        yRes=y_res,
        resampleAlg="bilinear",
    )
    ds = None


# =========================================================
# 12. Reproject a raster to a new CRS
# =========================================================

def reproject_raster(input_path: str, output_path: str, dst_epsg: int) -> None:
    """Reproject a raster to the target EPSG code."""
    ds = gdal.Open(input_path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {input_path}")

    gdal.Warp(output_path, ds, dstSRS=f"EPSG:{dst_epsg}")
    ds = None


# =========================================================
# 13. Build a binary mask from a threshold
# =========================================================

def threshold_mask(arr: np.ndarray, threshold: float) -> np.ndarray:
    """Return a uint8 mask where values >= threshold are 1, else 0."""
    return (arr >= threshold).astype("uint8")


# =========================================================
# 14. Compute a per-pixel mean across multiple rasters
# =========================================================

def stack_mean(arrays: list[np.ndarray]) -> np.ndarray:
    """Return the element-wise mean of equally-shaped arrays."""
    if not arrays:
        raise ValueError("arrays must not be empty.")
    stack = np.stack([a.astype("float64") for a in arrays], axis=0)
    return np.mean(stack, axis=0)


# =========================================================
# 15. Build overviews (pyramids) for a raster
# =========================================================

def build_overviews(path: str, levels: list[int] | None = None) -> None:
    """Build internal overviews for faster display at lower resolutions."""
    if levels is None:
        levels = [2, 4, 8, 16]
    ds = gdal.Open(path, gdal.GA_Update)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster for update: {path}")

    ds.BuildOverviews("AVERAGE", levels)
    ds = None


# =========================================================
# 16. Sample a raster value at a pixel
# =========================================================

def sample_pixel(path: str, row: int, col: int, band_index: int = 1) -> float:
    """Return the value of a single pixel."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {path}")

    band = ds.GetRasterBand(band_index)
    arr = band.ReadAsArray(col, row, 1, 1)
    if arr is None:
        raise RuntimeError("Failed to read raster value.")
    return float(arr[0, 0])


# =========================================================
# 17. Convert a pixel center to world coordinates
# =========================================================

def pixel_center_to_world(path: str, row: int, col: int) -> tuple[float, float]:
    """Return the world (x, y) coordinate of a pixel's center."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {path}")

    gt = ds.GetGeoTransform()
    x = gt[0] + (col + 0.5) * gt[1] + (row + 0.5) * gt[2]
    y = gt[3] + (col + 0.5) * gt[4] + (row + 0.5) * gt[5]
    return x, y


# =========================================================
# 18. Reproject a single coordinate into the raster's CRS
# =========================================================

def lonlat_to_raster_crs(path: str, lon: float, lat: float) -> tuple[float, float]:
    """Transform a WGS84 lon/lat into the raster's coordinate system."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {path}")

    proj = ds.GetProjection()
    if not proj:
        raise ValueError("Raster has no CRS/projection.")

    raster_crs = CRS.from_wkt(proj)
    if raster_crs.to_epsg() == 4326:
        return lon, lat

    transformer = Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True)
    return transformer.transform(lon, lat)


# =========================================================
# 19. Compute the area of valid data in square meters
# =========================================================

def valid_data_area_m2(path: str, band_index: int = 1) -> float:
    """Return the ground area of valid pixels, assuming a projected CRS in meters."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {path}")

    gt = ds.GetGeoTransform()
    pixel_area = abs(gt[1] * gt[5])

    band = ds.GetRasterBand(band_index)
    arr = band.ReadAsArray()
    nodata = band.GetNoDataValue()

    valid = arr.size if nodata is None else int(np.count_nonzero(arr != nodata))
    return float(valid * pixel_area)


# =========================================================
# 20. Build a histogram of pixel values
# =========================================================

def value_histogram(path: str, bins: int = 10, band_index: int = 1) -> tuple[list, list]:
    """Return (counts, bin_edges) for a band's valid pixels."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {path}")

    band = ds.GetRasterBand(band_index)
    arr = band.ReadAsArray().astype("float64")
    nodata = band.GetNoDataValue()
    if nodata is not None:
        arr = arr[arr != nodata]

    counts, edges = np.histogram(arr, bins=bins)
    return counts.tolist(), edges.tolist()
