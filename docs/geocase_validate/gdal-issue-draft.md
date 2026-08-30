# GetArrowStream on GPKG returns NULL-geometry features when a spatial filter is set

## Summary

With a spatial filter active on a GPKG layer, `OGR_L_GetArrowStream()` returns features
whose geometry is NULL. The ordinary feature iterator on the same layer with the same
filter excludes them, so the two access paths disagree on the same query.

This looks adjacent to #8347 (spatial filter not honoured exactly through the Arrow
interface, fixed for GDAL 3.8) — the bbox-intersection behaviour described there is
gone, but NULL-geometry features still pass the filter through the Arrow path.

## Environment

- GDAL **3.13.3**, conda-forge `libgdal-core`
- Linux x86_64
- Observed through pyogrio, but reproduced below at the C-API level via `ogrinfo` plus a
  direct `GetArrowStream` consumer.

## Reproducing fixture

Three features: two valid points and one NULL geometry.

```bash
cat > src.geojson <<'EOF'
{"type":"FeatureCollection","features":[
 {"type":"Feature","properties":{"v":1},"geometry":{"type":"Point","coordinates":[10,50]}},
 {"type":"Feature","properties":{"v":2},"geometry":{"type":"Point","coordinates":[11,51]}},
 {"type":"Feature","properties":{"v":3},"geometry":null}]}
EOF

ogr2ogr -f GPKG -nln empty_geom -a_srs EPSG:4326 t.gpkg src.geojson
```

## Expected

Both access paths return the 2 features whose geometry intersects the filter rectangle.
A NULL geometry intersects nothing, so it should not be returned.

## Actual

Feature iterator — correct:

```
$ ogrinfo -so -spat 9.9 49.9 11.1 51.1 t.gpkg empty_geom
Feature Count: 2

$ ogrinfo -spat 9.9 49.9 11.1 51.1 t.gpkg empty_geom | grep -E '^OGRFeature|POINT'
OGRFeature(empty_geom):1
  POINT (10 50)
OGRFeature(empty_geom):2
  POINT (11 51)
```

Arrow stream — returns 3 rows, the third with a NULL geometry:

```python
# equivalent to: OGR_L_SetSpatialFilterRect(layer, 9.9, 49.9, 11.1, 51.1)
#                OGR_L_GetArrowStream(layer, &stream, options)
from pyogrio import open_arrow

with open_arrow("t.gpkg", bbox=(9.9, 49.9, 11.1, 51.1), use_pyarrow=True) as (meta, reader):
    print(reader.read_all().num_rows)     # 3, expected 2
```

The same happens with a general geometry filter (`OGR_L_SetSpatialFilter` with a polygon
covering both points) rather than a rectangle.

## Driver scope

Tested with the same three features written to each format:

| driver | feature iterator | Arrow stream |
|---|---|---|
| **GPKG** | 2 | **3** |
| GeoJSON | 2 | 2 |
| ESRI Shapefile | 2 | 2 |
| SQLite | 2 | 2 |
| FlatGeobuf | n/a — driver rejects NULL geometry when a spatial index is created | |

Only GPKG diverges among the drivers tested, which suggests the GPKG Arrow
fast-path rather than the generic implementation.

## Why it matters

Consumers that offer both access paths — pyogrio's `use_arrow=True` / `False`, and
anything layered on it such as GeoPandas — silently return a different number of rows
for the same filtered query depending on which path is taken. Rows with NULL geometry
appearing in a spatially filtered result are also easy to carry a long way downstream
before anyone notices, since a NULL geometry does not raise anything on its own.

## Credit

Found while validating [geocase](https://pypi.org/project/geocase/), a curated corpus of
geospatial edge-case files, against pyogrio; the triggering case is a GPKG holding a
NULL geometry alongside a `POINT EMPTY`.
