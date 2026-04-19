# Case Discovery

This guide shows how to find GeoCase cases by metadata instead of memorizing individual case IDs.

GeoCase cases are designed to be discovered by intent:

- what data type you need,
- what geometry type you care about,
- what bug or risk you want to expose,
- what suite already groups relevant cases.

---

## Start with the broadest filter

The most common first filter is `category`:

```python
import pytest


@pytest.mark.geocase_select(category="vector")
def test_all_vectors(geocase) -> None:
    gdf = geocase.load()
    assert len(gdf) > 0
```

Use:

- `category="vector"` for GeoPandas-based cases,
- `category="raster"` for raster cases,
- `category="netcdf"` for xarray/NetCDF cases.

---

## Narrow by geometry type

For vector cases, `geometry_type` is often the next best filter.

```python
@pytest.mark.geocase_select(category="vector", geometry_type="Polygon")
def test_polygon_cases(geocase) -> None:
    gdf = geocase.load()
    assert len(gdf) > 0
```

Common values include:

- `Point`
- `MultiPoint`
- `LineString`
- `MultiLineString`
- `Polygon`
- `MultiPolygon`
- `GeometryCollection`

---

## Use tags for scenario discovery

Tags describe the scenario a case is meant to expose.

Examples:

- `dateline`
- `antimeridian`
- `utm`
- `nodata`
- `invalid`
- `hole`
- `encoding`
- `precision`

Use `tags_any` when any one of the listed tags is enough:

```python
@pytest.mark.geocase_select(category="vector", tags_any=["dateline", "antimeridian"])
def test_wrapped_longitude_cases(geocase) -> None:
    gdf = geocase.load()
    assert len(gdf) > 0
```

Use `tags_all` when you want cases that satisfy all listed traits:

```python
@pytest.mark.geocase_select(category="vector", tags_all=["polygon", "invalid"])
def test_invalid_polygon_cases(geocase) -> None:
    gdf = geocase.load()
    assert len(gdf) > 0
```

---

## Use risk types for bug-oriented selection

`risk_types` are useful when your test is about failure modes rather than shape or format.

Examples:

- `coordinate_wrapping`
- `topology_breakage`
- `bbox_misinterpretation`
- `nan_propagation`
- `incorrect_statistics`

```python
@pytest.mark.geocase_select(risk_types_any=["coordinate_wrapping"])
def test_coordinate_wrapping_risks(geocase) -> None:
    assert "coordinate_wrapping" in geocase.metadata.risk_types
```

A good rule of thumb:

- use `tags` for scenario labels,
- use `risk_types` for the kind of bug you expect.

---

## Filter by format

If you need to exercise file-format-specific behavior, use `format`.

```python
@pytest.mark.geocase_select(category="vector", format="GPKG")
def test_gpkg_cases(geocase) -> None:
    gdf = geocase.load()
    assert len(gdf) > 0
```

Typical examples:

- `GeoJSON`
- `GPKG`
- `Shapefile`
- `Parquet`
- `GeoTIFF`
- `NetCDF`

Use format filtering when the format itself matters, such as:

- shapefile field truncation,
- GeoJSON precision loss,
- GPKG null geometry behavior.

---

## Use suites when the grouping already exists

Suites are named, curated groups of cases.

```python
import pytest


@pytest.mark.geocase_suite("core-vector")
def test_core_vector_suite(geocase) -> None:
    gdf = geocase.load()
    assert len(gdf) > 0
```

Use a suite when:

- the repo already defines the grouping you want,
- you want a stable maintainer-curated set,
- you do not want to repeat selector logic in every test.

Use selectors when your intent is more specific or temporary.

---

## Decision guide

| If you want... | Use... |
|---|---|
| One specific known case | `@pytest.mark.geocase_case(...)` |
| A curated named group | `@pytest.mark.geocase_suite(...)` |
| A metadata-defined family of cases | `@pytest.mark.geocase_select(...)` |
| Format-specific behavior | `format=...` |
| A geometry family | `geometry_type=...` |
| A bug category | `risk_types_any=[...]` |
| A scenario label | `tags_any=[...]` or `tags_all=[...]` |

---

## Good discovery patterns

### Start broad, then narrow

```python
@pytest.mark.geocase_select(category="vector", geometry_type="Polygon", tags_any=["invalid"])
def test_invalid_polygon_behavior(geocase) -> None:
    geom = geocase.load()
    assert len(geom) > 0
```

### Prefer suites for stable CI coverage

```python
@pytest.mark.geocase_suite("core-vector")
def test_fast_smoke_suite(geocase) -> None:
    assert geocase.id
```

### Prefer selectors for behavior-driven tests

```python
@pytest.mark.geocase_select(category="raster", tags_any=["nodata"])
def test_nodata_behavior(geocase) -> None:
    data, _, _ = geocase.read(1)
    assert data.size > 0
```

---

## Related docs

- [`getting-started.md`](getting-started.md)
- [`using-parameterized-tests.md`](using-parameterized-tests.md)
- [`testing-your-function-with-geocase.md`](testing-your-function-with-geocase.md)
- [`adding-a-case.md`](adding-a-case.md)
