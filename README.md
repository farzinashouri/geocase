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

That is what GeoCase is: 153 curated vector, raster and NetCDF files, each one built around a
failure mode that survives code review. **NoData** averaged into a statistic; geometry crossing
the **antimeridian** and coming back as a ring around the globe; a **CRS mismatch** between two
layers that overlay perfectly on screen; EPSG **axis order** flipping latitude and longitude.

The realistic alternative is not "no tests" — it is the `test_data/sample.tif` someone exported
once and the `numpy` arrays each test improvises. Those pass because they were chosen by the same
person who wrote the code, so they encode the same assumptions. GeoCase cases were not, and they
ship as a versioned dependency instead of a folder nobody remembers the provenance of. (They also
give a coding assistant something to reach for instead of inventing a fixture that agrees with
the bug.)

> Status: **1.0.0rc1 is available on [PyPI](https://pypi.org/project/geocase/)**; this repository contains the next release candidate (`1.0.0rc2`). The compatibility promise covers two surfaces — the `pytest` workflow (fixtures and markers) and the `import geocase` public API. 153 bundled cases, 5.1 MB. Remote dataset transport is deferred to v1.1; see the [changelog](CHANGELOG.md).

## Quick Start

### 1) Install

For local development in this repo:

```bash
pip install -e ".[dev]"
```

Install the latest published release from PyPI:

```bash
pip install "geocase[all]"
```

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
- [`docs/benchmark/quickstart.md`](docs/benchmark/quickstart.md) — the LLM benchmark built on the catalog
- [`src/geocase/raster/`](src/geocase/raster/) — `geocase.raster`, a dependency-free raster primitive plus Sentinel-1/2 presets
- [`docs/plans/development-plan.md`](docs/plans/development-plan.md)
- [`docs/contributing/workflow.md`](docs/contributing/workflow.md)
- [`docs/design/case-recommendation-service.md`](docs/design/case-recommendation-service.md)
