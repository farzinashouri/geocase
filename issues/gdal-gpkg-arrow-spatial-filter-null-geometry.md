# GPKG: Arrow stream returns features with NULL geometry when a spatial filter is set

> **Filed 2026-11-01 as [OSGeo/gdal#15465](https://github.com/OSGeo/gdal/issues/15465)** with the text below
> (paragraphs unwrapped for GitHub). Sections follow GDAL's bug report template.

### What is the bug?

On a GeoPackage layer with a spatial filter, `GetArrowStream()` returns features that have a NULL
geometry. `GetNextFeature()` on the same layer with the same filter does not return them.

It happens when the filter rectangle covers the whole layer extent. With a smaller rectangle the
NULL row is not returned. Points outside the rectangle are filtered correctly in both cases; only
NULL geometries get through.

I found it through pyogrio: `read_dataframe(path, bbox=...)` gave 2 rows and
`read_dataframe(path, bbox=..., use_arrow=True)` gave 3 for the same file. The extra row is
already in the stream GDAL returns, so I am reporting it here.

### Steps to reproduce the issue

```python
import os, tempfile
from osgeo import gdal, ogr, osr
gdal.UseExceptions()

path = os.path.join(tempfile.mkdtemp(), "test.gpkg")
ds = gdal.GetDriverByName("GPKG").Create(path, 0, 0, 0, gdal.GDT_Unknown)
srs = osr.SpatialReference()
srs.ImportFromEPSG(4326)
lyr = ds.CreateLayer("test", srs, ogr.wkbPoint)
lyr.CreateField(ogr.FieldDefn("v", ogr.OFTInteger))
for v, wkt in [(1, "POINT (10 50)"), (2, "POINT (11 51)"), (3, None)]:
    f = ogr.Feature(lyr.GetLayerDefn())
    f["v"] = v
    if wkt:
        f.SetGeometry(ogr.CreateGeometryFromWkt(wkt))
    lyr.CreateFeature(f)
ds = None

ds = ogr.Open(path)
lyr = ds.GetLayer(0)
lyr.SetSpatialFilterRect(9.9, 49.9, 11.1, 51.1)
print("GetNextFeature:", [f["v"] for f in lyr])
lyr.ResetReading()
print("Arrow stream:  ", [int(x) for batch in lyr.GetArrowStreamAsNumPy() for x in batch["v"]])
```

Output:

```
GetNextFeature: [1, 2]
Arrow stream:   [1, 2, 3]
```

Feature 3 has no geometry, so it should not pass the spatial filter.

Other cases (GetNextFeature result, then Arrow result). In the last two, the layer has one more
point, `v=5` at `POINT (20 60)`:

```
rectangle covers only point 1           [1]        [1]
rectangle covers points 1 and 2 only    [1, 2]     [1, 2]
rectangle (-180, -90, 180, 90)          [1, 2, 5]  [1, 2, 3, 5]
```

With `OGR_GPKG_STREAM_BASE_IMPL=YES`, the Arrow stream returns `[1, 2]`, so the generic
implementation is fine and the problem is in the GPKG-specific one. The GeoJSON and SQLite
drivers also return `[1, 2]` on both paths.

### Versions and provenance

- GDAL 3.12.2 and 3.13.3 from conda-forge, macOS arm64
- master built from source at 6a95fc6aab, macOS arm64

I did not see any change to this code in master since then.

### Additional context

I think this is the cause, from reading `ogrgeopackagetablelayer.cpp`:

When the filter rectangle covers the layer extent, `GetNextArrowArrayAsynchronousWorker()` does
not use the R-tree join (`bUseSpatialIndex = false`,
[L8653](https://github.com/OSGeo/gdal/blob/b4f950833f/ogr/ogrsf_frmts/gpkg/ogrgeopackagetablelayer.cpp#L8653)),
and it does not add `m_soFilter` either, because that only happens in the `else` branch. So the
SQL has no spatial condition and everything depends on the per-row check in
`OGR_GPKG_FillArrowArray_Step()`. That check is inside `if (nWKBSize != 0)`
([L8130](https://github.com/OSGeo/gdal/blob/b4f950833f/ogr/ogrsf_frmts/gpkg/ogrgeopackagetablelayer.cpp#L8130)),
so a NULL geometry skips it and the row is kept. This per-row check came with #8354 (the fix
for #8347).

When the R-tree join is used, NULL rows are not in the R-tree, which is why the smaller rectangle
works.

`OGRLayer::FilterGeometry()` returns FALSE for a NULL geometry, so I would expect the Arrow path to
drop the row when a spatial filter is set and the geometry is NULL. I can open a PR with that
change and a test if that is the right direction.
