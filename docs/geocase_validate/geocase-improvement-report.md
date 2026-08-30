# geocase 1.0.0rc2 — findings from a validation run against pyogrio

## What this was

A single question: does geocase surface defects that a hand-written test suite would
miss? To answer it, geocase's vector corpus was run against a from-source build of
pyogrio (GDAL 3.13.3) with a differential harness — every case read twice, once through
pyogrio's numpy path and once through its Arrow path, results compared — plus invariant
probes over `skip_features` / `max_features` / `fids` / `columns` / `bbox` / `mask` and
a write-read round-trip across four drivers.

## Verdict

**Worth shipping.** The run found two real defects in a mature, widely-used library:

1. A crash in `pyogrio.read_dataframe(fid_as_index=True, use_arrow=True)` — the FID
   column and a regular field collide by name in the Arrow schema, and pandas rejects
   the resulting 2-D index selection. Patched and accepted into a regression test.
2. A GPKG spatial-filter divergence where pyogrio's Arrow path returns a NULL-geometry
   feature that the non-Arrow path, and GDAL's own `ogrinfo -spat`, exclude. Traced into
   GDAL's `GetArrowStream`; filed upstream.

Both came from cases built around a **named failure mode** — `dateline_chain_cluster`
(three points straddling the antimeridian, whose integer `id` property happened to trip
GDAL's FID promotion) and `empty_geometry_gpkg` (a NULL geometry alongside a
`POINT EMPTY`). Neither came from the ~60 `*_baseline` files.

That distribution is the most important thing in this report, and it cuts both ways:
`risk_types` is what made the corpus useful, and the baselines contributed nothing but
runtime. If you have to choose where to spend curation effort, the evidence says spend
it on more failure modes rather than more format coverage of clean data.

The single strongest argument for geocase, worth putting in the README: the crash it
found **reduces to eight lines of stdlib `json`**. A curated corpus led to a defect whose
final repro needs no geocase install at all. That is exactly what a test corpus is for —
it does not need to be a permanent dependency of the projects it helps.

---

## Reliability issues

Ordered by how much each one costs a consumer.

### 1. 19 of 104 vector cases cannot be opened by an OGR-based consumer

```
total vector: 104   readable: 84   failed: 20
failures by format: WKB 6, WKT 6, Parquet 3, Feather 2, GeoArrow 1, Arrow 1, GeoJSON 1
```

Two distinct causes, which matters because they need different fixes, plus one case that
is failing on purpose:

- **12 cases are not datasets at all.** The `.wkb` and `.wkt` cases are bare geometry
  blobs. No OGR-based tool can open them — not pyogrio, not fiona, not `ogrinfo`. They
  are loadable only by `shapely.from_wkb` / `from_wkt`. Every one produced
  `DataSourceError: not recognized as being in a supported file format`.
- **7 cases need an optional GDAL driver plugin** (`Parquet`, `Arrow`, `GeoArrow`,
  `Feather`). These are absent from `libgdal-core`, the default conda-forge GDAL, and
  from pyogrio's PyPI wheels. They require `libgdal-arrow-parquet`.
- 1 case, `unclosed_ring_polygon`, raises `GEOSException` and is *supposed* to —
  `expect_loadable=False`. Correct behaviour, listed here only so the count reconciles.

**Recommendation.** Make `loader_hint` a filter argument on `list_cases()`, so a harness
can select `loader_hint="ogr"` and skip the rest rather than logging 19 spurious
`DataSourceError`s and then hand-maintaining an exclusion list. Separately, add a
declared driver prerequisite per case — something a consumer can check against
`pyogrio.list_drivers()` / `fiona.supported_drivers` before attempting a read. As it
stands, an 18% failure rate on first contact reads as "the corpus is broken", and a new
user has no way to tell which failures are theirs and which are the corpus's.

### 2. `list_cases(format="vector")` raises instead of redirecting

```python
>>> geocase.list_cases(format="vector")
pydantic_core._pydantic_core.ValidationError: 1 validation error for SuiteSelection
format
  Input should be 'GeoJSON', 'GPKG', 'Shapefile', 'GeoTIFF', 'NetCDF', 'Parquet',
  'GML', 'KML', 'CSV_WKT', 'Feather', 'Arrow', 'GeoArrow', 'WKB', 'WKT', 'SQLite',
  'FlatGeobuf' or 'Other' [type=literal_error, input_value='vector', input_type=str]
```

`format` wants a file format; `category` wants `vector`. This was the first call made
against the library and it failed. The pydantic error is informative enough to recover
from in seconds, but the names invite the mistake: in most geospatial tooling "vector"
*is* a format-ish word.

**Recommendation.** Either rename `format` to `file_format`, or special-case the three
category values with a redirecting message — `"'vector' is a category, not a format; use
list_cases(category='vector')"`. Cheap, and it removes the library's worst first
impression.

