"""GDAL silently writes coordinates in [1e-14, 1e-13) as 0.

Builds its own file. Does not import geocase.
Expected: the coordinate survives a GeoJSON round-trip, since 1e-14 is
0.00000000000001 -- 14 decimal places, inside the writer's own 15-decimal
default precision.
Actual: it is written as 0.0.
"""
import json, os, tempfile
from osgeo import gdal, ogr
gdal.UseExceptions()

src = os.path.join(tempfile.mkdtemp(), "in.geojson")
with open(src, "w") as f:
    json.dump({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"id": 1},
         "geometry": {"type": "Point", "coordinates": [1e-14, 1e-14]}}]}, f)

dst = src.replace("in.", "out.")
gdal.VectorTranslate(dst, src, format="GeoJSON")
out = json.load(open(dst))["features"][0]["geometry"]["coordinates"]
print("in  :", [1e-14, 1e-14])
print("out :", out)

# Same defect on the WKT path, no file involved.
g = ogr.CreateGeometryFromWkt("POINT (1e-14 1)")
print("wkt :", g.ExportToWkt())

assert out == [1e-14, 1e-14], f"coordinate destroyed: {out}"
