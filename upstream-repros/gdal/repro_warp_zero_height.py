"""AutoCreateWarpedVRT returns a dataset with RasterYSize == 0.

Standalone: builds its own file, does not import geocase.

    python repro_warp_zero_height.py

Filed: https://github.com/OSGeo/gdal/issues/15266
Fixed: https://github.com/OSGeo/gdal/pull/15274 (merged 2026-10-01). After the
fix, GDALSuggestedWarpOutput2 fails with an error instead of returning 0 rows.

A 16x16 EPSG:4326 raster crossing the antimeridian (x from 179.9 to 180.22),
warped to EPSG:3857. PROJ wraps the east edge to about -20013018 m, so the
suggested output spans the globe in X while Y spans ~35 km.
GDALSuggestedWarpOutput2 derives one square pixel size from the diagonal of that
extent, the line count rounds to 0, and the function still returns CE_None.

Expected: a usable dataset, or a clear failure from SuggestedWarpOutput.
Actual:   a 23x0 dataset; gdal.Warp later fails with
          "Attempt to create 23x0 dataset is illegal".

Control: the same raster shifted to x = 10.0 warps to a normal size.
"""

import os
import tempfile

from osgeo import gdal, osr

gdal.UseExceptions()


def make(path, x0):
    ds = gdal.GetDriverByName("GTiff").Create(path, 16, 16, 1, gdal.GDT_Byte)
    ds.SetGeoTransform((x0, 0.02, 0.0, 1.0, 0.0, -0.02))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    ds.SetSpatialRef(srs)
    ds.GetRasterBand(1).Fill(1)
    ds = None
    return path


def warped_size(path):
    tgt = osr.SpatialReference()
    tgt.ImportFromEPSG(3857)
    try:
        vrt = gdal.AutoCreateWarpedVRT(gdal.Open(path), None, tgt.ExportToWkt())
    except RuntimeError as e:
        return f"error: {e}"
    return (vrt.RasterXSize, vrt.RasterYSize)


def main():
    print("GDAL", gdal.__version__)
    d = tempfile.mkdtemp()
    dateline = warped_size(make(os.path.join(d, "dateline.tif"), 179.9))
    control = warped_size(make(os.path.join(d, "normal.tif"), 10.0))
    print("antimeridian source -> warped VRT size:", dateline)
    print("control (x0 = 10)   -> warped VRT size:", control)

    ok = isinstance(dateline, tuple) and dateline[1] == 0 and isinstance(control, tuple) and control[1] > 0
    print("\nRESULT:", "REPRODUCED" if ok else "did not reproduce")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