### 3. Cases are too small to reach paging, batching, or windowing bugs

Feature counts across the 84 readable vector cases:

| features | cases |
|---|---|
| 1 | 74 |
| 2 | 2 |
| 3 | 6 |
| 4 | 2 |

Maximum is **4**. This caps what a harness can reach. Probes written for
`skip_features`, `max_features`, their interaction, Arrow batch chunking
(`batch_size` / `MAX_FEATURES_IN_BATCH`), and paged reads all executed but could not
discriminate — with one feature, every boundary is the same boundary. Off-by-one errors
in windowing, batch-boundary geometry corruption, and partial-read dtype instability
(pyogrio documents that reading different row subsets can yield different dtypes for the
same column) are all invisible to a 1-feature corpus.

**Recommendation.** A handful of cases in the 10k-feature range, each still built around
one failure mode — e.g. an invalid geometry at feature 9,999; a NULL in a column whose
first 10k values are non-NULL, so type inference on a partial read disagrees with the
full read; a mixed-timezone datetime column that only becomes mixed after the first
batch. Storage cost is small and these reach a whole class of bugs the current corpus
cannot.

### 4. `expect_valid_geometry=False` conflates two different outcomes

```
self_intersecting_polygon   expect_loadable=True   expect_valid_geometry=False
unclosed_ring_polygon       expect_loadable=False  expect_valid_geometry=False
```

The first loads fine and is topologically invalid. The second cannot be constructed at
all — `shapely.from_wkb` raises `GEOSException: IllegalArgumentException: Points of
LinearRing do not form a closed linestring` before any validity question arises. Same
`expect_valid_geometry` value, categorically different consumer behaviour: one needs
`assert not geom.is_valid`, the other needs `pytest.raises`.

`expect_loadable` does disambiguate, but only for a consumer who reads both fields
together and works out that the combination is the signal. That is a documentation and
naming problem rather than a data problem.

**Recommendation.** Document the field pair as a matrix with the assertion each cell
implies. A tri-state `expect_valid_geometry` (`True` / `False` / `"unconstructible"`)
would be clearer still, if you are willing to change the schema before 1.0 final.

### 5. Failure *mode* is not assertable

When a case is expected to fail, what surfaces is the consumer library's own exception —
`GEOSException` from shapely, `DataSourceError` from pyogrio, `ValueError` from pandas.
Nothing in the case metadata says which. A harness can assert *that* a case failed, never
*how*, so it cannot distinguish "failed for the curated reason" from "failed because the
driver is missing" or "failed because the consumer has a new bug". During this run that
distinction had to be made by hand for all 20 failures.

**Recommendation.** An optional expected-error taxonomy on `assertions` — a small
vocabulary (`unparseable_geometry`, `unsupported_format`, `missing_driver`,
`invalid_crs`) rather than concrete exception classes, since those are consumer-specific.
This is what turns geocase from "files with labels" into something a CI job can gate on.

---

## Two additions that would have shortened this run

- **Ship the differential-harness recipe.** The most productive thing built here was
  ~100 lines: read every case two ways, compare, report divergences. That pattern is
  general — any library with two code paths (numpy vs Arrow, eager vs lazy, C vs pure
  Python) can use it verbatim. Shipping it as a documented example, or as a
  `geocase.differential` helper, means the next user finds bugs on day one instead of
  writing the harness first. The pytest markers and fixtures are aimed at
  assert-against-declared-truth, which is the *less* productive mode: both bugs here came
  from comparing a consumer against **itself**, not against geocase's assertions.

- **Record known consumer divergences per case.** `empty_geometry_gpkg` will now diverge
  between pyogrio's two paths for every user, until GDAL fixes it. Without somewhere to
  record that, the next person to run this harness re-investigates it from scratch, and —
  worse — cannot tell a newly-introduced bug from the catalogued one. A `known_divergences`
  block (consumer, version range, description, upstream link) would make repeat runs
  cumulative rather than repetitive.

---

## Corpus notes

Small observations, no action necessarily needed:

- `read_info()["features"]` is `-1` for all 6 GML cases — GDAL cannot count GML features
  without a scan. Not a geocase problem, but a harness that trusts declared feature
  counts will trip on it, so it is worth a note in the docs.
- The KML cases produce `object` dtype on pyogrio's numpy path and pandas `str` dtype on
  its Arrow path for `description` / `altitudeMode` / `icon`. This is expected pandas
  behaviour rather than a bug, but it is the kind of noise a differential harness has to
  be taught to ignore, and a per-case note would help.
- The CSV_WKT cases read their geometry as a plain string column unless the consumer
  passes GDAL's `GEOM_POSSIBLE_NAMES` open option. Worth stating in the case notes,
  since otherwise every consumer rediscovers it.
