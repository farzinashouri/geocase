# Testing Edge Cases

> Consolidated from historical docs: `invalid-geometry-testing-strategy.md`, `adding-invalid-geometry-edge-cases.md`, `test-parametrization-filtering.md`

This document covers the strategy for testing invalid and edge-case geometries in GeoCase.

---

## Overview

### The Problem

**Silent acceptance of invalid data that produces wrong output is the worst outcome** — users don't know their results are garbage. A good geospatial function should either:

1. **Explicitly reject** invalid input with a clear error message, or
2. **Repair and warn** if repair is appropriate for that function

### Goals

1. Ensure all `_perfect` functions explicitly reject or handle invalid geometry
2. Document which `simple` functions silently fail (educational material)
3. Standardize error messages across the codebase
4. Expand invalid geometry fixture coverage

---

## Test Parametrization Filtering

### Problem Statement

When adding special cases like `empty_geometry_gpkg` (which contains NULL and EMPTY geometries), standard parametrized tests that select all Point/Polygon cases will include these problematic geometries. Functions like `reproject_point` or `cluster_points` expect valid geometry objects with `.x`/`.y` attributes, causing test failures.

### Solution: Dual Parameter Sets

Create separate parameter sets for valid-only vs all cases:

```python
def _is_valid_geometry_case(meta: Any) -> bool:
    """Return True if case is expected to have valid, non-empty geometry.
    
    Checks:
    1. assertions.expect_valid_geometry is not False
    2. Tags do not include 'invalid' or 'empty'
    """
    assertions = getattr(meta, 'assertions', None)
    if assertions is not None:
        if getattr(assertions, 'expect_valid_geometry', None) is False:
            return False
    
    tags = set(getattr(meta, 'tags', []) or [])
    if 'invalid' in tags or 'empty' in tags:
        return False
    
    return True

# Valid-only params (default for standard tests)
_VECTOR_POLYGON_CASE_PARAMS = build_case_params(
    _select_case_metadata(
        category="vector",
        geometry_type="Polygon",
        extra_filter=_is_valid_geometry_case,
    ),
    load_case=_load_case,
)

# All cases params (for tests that handle invalid/empty)
_VECTOR_POLYGON_ALL_PARAMS = build_case_params(
    _select_case_metadata(category="vector", geometry_type="Polygon"),
    load_case=_load_case,
)
```

### Case Metadata Requirements

Cases with invalid or empty geometries should be marked appropriately:

```yaml
# Use assertions (recommended)
assertions:
  expect_valid_geometry: false

# And/or use tags
tags:
  - invalid
  - self_intersection
```

### Tests That Need `_ALL` Params

| Test Function | Reason |
|--------------|--------|
| `test_fix_geometry_handles_all_polygon_cases` | Repair function expects invalid input |
| `test_validate_polygon_geometry_handles_all_polygon_cases` | Validation should flag invalid |
| `test_area_m2_handles_all_polygon_cases` | Should reject/handle invalid |
| `test_dissolve_polygons_handles_all_polygon_cases` | Should handle repair before dissolve |

---

## Invalid Geometry Params

For explicit rejection tests, filter for invalid geometry cases only:

```python
def _is_invalid_geometry_case(meta: Any) -> bool:
    """Return True if case is expected to have invalid geometry."""
    assertions = getattr(meta, "assertions", None)
    if assertions and getattr(assertions, "expect_valid_geometry", None) is False:
        return True
    tags = getattr(meta, "tags", []) or []
    return "invalid" in tags

_INVALID_POLYGON_PARAMS = build_case_params(
    _select_case_metadata(
        category="vector",
        geometry_type="Polygon",
        extra_filter=_is_invalid_geometry_case,
    ),
    load_case=_load_case,
)
```

---

## Parametrized "Must Reject Invalid" Tests

For each `_perfect` function, add tests that verify proper rejection:

```python
@pytest.mark.parametrize("geocase", _INVALID_POLYGON_PARAMS)
def test_area_m2_perfect_rejects_invalid_geometries(geocase):
    """Verify area_m2_perfect explicitly rejects all invalid polygon cases."""
    geom = _load_selected_geometry(geocase)
    
    # Skip if geometry was auto-repaired on load (e.g., unclosed rings)
    if geom.is_valid:
        pytest.skip("Geometry was auto-repaired on load")
    
    with pytest.raises(ValueError, match="invalid|Invalid"):
        area_m2_perfect(geom)
```

---

## Standard Error Message Pattern

All `_perfect` functions should raise `ValueError` with consistent messages:

```python
def some_function_perfect(geom):
    if geom is None:
        raise TypeError("geom must not be None")
    if geom.is_empty:
        raise ValueError("geom must not be empty")
    if not geom.is_valid:
        raise ValueError(
            f"Invalid geometry: {explain_validity(geom)}. "
            "Use shapely.make_valid() to repair before processing."
        )
    # ... rest of function
```

