---
description: "Install GeoCase and run your first geospatial test in plain pytest, using the geocase_case fixture and the geocase_suite and geocase_select markers."
---

# Getting Started

This guide shows the fastest way to start using GeoCase with plain `pytest`.

GeoCase is built around a simple workflow:

1. install the package into your test environment,
2. select cases by ID, suite, or metadata,
3. write a normal `pytest` test,
4. let GeoCase provide realistic geospatial inputs.

To see what ships in the box, [browse all 163 cases](_generated/catalog/index.md).

If you want to understand the broader roadmap, see [`docs/plans/development-plan.md`](https://github.com/farzinashouri/geocase/blob/main/docs/plans/development-plan.md).

---

## What GeoCase gives you

GeoCase provides:

- packaged geospatial test cases,
- `pytest` markers for selecting relevant cases,
- fixtures that materialize case objects in your tests,
- reusable geospatial assertion helpers.

The primary goal is not to introduce a new test runner. The goal is to make your existing `pytest` workflow more realistic for geospatial code.

---

## Install

### Local development in this repository

If you are working inside this repository, use an editable install:

```bash
pip install -e ".[dev]"
```

### Installed package usage

There are two supported install shapes. Pick by whether you already have a geospatial stack.

**Greenfield** — no geo stack yet, let pip build one:

```bash
pip install "geocase[all]"
```

**Existing geo stack** — you already have GDAL, geopandas or rasterio, from conda, system
packages, or a `--system-site-packages` venv:

```bash
pip install geocase
```

Plain `geocase` is enough to enumerate, select and resolve every case. It pulls in only
`pydantic`, `pyyaml` and `geofacts`, and `case.primary_path` is an ordinary filesystem path,
so you read the file with the readers you already have:

```python
import geocase
from osgeo import gdal

case = geocase.load_case("rotated_two_islands")
ds = gdal.Open(str(case.primary_path))       # no optional dependency needed
```

The extras exist for the convenience loaders — `case.load()` returning a GeoDataFrame,
`case.read()` returning an array — not for reading the files at all.

`[all]` re-resolves numpy and pandas and can shadow or break a working geospatial
environment. Use it only in a greenfield one.

---

## Your first GeoCase test

### Explicit case IDs

Use explicit IDs when you know exactly which edge cases you want.

```python
import pytest


@pytest.mark.geocase_case("dateline_crossing_polygon")
def test_case_loads(geocase_case) -> None:
    gdf = geocase_case.load()

    assert geocase_case.id == "dateline_crossing_polygon"
    assert gdf.crs is not None
```

This is the most direct way to get started.

### Metadata-based selection

Use metadata selectors when you want your test to cover a whole family of cases.

```python
import pytest


@pytest.mark.geocase_select(category="raster")
def test_all_raster_cases_have_pixels(geocase) -> None:
    data, _, _ = geocase.read(1)
    assert data.size > 0
```

This runs once per matching case.

---

## Core markers and fixtures

### Markers

- `@pytest.mark.geocase_case(...)` selects explicit case IDs.
- `@pytest.mark.geocase_suite(...)` selects a named suite.
- `@pytest.mark.geocase_select(...)` selects cases by metadata.

### Fixtures

- `geocase` gives one resolved case per test invocation.
- `geocase_case` gives exactly one resolved case and is convenient for single-case tests.
- `geocase_cases` gives all resolved cases as a list.

---

## Start here: the georeferencing conventions suite

If you are new to GeoCase and want the shortest path from install to a real
finding, run this suite first:

```python
@pytest.mark.geocase_suite("georeferencing-conventions")
def test_georeferencing(geocase) -> None:
    ...
```

It gathers the affine-transform and footprint cases that live in three
different corpus directories — rotated geotransforms, bottom-up rasters,
pixel-is-area versus pixel-is-point anchoring, footprints over sparse or
holed coverage, and antimeridian bounds. Every defect reported by the most
recent external consumer came from this axis, and none of these cases are
ones a team tends to construct for itself.

The cases read as ordinary files: `case.primary_path` is a filesystem path,
so `gdal.Open` works with no optional dependency installed.

---

## Common patterns

### Test one known edge case

```python
@pytest.mark.geocase_case("geotiff_nodata_small")
def test_nodata_case(geocase_case) -> None:
    data, _, nodata = geocase_case.read(1)
    assert nodata is not None
```

### Test a whole category

```python
@pytest.mark.geocase_select(category="vector")
def test_all_vectors_load(geocase) -> None:
    gdf = geocase.load()
    assert len(gdf) > 0
```

### Test by geometry type

```python
@pytest.mark.geocase_select(category="vector", geometry_type="Polygon")
def test_polygon_cases(geocase) -> None:
    gdf = geocase.load()
    assert len(gdf) > 0
```

### Branch expectations by case ID

```python
@pytest.mark.geocase_case("geotiff_nodata_small", "geotiff_utm_boundary")
def test_two_raster_behaviors(geocase) -> None:
    if geocase.id == "geotiff_nodata_small":
        data, _, nodata = geocase.read(1)
        assert nodata is not None
    elif geocase.id == "geotiff_utm_boundary":
        assert geocase.primary_path.suffix.lower() in {".tif", ".tiff"}
```

---

## Running tests

Run all tests:

```bash
pytest
```

Run only GeoCase-driven tests:

```bash
pytest -m "geocase_case or geocase_suite or geocase_select" -v
```

Run one file:

```bash
pytest examples/test_real_geospatial_function.py -v
```

---

## How to choose between case, suite, and selector

Use this rule of thumb:

- use `geocase_case` when you want stable, explicit coverage,
- use `geocase_suite` when the repo already defines a meaningful group,
- use `geocase_select` when you want coverage by metadata traits rather than hardcoded IDs.

Start simple with explicit case IDs. Move to selectors when your test intent is about behavior categories rather than a fixed list.

---

## Helpful next reads

- [`docs/testing-your-function-with-geocase.md`](testing-your-function-with-geocase.md)
- [`docs/using-parameterized-tests.md`](using-parameterized-tests.md)
- [`docs/case-discovery.md`](case-discovery.md)
- [`docs/assertions-reference.md`](assertions-reference.md)
- [`docs/examples-index.md`](examples-index.md)
- [`docs/adding-a-case.md`](adding-a-case.md)
- [`docs/contributing/workflow.md`](contributing/workflow.md)

---

## Current project status

GeoCase 1.0.0 covers the core `pytest` workflow and a small public API, with 1701 passing
tests and 163 bundled cases. The metadata, catalog, runtime, assertions, loader, and
pytest plugin layers are complete.

The v1.0 compatibility promise covers **two surfaces only**: the pytest workflow (markers
and fixtures) and the `import geocase` public API. Everything else is internal and may
change in a minor release.

Deferred to v1.1, by decision rather than omission:
- Remote dataset transport — declared cases are discoverable but not fetchable
- Rotated/skewed affine transforms and southern-hemisphere UTM coverage
- A command-line interface

See [`docs/plans/development-plan.md`](https://github.com/farzinashouri/geocase/blob/main/docs/plans/development-plan.md) for the
current roadmap.
