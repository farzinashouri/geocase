# Using parameterized tests

GeoCase is designed to make metadata-driven parameterization natural.

If you want help choosing filters, see [`case-discovery.md`](case-discovery.md).

---

## Metadata and cases are two different things

Every example below uses two functions, and it is worth knowing why:

- `geocase.list_cases(...)` returns **metadata** — `CaseMetadata` objects
  describing what each case is. Reading it opens no files and imports no
  geospatial library.
- `geocase.load_case(case_id)` returns a **case** — a `VectorCase`,
  `RasterCase`, or `NetCDFCase` you can call `.load()` or `.open()` on.

So you filter on metadata, then load the ones you selected. Metadata objects
have no `.load()` method; that separation is deliberate, and it keeps
collection cheap even when a filter matches most of the catalog.

The plugin's `geocase` fixture yields the loaded case directly, because by then
selection has already happened.

---

## Select by metadata

Use `list_cases(...)` when you want to resolve matching cases directly in `pytest.mark.parametrize(...)`.

```python
import pytest
import geocase


@pytest.mark.parametrize(
    "meta",
    geocase.list_cases(category="vector", test_tier="unit"),
    ids=lambda m: m.id,
)
def test_vector_cases_load(meta):
    if not meta.assertions.expect_loadable:
        pytest.skip(f"{meta.id} is a case that should not load cleanly")
    gdf = geocase.load_case(meta.id).load()
    assert len(gdf) > 0
```

This pattern is useful when your test intent is broad, such as “all unit-tier vector cases should load”.

**Mind the cases that are supposed to fail.** A broad filter will sweep in
cases built to break loaders — `unclosed_ring_polygon` is one of the 103
unit-tier vector cases, and loading it raises a `GEOSException` by design.
`meta.assertions.expect_loadable` tells you which those are, so a broad test
can skip them rather than report a failure GeoCase intended.

---

## Select by risk type

Risk types let you group by likely bug or failure mode.

```python
import pytest
import geocase


@pytest.mark.parametrize(
    "meta",
    geocase.list_cases(risk_types_any=["bbox_misinterpretation"]),
    ids=lambda m: m.id,
)
def test_bounds_handling(meta):
    data = geocase.load_case(meta.id).load()
    assert data is not None
```

---

## Use a named suite

Use `get_suite(...)` when maintainers already define the group you want. It returns a
`ResolvedSuite`, whose `.cases` are metadata like `list_cases()` returns.

```python
import pytest
import geocase


@pytest.mark.parametrize(
    "meta",
    geocase.get_suite("core-vector").cases,
    ids=lambda m: m.id,
)
def test_core_vector_suite(meta):
    gdf = geocase.load_case(meta.id).load()
    assert gdf is not None
```

Suites are a good fit for stable CI coverage because they avoid repeating selector logic in many test files.

Use `geocase.list_suites()` to see every suite the package ships.

---

## Combine GeoCase with reusable assertions

GeoCase works well with the helpers in `geocase.assertions`.

```python
import pytest
import geocase
from geocase.assertions import assert_has_crs


@pytest.mark.parametrize(
    "meta",
    geocase.list_cases(category="vector", test_tier="unit"),
    ids=lambda m: m.id,
)
def test_vector_cases_have_crs(meta):
    if not meta.assertions.expect_loadable:
        pytest.skip(f"{meta.id} is a case that should not load cleanly")
    gdf = geocase.load_case(meta.id).load()
    assert_has_crs(gdf)
```

See [`assertions-reference.md`](assertions-reference.md) for a compact list of the available helpers.

---

## Inspect a single case

`show_case(...)` prints a readable summary — useful when a parametrized run fails and
you want to know what the case actually is.

```python
>>> import geocase
>>> print(geocase.show_case("dateline_crossing_polygon"))
```

---

## When to use `list_cases(...)` vs plugin markers

Both approaches are valid:

- use `list_cases(...)` when you want explicit `pytest.mark.parametrize(...)` in the test body,
- use `@pytest.mark.geocase_select(...)` when you want GeoCase's plugin to handle parameterization for you,
- use `@pytest.mark.geocase_suite(...)` when you want a curated named group,
- use `@pytest.mark.geocase_case(...)` when you want exact case IDs.

With the markers, the `geocase` fixture hands your test a loaded case, so there is no
`load_case(...)` step to write.

---

## Related docs

- [`getting-started.md`](getting-started.md)
- [`case-discovery.md`](case-discovery.md)
- [`assertions-reference.md`](assertions-reference.md)
- [`testing-your-function-with-geocase.md`](testing-your-function-with-geocase.md)