---

## Classic Invalid Geometry Edge Cases

These edge cases represent common real-world data quality issues:

| Edge Case | Problem | Why It Breaks Things |
|-----------|---------|---------------------|
| **Unclosed Ring** | Polygon ring missing closing coordinate | Strict parsers reject; others silently accept |
| **Null Island** | Point at (0, 0) | Usually indicates failed geocoding |
| **Out-of-Bounds Coordinates** | Lat > 90° or Lon > 180° | Spatial indexes fail; often lat/lon swap |
| **Self-Intersecting Polygon** | Bow-tie or figure-8 shape | Many operations produce wrong results |
| **Spike Invalid Polygon** | Degenerate spike in outline | Area calculations fail |

### Example Case: Null Island Point

```yaml
id: null_island_point
title: Null Island Point
description: >
  A point at (0, 0) — almost always indicates a failed geocoding operation.
category: vector
format: GeoJSON
test_tier: unit
size_class: tiny
storage_class: bundled

tags:
  - vector
  - point
  - invalid
  - null_island
  - geocoding_failure
  - data_quality

risk_types:
  - geocoding_failure
  - silent_bad_data

assertions:
  expect_loadable: true
  expect_valid_geometry: false
  expected_epsg: 4326

params:
  is_null_island: true
  likely_geocoding_failure: true
```

### Example Case: Out-of-Bounds Coordinates

```yaml
id: out_of_bounds_coordinates
title: Out-of-Bounds / Invalid Coordinates
description: >
  A point with latitude exceeding the valid range (100° instead of max 90°).
  Typically indicates a lat/lon coordinate swap.
category: vector
format: GeoJSON

tags:
  - vector
  - point
  - invalid
  - out_of_bounds
  - coordinate_error
  - lat_lon_swap

risk_types:
  - coordinate_range_error
  - lat_lon_swap
  - spatial_index_failure

assertions:
  expect_loadable: true
  expect_valid_geometry: false

params:
  is_valid: false
  coordinate_error_type: out_of_bounds
  latitude_in_file: 100.0
```

---

## Invalid Geometry Coverage Gaps

| Geometry Type | Existing Invalid Cases | Needed |
|---------------|----------------------|--------|
| Point | `null_island_point`, `out_of_bounds_coordinates` | NaN coordinates |
| LineString | `degenerate_but_parseable_line` | `zero_length_line` |
| Polygon | `self_intersecting_polygon`, `spike_invalid_polygon`, `unclosed_ring_polygon` | `hole_outside_shell` |
| MultiPolygon | None | `overlapping_polygons`, `invalid_component` |

---

## Test Matrix

Each `_perfect` function should be tested against all relevant invalid cases:

| Function | Invalid Polygon | Invalid Point | Invalid LineString |
|----------|----------------|---------------|-------------------|
| `area_m2_perfect` | ✓ Reject | N/A | N/A |
| `centroid_perfect` | ✓ Reject | ✓ Reject | ✓ Reject |
| `buffer_perfect` | ✓ Reject | ✓ Reject | ✓ Reject |
| `repair_geometry_perfect` | ✓ Accept & Fix | ✓ Accept & Fix | ✓ Accept & Fix |
| `validate_geometry_perfect` | ✓ Return errors | ✓ Return errors | ✓ Return errors |

---

## Design Decisions

### Repair vs Reject?

**Decision**: Reject by default. Reasons:
- Explicit is better than implicit
- User should know their input was invalid
- Auto-repair may not produce intended geometry
- Add separate `*_with_repair` variants if needed

### Metadata Declares Intent

| Criterion | Excludes From Standard Tests |
|-----------|------------------------------|
| `assertions.expect_valid_geometry: false` | ✅ Yes |
| Tag `invalid` | ✅ Yes |
| Tag `empty` | ✅ Yes |
| Runtime `geom.is_valid == False` | ❌ No (use metadata) |

The key principle: **metadata declares intent, not runtime inspection**. This keeps test parametrization fast and predictable.

---

## Implementation Checklist

- [x] Add `_is_valid_geometry_case` filter function
- [x] Add `_is_invalid_geometry_case` filter function
- [x] Create `_INVALID_POLYGON_PARAMS`, `_INVALID_POINT_PARAMS`, `_INVALID_LINESTRING_PARAMS`
- [x] Create `_VECTOR_*_ALL_PARAMS` for tests handling invalid/empty
- [x] Add "must reject" tests for `_perfect` functions
- [ ] Add missing invalid LineString fixtures
- [ ] Add missing invalid MultiPolygon fixtures
- [ ] Add NaN/Inf coordinate fixtures (future)
