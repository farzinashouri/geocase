# GeoCase

GeoCase is an open geospatial testing toolkit and dataset catalog for realistic, reproducible, parameterized tests.

Instead of relying on simplistic geometries or ad hoc local sample files, GeoCase provides curated compact cases for vector, raster, and NetCDF workflows. Each case includes metadata describing what testing risk it represents, such as CRS mismatch, topology issues, dateline crossing, nodata handling, or encoding problems.

## Main idea

GeoCase is designed around a catalog of cases that can be selected directly into pytest parameterization.

```python
import pytest
from geocase import select_cases

@pytest.mark.parametrize(
    "case",
    select_cases(category="vector", test_tier="unit"),
    ids=lambda c: c.id,
)
def test_vector_loading(case):
    gdf = case.load()
    assert len(gdf) > 0