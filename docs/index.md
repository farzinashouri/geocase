# GeoCase

GeoCase is an open geospatial testing toolkit and dataset catalog for realistic, reproducible, parameterized tests.

Most spatial tests use overly simple geometries or ad hoc local files. GeoCase provides a curated catalog of compact but behaviorally meaningful cases that can be selected into pytest suites by metadata such as category, risk type, test tier, format, and storage class.

## Core ideas

- **Cases, not random files**  
  Every sample is a self-contained test case with metadata describing why it exists.

- **Parameterized testing first**  
  GeoCase is designed to work naturally with `pytest.mark.parametrize(...)`.

- **Metadata-driven selection**  
  Users select cases by tags, risk types, categories, and suites rather than hardcoding paths everywhere.

- **Small bundled core, larger optional catalog**  
  Tiny core cases ship with the package. Larger realistic samples can be fetched on demand.

## Example

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