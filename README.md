# GeoCase

GeoCase is a geospatial testing toolkit and case catalog for realistic, reproducible `pytest` tests.

> Status: **1.0**. The compatibility promise covers two surfaces — the `pytest` workflow (fixtures and markers) and the `import geocase` public API. 134 bundled cases, 4.2 MB. Remote dataset transport is deferred to v1.1; see the [changelog](CHANGELOG.md).

The main goal is simple: use plain `pytest` with a few GeoCase fixtures and markers to run your geospatial code against curated edge cases.

Instead of hand-picking random sample files, you select packaged cases (vector, raster, NetCDF) and run your function against scenarios such as CRS issues, dateline crossing, topology problems, and NoData behavior.

## Quick Start

### 1) Install

For local development in this repo:

```bash
pip install -e ".[dev]"
```

When a package release is published, install from the package index:

```bash
pip install "geocase[all]"
```

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

This repository uses GitLab CI with job definitions in `ci/` and includes from
`.gitlab-ci.yml`.

- `catalog_validation` (`ci/catalog-validation.yml`)
    - runs catalog integrity checks (`build_case_index.py` generation smoke check and `validate_catalog.py`)
- `tests` (`ci/tests.yml`)
    - runs on push and merge request pipelines, on Python 3.11 and 3.14
    - executes the whole `tests/` directory and reports coverage (not gated)
- `lint` (`ci/lint.yml`)
    - runs on push and merge request pipelines
    - `ruff format --check` and `ruff check` over `src` and `tests`

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
- [`docs/contributing/development-plan.md`](docs/contributing/development-plan.md)
- [`docs/contributing/workflow.md`](docs/contributing/workflow.md)
- [`docs/design/case-recommendation-service.md`](docs/design/case-recommendation-service.md)