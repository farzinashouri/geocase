# GeoCase

**Two pixels out of a hundred are NoData, and your mean elevation is off by 200 metres.**

Here is the code. It looks fine, it passes review, and it is wrong:

```python
def mean_elevation(array):
    return float(array.mean())
```

Point it at a GeoCase case that ships with the package:

```python
import pytest


@pytest.mark.geocase_case("geotiff_nodata_small")
def test_mean_elevation_ignores_nodata(geocase_case):
    array, _profile, nodata = geocase_case.read(1)
    valid = array[array != nodata]
    assert mean_elevation(array) == pytest.approx(float(valid.mean()), rel=0.01)
```

```
E   assert -152.8628387451172 == 48.07874298095703 ± 0.480787
```

The file carries an explicit `-9999` NoData sentinel in 2 of its 100 pixels. `array.mean()`
averages the sentinel in and reports **−152.9 m** for terrain whose real mean is **48.1 m**.
Nothing raises and nothing warns — the number is simply wrong, and it stays wrong all the way
into the report. The only thing that catches it is a test file that actually has NoData in it.

That is what GeoCase is: 166 curated vector, raster and NetCDF files, each one built around a
failure mode that survives code review.

Most of them are about **geometry, CRS and georeferencing conventions** — the assumptions a
codebase makes about where a pixel or a vertex actually is:

- a **rotated geotransform**, where the shortcut inverse matrix everyone writes is wrong, and
  wrong quietly;
- a **bottom-up raster** with a positive `e` term, read upside down without a single warning;
- **pixel-is-area versus pixel-is-point** anchoring, a half-pixel shift that survives review;
- geometry crossing the **antimeridian** and coming back as a ring around the globe, or a
  footprint reaching lon 180.22 that sends a tile request to a tile that does not exist;
- a **CRS mismatch** between two layers that overlay perfectly on screen;
- EPSG **axis order** flipping latitude and longitude;
- **NoData** averaged into a statistic, as above.

