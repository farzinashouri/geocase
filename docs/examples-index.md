# Examples Index

The `examples/` directory shows how to use GeoCase in realistic test workflows.

Use this page as a quick map before diving into the files.

---

## Plugin and selector workflows

### `examples/test_parametrized_vector.py`

Shows metadata-driven vector selection in normal `pytest` tests.

### `examples/test_dateline_suite.py`

Shows how to use a focused suite for dateline and antimeridian behavior.

### `examples/test_crs_edge_cases.py`

Shows case-driven tests around CRS assumptions and reprojection scenarios.

---

## Raster workflows

### `examples/test_raster_nodata_suite.py`

Shows raster tests focused on NoData handling and related expectations.

### `examples/test_gdal_footprint.py`

Shows GDAL/raster footprint testing patterns with GeoCase data.

### `examples/gdal_footprint.py`

Contains supporting logic for footprint-oriented examples.

---

## Differential workflows

### `examples/test_differential_pyogrio.py`

Reads every openable vector case twice through pyogrio — once on its numpy path,
once on its Arrow path — and reports the disagreements. This is the mode that
found real defects in pyogrio and GDAL; see
[Differential testing](differential-testing.md). Needs `pyogrio` and `pyarrow`,
and skips without them.

---

## Real-function examples

### `examples/test_real_geospatial_function.py`

Shows how to exercise a realistic geospatial function against curated cases.

### `examples/real_geospatial_function.py`

Contains the function under test used by the example suite.

---

## Interview-style training examples

### `examples/test_easy_geospatial_interview_questions_simple.py`

Covers simple implementations that are intentionally naive.

### `examples/test_easy_geospatial_interview_questions_perfect.py`

Covers more robust `*_perfect` implementations against the same classes of cases.

### `examples/_easy_geospatial_interview_test_support.py`

Provides the shared fixture-loading and test support helpers behind the interview examples.

### `examples/interview_questions/`

Contains the interview-style implementation modules themselves.

---

## How to choose an example

| If you want to learn... | Start with... |
|---|---|
| Basic case selection | `examples/test_parametrized_vector.py` |
| CRS or dateline behavior | `examples/test_crs_edge_cases.py` or `examples/test_dateline_suite.py` |
| Raster NoData patterns | `examples/test_raster_nodata_suite.py` |
| Realistic function testing | `examples/test_real_geospatial_function.py` |
| Finding bugs without declaring expectations | `examples/test_differential_pyogrio.py` |
| Training / educational contrasts | `examples/test_easy_geospatial_interview_questions_perfect.py` |

---

## Related docs

- [`getting-started.md`](getting-started.md)
- [`testing-your-function-with-geocase.md`](testing-your-function-with-geocase.md)
- [`using-parameterized-tests.md`](using-parameterized-tests.md)
- [`case-discovery.md`](case-discovery.md)
