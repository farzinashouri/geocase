# Adding a Case

This guide explains how to add a new GeoCase case to the bundled catalog.

The current workflow is metadata-first:

1. create a case folder and files,
2. write the case metadata,
3. add the case to `case-index.yaml`,
4. verify that GeoCase can resolve and load it,
5. add or update tests that exercise the new scenario.

---

## What a case is

A GeoCase case is a directory of test data plus a metadata file that tells GeoCase:

- what the data is,
- why it exists,
- how it should be loaded,
- what behavior or risk it is meant to expose.

Each case becomes addressable by a unique ID, which means users can select it from `pytest` with `@pytest.mark.geocase_case("your_case_id")`.

---

## Step 1 — Pick the right location

Bundled core cases live under `src/geocase/data/core/`.

Use a category-specific folder such as:

- `src/geocase/data/core/vector/`
- `src/geocase/data/core/raster/`
- `src/geocase/data/core/netcdf/`

Typical structure:

```text
src/geocase/data/core/vector/my_new_case/
├── case.yaml
├── geometry.geojson
└── notes.md
```

For raster or NetCDF cases, the primary file will usually be a `.tif`, `.tiff`, or `.nc` file instead.

---

## Step 2 — Copy the template

Start from the template:

- `src/geocase/templates/new_case.yaml`

Copy it into your new case directory as `case.yaml`, then fill in the fields.

Example starting point:

```yaml
id: my_new_case
title: My New Case
description: >
  Short description of what this case tests.
category: vector
format: GeoJSON
test_tier: unit
size_class: tiny
storage_class: bundled
redistributable: true
schema_version: "1.0"
status: draft
```

---

## Step 3 — Fill out the important metadata

### Required identity and classification fields

These fields describe the case at a catalog level:

- `id`: unique identifier, lowercase with underscores
- `title`: human-friendly name
- `description`: what the case contains and why it matters
- `category`: `vector`, `raster`, `netcdf`, or `satellite`
- `format`: data format such as `GeoJSON`, `GeoTIFF`, or `NetCDF`
- `test_tier`: such as `unit`, `integration`, or `remote`
- `size_class`: such as `tiny` or `small`
- `storage_class`: such as `bundled` or `remote`
- `status`: lifecycle status such as `draft` or `validated`

### Discovery fields

These make the case easy to select later:

- `tags`
- `risk_types`
- `geometry_type` for vector cases
- `crs` when relevant

Choose tags and risk types based on how users are likely to search for the scenario in tests.

Good examples:

- tags: `vector`, `polygon`, `hole`, `invalid`, `nodata`
- risk types: `coordinate_wrapping`, `topology_breakage`, `attribute_encoding`

### Behavioral fields

These explain why the case exists:

- `behavioral_goal`
- `expected_capabilities`
- `loader_hint`

Example:

```yaml
behavioral_goal: >
  Ensure a polygon with an interior hole loads correctly and preserves
  the hole during downstream geometry operations.

expected_capabilities:
  - load
  - geometry-validation

loader_hint: geopandas
geometry_type: Polygon
crs: EPSG:4326
```

### Files section

The `files` section tells GeoCase which file is the primary artifact.

Example:

```yaml
files:
  primary: geometry.geojson
  notes: notes.md
```

The `primary` path is relative to the directory that contains `case.yaml`.

### Assertions section

Use the `assertions` block to describe the expected baseline behavior of the case.

Example:

```yaml
assertions:
  expect_loadable: true
  expect_valid_geometry: true
  expect_crs: true
  expected_epsg: 4326
  expected_geometry_types:
    - Polygon
```

### Optional custom parameters

Use `params` for case-specific values that tests may want to read.

This is especially useful when a function test needs metadata such as:

- expected output file names,
- thresholds,
- known result values,
- special-case flags.

Example:

```yaml
params:
  expected_footprint: all_valid_rectangular.geojson
  min_rect_ratio: 0.98
```

---

## Step 4 — Add the case to the index

Bundled cases are discovered through:

- `src/geocase/metadata/case-index.yaml`

Add a new entry under `cases:`.

Example:

```yaml
cases:
  - path: data/core/vector/my_new_case/case.yaml
```

You can regenerate the index automatically with:

```bash
python scripts/build_case_index.py
```

Recommended follow-up checks:

```bash
python scripts/build_case_index.py --check
python scripts/validate_catalog.py
```

---

## Step 5 — Check a real example

Use an existing case as a model. A good starting point is:

- `src/geocase/data/core/vector/simple_valid_polygon/case.yaml`

That case shows a clear, compact metadata file with:

- good tags,
- a useful behavioral goal,
- explicit assertions,
- a bundled primary data file.

### End-to-end example: `simple_valid_polygon`

This case is a good reference because it is intentionally small and easy to understand.

Folder layout:

```text
src/geocase/data/core/vector/simple_valid_polygon/
├── case.yaml
├── geometry.geojson
└── notes.md
```

What each file does:

- `case.yaml` defines how the case is discovered and interpreted.
- `geometry.geojson` is the actual vector data.
- `notes.md` explains the testing purpose in plain language.