Radiometric conventions for Sentinel-1 and Sentinel-2 — scale factors, BOA offsets, dB
conversion — are one vertical inside that, machine-checked against
[`geofacts`](https://github.com/farzinashouri/geofacts). They are not the thesis.

If your codebase moves pixels and geometry around and reads them with plain GDAL, you are the
audience this corpus serves best.

### Works with plain GDAL

`case.primary_path` is an ordinary filesystem path. `gdal.Open` just works, and the base install
needs only `pydantic`, `pyyaml` and `geofacts` — no rasterio, no geopandas, no xarray:

```python
import geocase
from osgeo import gdal

case = geocase.load_case("rotated_two_islands")
ds = gdal.Open(str(case.primary_path))
print(ds.GetGeoTransform())
```

The extras exist for the convenience loaders (`case.load()`, `case.read()`), not for reading the
files. Enumerating, selecting and resolving cases needs no optional dependency at all.

The `georeferencing-conventions` suite is the shortest path from install to a real finding:

```python
@pytest.mark.geocase_suite("georeferencing-conventions")
def test_georeferencing(geocase) -> None:
    ...
```

The realistic alternative is not "no tests" — it is the `test_data/sample.tif` someone exported
once and the `numpy` arrays each test improvises. Those pass because they were chosen by the same
person who wrote the code, so they encode the same assumptions. GeoCase cases were not, and they
ship as a versioned dependency instead of a folder nobody remembers the provenance of. (They also
give a coding assistant something to reach for instead of inventing a fixture that agrees with
the bug.)

> Status: **1.0.0 is available on [PyPI](https://pypi.org/project/geocase/)** — `pip install geocase`. The compatibility promise covers two surfaces — the `pytest` workflow (fixtures and markers) and the `import geocase` public API. 166 bundled cases, 5.1 MB. Remote dataset transport is deferred to v1.1; see the [changelog](CHANGELOG.md).

## Quick Start

### 1) Install

For local development in this repo:

```bash
pip install -e ".[dev]"
```

There are two supported install shapes, and picking the right one matters.

**Greenfield** — no geospatial stack yet, let pip build one:

```bash
pip install "geocase[all]"
```

**You already have a working geo stack** — GDAL, geopandas, rasterio, whether from conda,
system packages or a `--system-site-packages` venv:

```bash
pip install geocase
```

Plain `geocase` is enough to enumerate, select and resolve every case, because `primary_path`
is just a path and you already have the readers. Use it. `[all]` re-resolves numpy and pandas
and can shadow or break a working stack — it is for greenfield environments only.

A conda-forge feedstock does not exist yet. When one does, installing from it
will not carry the extras, since bundling GDAL would make the conda package far
heavier than the PyPI equivalent:

```bash
conda install -c conda-forge geocase
```

GeoCase depends on [`geofacts`](https://github.com/farzinashouri/geofacts) at
runtime — a zero-dependency table of geospatial product facts (radiometric
constants, CRS conventions) that the raster presets are machine-checked
against. Everything else is optional and gated behind extras.

### 2) Write a test with GeoCase markers

```python
import pytest


@pytest.mark.geocase_case("dateline_crossing_polygon")
def test_vector_case_loads(geocase_case) -> None:
    gdf = geocase_case.load()
    assert geocase_case.id == "dateline_crossing_polygon"
    assert gdf.crs is not None


@pytest.mark.geocase_select(category="raster")
def test_all_raster_cases_have_pixels(geocase) -> None:
    data, _, _ = geocase.read(1)
    assert data.size > 0
```

### 3) Run tests

```bash
pytest -v
```

Run only GeoCase-marked tests:

```bash
pytest -m "geocase_case or geocase_suite or geocase_select" -v
```

## CI Jobs

This repository uses GitHub Actions, defined in `.github/workflows/`.

`ci.yml` runs on pushes to `main` and on pull requests:

- `catalog` — catalog integrity checks (`build_case_index.py` smoke check,
  `validate_catalog.py`, fixture and checksum gates, generated-page freshness)
- `tests` — the whole `tests/` directory on Python 3.11 and 3.14, reporting
  coverage (not gated)
- `lint` — `ruff format --check` and `ruff check` over `src` and `tests`
- `typecheck` — `mypy src`
- `docs` — `mkdocs build --strict`

`release.yml` runs only on `vX.Y.Z` tags; see
[Releasing](docs/contributing/releasing.md).

Local equivalents:

```bash
python scripts/build_case_index.py --check
python scripts/validate_catalog.py

python -m pytest tests -q
ruff format --check src tests && ruff check src tests
```

## Core Concepts

- `@pytest.mark.geocase_case(...)`: select explicit case IDs.
- `@pytest.mark.geocase_suite(...)`: use named suites.
- `@pytest.mark.geocase_select(...)`: select by metadata (`category`, `format`, `geometry_type`, `tags`, `risk_types_any`, etc.).
- `geocase`: auto-parameterized fixture (one invocation per resolved case).
- `geocase_case`: convenience fixture for exactly one resolved case.
- CLI tooling is optional; the primary workflow is plain `pytest`.

If a GeoCase marker is missing, resolves no cases, refers to an unknown suite, or `geocase_case` resolves more than one case, the plugin now raises a focused `pytest.UsageError` that explains what to fix.

## Learn More

- [`docs/getting-started.md`](docs/getting-started.md)
- [`docs/testing-your-function-with-geocase.md`](docs/testing-your-function-with-geocase.md)
- [`docs/case-discovery.md`](docs/case-discovery.md)
- [`docs/assertions-reference.md`](docs/assertions-reference.md)
- [`docs/examples-index.md`](docs/examples-index.md)
- [`docs/benchmark/quickstart.md`](docs/benchmark/quickstart.md) — the LLM benchmark built on the catalog. **Experimental:** not part of the v1.0 compatibility promise and not published to the docs site.
- [`src/geocase/raster/`](src/geocase/raster/) — `geocase.raster`, a dependency-free raster primitive plus Sentinel-1/2 presets
- [`docs/plans/development-plan.md`](docs/plans/development-plan.md)
- [`docs/contributing/workflow.md`](docs/contributing/workflow.md)
- [`docs/design/case-recommendation-service.md`](docs/design/case-recommendation-service.md)
