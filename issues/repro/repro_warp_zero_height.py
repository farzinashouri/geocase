"""AutoCreateWarpedVRT returns a dataset with RasterYSize == 0.

Builds its own file. Does not import geocase.
A 16x16 EPSG:4326 raster crossing the antimeridian (x from 179.9 to 180.22)
warped to EPSG:3857: PROJ wraps the east edge to -20013018, so the suggested
output spans the globe in X while Y spans ~35 km. GDALSuggestedWarpOutput2
rounds the line count to 0 and reports success.

Expected: a valid dataset, or a clear failure from SuggestedWarpOutput.
Actual: a 23x0 dataset; gdal.Warp later fails with
        "Attempt to create 23x0 dataset is illegal".
"""
import os, tempfile
from osgeo import gdal, osr
gdal.UseExceptions()

path = os.path.join(tempfile.mkdtemp(), "dateline.tif")
ds = gdal.GetDriverByName("GTiff").Create(path, 16, 16, 1, gdal.GDT_Byte)
ds.SetGeoTransform((179.9, 0.02, 0.0, 1.0, 0.0, -0.02))
srs = osr.SpatialReference(); srs.ImportFromEPSG(4326)
ds.SetSpatialRef(srs)
ds.GetRasterBand(1).Fill(1)
ds = None

tgt = osr.SpatialReference(); tgt.ImportFromEPSG(3857)
vrt = gdal.AutoCreateWarpedVRT(gdal.Open(path), None, tgt.ExportToWkt())
print("warped VRT size:", vrt.RasterXSize, "x", vrt.RasterYSize)
assert vrt.RasterYSize > 0, "AutoCreateWarpedVRT returned a zero-height dataset"