Key metadata choices in this case:

- `id: simple_valid_polygon` gives tests a stable explicit selector.
- `category: vector` and `format: GeoJSON` place it in the vector workflow.
- `tags: [vector, polygon, valid, baseline]` make it discoverable.
- `behavioral_goal` explains that it is the baseline happy-path polygon.
- `assertions` encode the expected baseline checks.

Index entry:

```yaml
cases:
  - path: data/core/vector/simple_valid_polygon/case.yaml
```

Minimal `pytest` check using that case:

```python
import pytest


@pytest.mark.geocase_case("simple_valid_polygon")
def test_simple_valid_polygon_smoke(geocase_case) -> None:
    gdf = geocase_case.load()

    assert geocase_case.id == "simple_valid_polygon"
    assert len(gdf) > 0
    assert gdf.crs is not None
```

That is the full GeoCase loop:

1. data file exists,
2. metadata describes it,
3. index exposes it to the registry,
4. a `pytest` marker selects it,
5. your test loads and checks it.

When creating a new case, aim for this same level of clarity before adding more complex behavior.

### Raster example: `geotiff_nodata_small`

For raster cases, the structure is very similar, but tests will usually use `.read(1)` or `.open()` instead of `.load()`.

Folder layout:

```text
src/geocase/data/core/raster/geotiff_nodata_small/
├── case.yaml
├── nodata_sample.tif
├── nodata_sample.tif.aux.xml
└── notes.md
```

Why this case is useful:

- it is tiny and fast to load,
- it exercises explicit NoData handling,
- it provides concrete expected metadata in `params`.

Notable metadata choices:

- `category: raster`
- `format: GeoTIFF`
- `loader_hint: rasterio`
- `risk_types: [nodata_ignored, nan_propagation, incorrect_statistics]`
- `params.nodata_value: -9999`
- `params.band_count: 1`
- `params.dtype: float32`

Index entry:

```yaml
cases:
  - path: data/core/raster/geotiff_nodata_small/case.yaml
```

Minimal `pytest` check using that case:

```python
import pytest


@pytest.mark.geocase_case("geotiff_nodata_small")
def test_geotiff_nodata_small_smoke(geocase_case) -> None:
    data, _, nodata = geocase_case.read(1)

    assert geocase_case.id == "geotiff_nodata_small"
    assert nodata == -9999
    assert data.size > 0
```

If your function needs a raster dataset handle instead of an array, use `geocase_case.open()` and run rasterio-based assertions there.

---

## Step 6 — Verify the new case

At minimum, verify the following:

1. the metadata is valid and readable,
2. the indexed path is correct,
3. the case loads through GeoCase,
4. the case can be selected by ID,
5. the case supports the intended assertions.
6. related suites include (or intentionally exclude) the new case.

Practical checks today:

```python
import pytest


@pytest.mark.geocase_case("my_new_case")
def test_my_new_case_loads(geocase_case) -> None:
    loaded = geocase_case.load()
    assert loaded is not None
```

If the case is raster-based, use `.read(1)` or `.open()` instead of `.load()`.

Suite and catalog checks:

```bash
python scripts/validate_catalog.py
```

---

## Step 7 — Add targeted tests

Every new case should justify itself by improving test coverage.

Common patterns:

- add a new unit test that directly selects the case,
- extend a selector-based test so the new case participates naturally,
- add case-specific expectations using `geocase.id` or `geocase.metadata.params`.

Examples:

```python
@pytest.mark.geocase_case("my_new_case")
def test_specific_behavior(geocase_case) -> None:
    data = geocase_case.load()
    assert data is not None
```

```python
@pytest.mark.geocase_select(category="vector", tags_any=["hole"])
def test_all_hole_cases(geocase) -> None:
    gdf = geocase.load()
    assert len(gdf) > 0
```

---

## Writing a good case

A strong case is:

- small enough to keep the repo lightweight,
- focused on one clear failure mode,
- easy to describe in one paragraph,
- tagged so users can discover it later,
- accompanied by a test that demonstrates why it exists.

Try not to add a case that is only “interesting data”. Add a case that captures a real testing need.

---

## Recommended author checklist

Before considering a case complete, check all of the following:

- folder is placed under the correct category path,
- `case.yaml` is filled out completely,
- `id` is unique and stable,
- `files.primary` points to the right artifact,
- tags and risk types are useful for selection,
- `case-index.yaml` contains the new path,
- suite membership is reviewed (`src/geocase/catalog/suites/*.yaml`),
- at least one test exercises the case,
- notes or provenance are included when helpful,
- case size is kept as small as practical.

---

## Current limitations

Catalog validation is handled by maintainer scripts:

```bash
python scripts/build_case_index.py --check
python scripts/validate_catalog.py
```

---

## Related docs

- `docs/getting-started.md`
- `docs/contributing/vector-dataset-generation.md`
- `docs/testing-your-function-with-geocase.md`
- `docs/contributing/workflow.md`
- `docs/contributing/development-plan.md`

