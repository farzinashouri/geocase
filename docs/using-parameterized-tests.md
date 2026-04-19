# Using parameterized tests

GeoCase is designed to make metadata-driven parameterization natural.

If you want help choosing filters, see [`case-discovery.md`](case-discovery.md).

---

## Select by metadata

Use `select_cases(...)` when you want to resolve a list of matching cases directly in `pytest.mark.parametrize(...)`.

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
```

This pattern is useful when your test intent is broad, such as “all unit-tier vector cases should load”.

---

## Select by risk type

Risk types let you group by likely bug or failure mode.

```python
import pytest
from geocase import select_cases


@pytest.mark.parametrize(
    "case",
    select_cases(risk_types_any=["bbox_misinterpretation"]),
    ids=lambda c: c.id,
)
def test_bounds_handling(case):
    data = case.load()
    assert data is not None
```

---

## Use a named suite

Use `suite(...)` when maintainers already define the group you want.

```python
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
```

Suites are a good fit for stable CI coverage because they avoid repeating selector logic in many test files.

---

## Combine GeoCase with reusable assertions

GeoCase works well with the helpers in `geocase.assertions`.

```python
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
```

See [`assertions-reference.md`](assertions-reference.md) for a compact list of the available helpers.

---

## When to use `select_cases(...)` vs plugin markers

Both approaches are valid:

- use `select_cases(...)` when you want explicit `pytest.mark.parametrize(...)` in the test body,
- use `@pytest.mark.geocase_select(...)` when you want GeoCase's plugin to handle parameterization for you,
- use `@pytest.mark.geocase_suite(...)` when you want a curated named group,
- use `@pytest.mark.geocase_case(...)` when you want exact case IDs.

---

## Related docs

- [`getting-started.md`](getting-started.md)
- [`case-discovery.md`](case-discovery.md)
- [`assertions-reference.md`](assertions-reference.md)
- [`testing-your-function-with-geocase.md`](testing-your-function-with-geocase.md)