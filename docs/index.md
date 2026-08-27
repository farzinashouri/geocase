---
description: "GeoCase is a pytest plugin and case catalog: 135 curated geospatial test cases covering NoData, antimeridian crossing, CRS mismatch and axis order."
---

# GeoCase

GeoCase is an open geospatial testing toolkit and case catalog for realistic, reproducible, parameterized tests.

> Status: **1.0.0rc1 is available on [PyPI](https://pypi.org/project/geocase/)**; this repository contains the next release candidate (`1.0.0rc2`). The compatibility promise covers two surfaces — the `pytest` workflow (fixtures and markers) and the `import geocase` public API. 135 bundled cases, 2.1 MB. Remote dataset transport is deferred to v1.1; see the [changelog](https://github.com/farzinashouri/geocase/blob/main/CHANGELOG.md).

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

## Start here

- New users: [`getting-started.md`](getting-started.md)
- Testing a real function: [`testing-your-function-with-geocase.md`](testing-your-function-with-geocase.md)
- Finding cases by metadata: [`case-discovery.md`](case-discovery.md)
- Reusable checks: [`assertions-reference.md`](assertions-reference.md)
- Example tests: [`examples-index.md`](examples-index.md)
- Adding new cases: [`adding-a-case.md`](adding-a-case.md)

## Documentation map

Each folder under `docs/` holds one kind of document:

- User guides at the top level explain how to select cases, write tests, and use GeoCase day to day.
- `docs/contributing/` — how to work on GeoCase: workflow, conventions, and maintainer practices.
- `docs/plans/` — what is planned and in what order, including the [roadmap](plans/development-plan.md). Superseded plans stay in `docs/plans/archive/` as an implementation log.
- `docs/design/` — future-facing designs that are not part of the core workflow.
- `docs/reference/` — descriptive maps of the project as it exists today, such as the [codebase summary](reference/codebase-summary.md).
- `docs/_generated/` — pages built by scripts and gated in CI; never edit them by hand.

## Example

```python
import pytest
import geocase

@pytest.mark.parametrize(
    "meta",
    geocase.list_cases(category="vector", test_tier="unit"),
    ids=lambda m: m.id,
)
def test_vector_loading(meta):
    if not meta.assertions.expect_loadable:
        pytest.skip(f"{meta.id} is a case that should not load cleanly")
    gdf = geocase.load_case(meta.id).load()
    assert len(gdf) > 0
```

`list_cases()` returns metadata, and `load_case()` turns a case id into
something loadable. The `expect_loadable` check matters because some cases
exist precisely to break loaders. See
[`using-parameterized-tests.md`](using-parameterized-tests.md) for both points.

## Next reads

- [`getting-started.md`](getting-started.md)
- [`using-parameterized-tests.md`](using-parameterized-tests.md)
- [`testing-your-function-with-geocase.md`](testing-your-function-with-geocase.md)
- [`case-discovery.md`](case-discovery.md)
