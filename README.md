# GeoCase

GeoCase is a geospatial testing toolkit and case catalog for realistic, reproducible `pytest` tests.

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

## Core Concepts

- `@pytest.mark.geocase_case(...)`: select explicit case IDs.
- `@pytest.mark.geocase_suite(...)`: use named suites.
- `@pytest.mark.geocase_select(...)`: select by metadata (`category`, `format`, `geometry_type`, `tags`, `risk_types_any`, etc.).
- `geocase`: auto-parameterized fixture (one invocation per resolved case).
- `geocase_case`: convenience fixture for exactly one resolved case.
- CLI tooling is optional; the primary workflow is plain `pytest`.

## Learn More

- `docs/development-plan.md`
- `docs/workflow.md`
- `docs/testing-your-function-with-geocase.md`
- `docs/using-parameterized-tests.md`
- `docs/case-recommendation-service.md`