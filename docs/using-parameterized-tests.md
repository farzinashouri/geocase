# Using parameterized tests

GeoCase is designed to make metadata-driven parameterization natural.

## Select by metadata

```python
import pytest
from geocase import select_cases

@pytest.mark.parametrize(
    "case",
    select_cases(category="vector", test_tier="unit"),
    ids=lambda c: c.id,
)
def test_vector_cases_load(case):
    gdf = case.load()
    assert len(gdf) > 0

## Select by risk type
import pytest
from geocase import select_cases

@pytest.mark.parametrize(
    "case",
    select_cases(risk_type="bbox_misinterpretation"),
    ids=lambda c: c.id,
)
def test_bounds_handling(case):
    data = case.load()
    assert data is not None

## Use a named suite

import pytest
from geocase import suite

@pytest.mark.parametrize(
    "case",
    suite("core-vector"),
    ids=lambda c: c.id,
)
def test_core_vector_suite(case):
    gdf = case.load()
    assert gdf is not None

## Combine GeoCase with reusable assertions
import pytest
from geocase import select_cases
from geocase.assertions import assert_has_crs

@pytest.mark.parametrize(
    "case",
    select_cases(category="vector", test_tier="unit"),
    ids=lambda c: c.id,
)
def test_vector_cases_have_crs(case):
    gdf = case.load()
    assert_has_crs(gdf)