# Two `use_arrow=True` divergences in `read_dataframe` (GDAL 3.13.3)

Both findings below were surfaced by running pyogrio's read paths against
[**geocase**](https://pypi.org/project/geocase/), a curated corpus of geospatial
edge-case files, and diffing the `use_arrow=True` results against the `use_arrow=False`
results for every case. The harness was a differential one: same file, same keyword
arguments, two code paths, compare.

**Finding 1 is a pyogrio bug** and reduces to a self-contained repro with no geocase
dependency — eight lines of stdlib `json`. A suggested patch and a regression test are
included; take them or redo them as you prefer.

**Finding 2 originates in GDAL**, not in pyogrio. It is reported here only because it
contradicts a statement in pyogrio's own `known_issues.md`, so the docs are stale
regardless of what GDAL does about it.

## Environment

| | |
|---|---|
| pyogrio | built from source at `main` |
| GDAL | 3.13.3 (conda-forge `libgdal-core`) |
| Python | 3.11.16 |
| pyarrow | 25.0.0 |
| geopandas | 1.1.4 |
| pandas | 3.0.5 |
| shapely | 2.1.2 |
| OS | Linux x86_64 |

---

# Finding 1 — `fid_as_index=True` + `use_arrow=True` raises `ValueError: Index data must be 1-dimensional`

## Repro (no geocase needed)

```python
import json, tempfile
from pathlib import Path
from pyogrio import read_dataframe

gj = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"id": 1, "label": "a"},
     "geometry": {"type": "Point", "coordinates": [0, 0]}},
    {"type": "Feature", "properties": {"id": 2, "label": "b"},
     "geometry": {"type": "Point", "coordinates": [1, 1]}}]}

p = Path(tempfile.mkdtemp()) / "t.geojson"
p.write_text(json.dumps(gj))

read_dataframe(p, fid_as_index=True)                   # works
read_dataframe(p, fid_as_index=True, use_arrow=True)   # ValueError
```

Observed:

```
numpy: {'id': {1: 1, 2: 2}, 'label': {1: 'a', 2: 'b'}, 'geometry': {1: <POINT (0 0)>, 2: <POINT (1 1)>}}
arrow: ValueError: Index data must be 1-dimensional
```

Traceback tail:

```
  File "pyogrio/geopandas.py", line 467, in read_dataframe
    df = df.set_index(meta["fid_column"])
  File "pandas/core/indexes/base.py", line 585, in __new__
    raise ValueError("Index data must be 1-dimensional") from err
ValueError: Data must be 1-dimensional, got ndarray of shape (2, 2) instead
```

The trigger is any layer whose FID column is *also* exposed as a regular field. The
GeoJSON driver does this: an integer `id` property is promoted to the FID column while
still being served as an ordinary field.

## Root cause

`OGR_L_GetFIDColumn()` returns `"id"` for this layer, and the field list also contains
`"id"`:

```python
>>> read_info(p)["fid_column"]
'id'
>>> with open_arrow(p, return_fids=True, use_pyarrow=True) as (meta, reader):
...     print(meta["fid_column"], list(meta["fields"]), reader.read_all().schema.names)
id ['id', 'label'] ['id', 'id', 'label', 'wkb_geometry']
```

The Arrow stream carries `id` **twice** — once as the FID column that `INCLUDE_FID=YES`
adds (`pyogrio/_io.pyx:2135`, left at YES because `return_fids` is set), once as the
regular field, which is not in `ignored_fields`. `df.set_index("id")` therefore selects
a 2-column block and pandas rejects it.

The underlying issue is an asymmetry between the two read paths:

- **non-arrow** (`pyogrio/geopandas.py:500`) receives FIDs as a **separate array** from
  `ogr_read`, so a name collision cannot arise.
- **arrow** (`pyogrio/geopandas.py:467`) resolves the FID **by name** against the
  converted DataFrame.

Name-based lookup is not safe here, because the FID name is not guaranteed to be unique
within the Arrow schema.

## Driver matrix

Same three-feature layer written to each format, then read with `fid_as_index=True`:

| driver | `use_arrow=False` | `use_arrow=True` |
|---|---|---|
| GeoJSON | index `[1, 2, 3]` | **`ValueError`** |
| GPKG | index `[1, 2, 3]` | index `[1, 2, 3]` |
| FlatGeobuf | index `[0, 1, 2]` | index `[0, 1, 2]` |
| ESRI Shapefile | index `[0, 1, 2]` | index `[0, 1, 2]` |
| SQLite | index `[1, 2, 3]` | index `[1, 2, 3]` |

GeoJSON is the only affected driver among those tested — it is the one that promotes a
field to the FID column without withdrawing it from the field list.

## Suggested fix

Rename the duplicated FID column on the Arrow table before `to_pandas()`, and index on
the renamed column, leaving the user's `id` field intact.

```diff
--- a/pyogrio/geopandas.py
+++ b/pyogrio/geopandas.py
@@ -404,6 +404,17 @@ def read_dataframe(

         meta, table = result

+        fid_column = meta["fid_column"]
+        if fid_as_index and table.schema.names.count(fid_column) > 1:
+            # Some drivers (e.g. GeoJSON) promote a field to the FID column but keep
+            # exposing it as a regular field, so the Arrow table contains two columns
+            # with the same name. Rename the FID column (always the first one) to avoid
+            # an ambiguous lookup when setting the index below.
+            fid_column = "__pyogrio_fid__"
+            names = list(table.schema.names)
+            names[names.index(meta["fid_column"])] = fid_column
+            table = table.rename_columns(names)
+
         # split_blocks and self_destruct decrease memory usage, but have as side effect
         # that accessing table afterwards causes crash, so del table to avoid.
         kwargs = {"self_destruct": True}
@@ -464,7 +475,7 @@ def read_dataframe(

         if fid_as_index:
-            df = df.set_index(meta["fid_column"])
+            df = df.set_index(fid_column)
             df.index.names = ["fid"]
```

Relying on the FID column being the first occurrence matches GDAL's `INCLUDE_FID`
behaviour. If you would rather not depend on that, selecting by schema position instead
of by name would be equivalent and slightly more explicit.

After the patch, the arrow path matches the non-arrow path exactly across the option
combinations that interact with `fid_as_index`:

| options | `use_arrow=False` | `use_arrow=True` |
|---|---|---|
| `fid_as_index=True` | cols `['id','label','geometry']`, idx `[1,2,3]` | identical |
| `+ fids=[1]` | cols `['id','label','geometry']`, idx `[1]` | identical |
| `+ columns=['label']` | cols `['label','geometry']`, idx `[1,2,3]` | identical |
| `+ read_geometry=False` | cols `['id','label']`, idx `[1,2,3]` | identical |

## Regression test

Added next to `test_read_fid_as_index_only` in `pyogrio/tests/test_geopandas_io.py`
(needs `import json` at the top of the module):

```python
def test_read_fid_as_index_fid_column_collision(tmp_path, use_arrow):
    """FID column exposed as a regular field as well should not break the index.

    The GeoJSON driver promotes an integer "id" property to the FID column while
    still exposing it as a regular field, so the Arrow table contains two columns
    named "id".
    """
    filename = tmp_path / "test.geojson"
    filename.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"id": 1, "label": "a"},
                        "geometry": {"type": "Point", "coordinates": [0, 0]},
                    },
                    {
                        "type": "Feature",
                        "properties": {"id": 2, "label": "b"},
                        "geometry": {"type": "Point", "coordinates": [1, 1]},
                    },
                ],
            }
        )
    )

    df = read_dataframe(filename, fid_as_index=True, use_arrow=use_arrow)

    assert_index_equal(df.index, pd.Index([1, 2], name="fid"))
    assert list(df.columns) == ["id", "label", "geometry"]
    assert df["id"].tolist() == [1, 2]
```

This test raises the original `ValueError` on unpatched code for the `use_arrow=True`
parametrisation and passes for both parametrisations after the patch.

## Verification performed

- `pytest pyogrio/tests -q -m "not network"` → **1630 passed, 43 skipped, 1 xfailed,
  5 xpassed** — no regressions.
- `ruff format --check` and `ruff check` clean on both touched files.

---

# Finding 2 — GPKG spatial filter with Arrow returns NULL-geometry features (GDAL-side)

## Observation

A GPKG layer with two valid points and one NULL geometry, read under a `bbox` that
covers both points:

```python
gdf = gpd.GeoDataFrame({"v": [1, 2, 3]},
                       geometry=[Point(10, 50), Point(11, 51), None], crs="EPSG:4326")
write_dataframe(gdf, "t.gpkg")

bbox = (9.9, 49.9, 11.1, 51.1)
len(read_dataframe("t.gpkg", bbox=bbox))                   # 2
len(read_dataframe("t.gpkg", bbox=bbox, use_arrow=True))   # 3  <-- extra NULL-geometry row
```

The same divergence occurs with `mask=box(*bbox)`: 2 vs 3.

## This is inside GDAL, not pyogrio

`ogrinfo` agrees with the non-arrow path:

```
$ ogrinfo -so -spat 9.9 49.9 11.1 51.1 t.gpkg empty_geom
Feature Count: 2
```

and the divergence is already present in the raw stream, before pyogrio touches the
data:

```python
>>> with open_arrow(path, bbox=bbox, use_pyarrow=True) as (meta, r):
...     r.read_all().num_rows
3
```

pyogrio calls `apply_bbox_filter` (`OGR_L_SetSpatialFilterRect`) and then
`OGR_L_GetArrowStream`, so the NULL-geometry feature is being admitted by GDAL's
`GetArrowStream` under a spatial filter that the ordinary feature iterator honours.
I am filing this upstream separately; no pyogrio code change is implied.

## Driver matrix

| driver | `use_arrow=False` | `use_arrow=True` |
|---|---|---|
| GPKG | 2 | **3** |
| GeoJSON | 2 | 2 |
| ESRI Shapefile | 2 | 2 |
| SQLite | 2 | 2 |
| FlatGeobuf | n/a | n/a — driver refuses NULL geometry with a spatial index |

## The docs request

`docs/source/known_issues.md`, section *"Incorrect results when using a spatial filter
and Arrow interface"*, currently closes with:

> A fix is expected in GDAL 3.8.0.

GPKG is listed among the affected drivers in that section, and this residual case is
live on **GDAL 3.13.3**. Whatever happens upstream, that sentence is now misleading for
anyone choosing between `use_arrow=True` and `use_arrow=False` for filtered reads.
Suggest narrowing the section to the case that remains — a spatial filter combined with
the Arrow interface can return features with NULL geometry on GPKG — and dropping the
version expectation.

---

## Credit

Both findings came out of a validation run of geocase against pyogrio. Finding 1 came
from a three-point GeoJSON case built around antimeridian coordinates whose `id`
property happened to trip the FID promotion; Finding 2 came from a GPKG case built
specifically around a NULL geometry alongside a `POINT EMPTY`. Neither is a file shape
that a hand-written test suite tends to produce on purpose, which is the argument for
that kind of corpus.
