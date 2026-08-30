# Plan 28 — Vector-First: Trust the Corpus, Then Sharpen It

> **Status: Phase 1 implemented 2026-08-28; Phase 2.1–2.3 implemented 2026-08-29;
> Phases 2.4–2.6, 3, 4 and 5 proposed.**

## Context

Two external validation runs of `1.0.0rc2` are in [`docs/geocase_validate/`](../geocase_validate/geocase-improvement-report.md). They reached **opposite verdicts**, and that split is the single most important input to this plan:

| Run | Target | Verdict | Bugs from the curated corpus |
|---|---|---|---|
| [geocase-improvement-report.md](../geocase_validate/geocase-improvement-report.md) | pyogrio / GDAL | **"Worth shipping."** | **2 real** — a `read_dataframe(fid_as_index=True, use_arrow=True)` crash (patched, accepted upstream as a regression test) and a GPKG spatial-filter divergence traced into GDAL's `GetArrowStream` (filed upstream) |
| [GEOCASE_VALIDATION_REPORT.md](../geocase_validate/GEOCASE_VALIDATION_REPORT.md) | rio-tiler | "Don't adopt as a bug-finding tool." | 0 |

The [GEOCASE_RECOMMENDATIONS.md](../geocase_validate/GEOCASE_RECOMMENDATIONS.md) "the files are not the moat, pivot to oracles" conclusion is drawn **from the rio-tiler run only**. It is not a verdict on geocase as a whole, and this plan does not treat it as one.

**The honest reading: the corpus works on the vector side and does not yet earn its keep on the raster side.** Both bugs pyogrio found came from cases under `vector/special/` built around a *named failure mode* (`dateline_chain_cluster`, `empty_geometry_gpkg`) — not from the 61 `*_baseline` files. So the corpus is validated where it is curated around failure modes, and thin where it is curated around format coverage.

### What I verified in this tree (not taken on the reports' word)

All of these reproduce:

- **`hole_center_nodata` is the exact inverse of its description.** It claims "valid pixels ring a central NoData void"; the actual 12×12 raster has nodata **only on the 1px outer border**, interior 10×10 fully valid. A consumer testing interior-hole preservation gets a green light from a case that cannot test it. This is the most damaging defect in the report — a validation tool that returns green for a property it cannot test terminates the user's search.
- **6 cases declare a nodata value and contain zero nodata pixels:** `multispectral_s2_like_small`, `ndvi_scaled_int16_small`, `multispectral_mixed_resolution_small`, `cog_multispectral_small`, `landcover_small`, `all_valid_rectangular`.
- **Root cause of both:** `scripts/validate_catalog.py` deliberately opens **no data file**. It checks schema, file *existence*, and byte-size-vs-`size_class`. Nothing has ever compared a declared assertion to an actual pixel or feature.
- **Scale ceiling:** 104 vector cases max out at **4 features** (74 have exactly 1); 55 raster payloads max out at **64px**, and 51 of 55 are striped not tiled.
- **`list_cases(format="vector")` raises a pydantic `ValidationError`** — the report's "worst first impression", reproduced on the first call.
- **19 of 104 vector cases cannot be opened by an OGR-based consumer** (6 WKB + 6 WKT bare geometry blobs, 7 needing `libgdal-arrow-parquet`). `loader_hint` cannot distinguish them: it is a pure 1:1 proxy for `category` (104 `geopandas` / 30 `rasterio` / 1 `xarray`), so the report's "filter on `loader_hint`" fix would not actually work. The real need is a **declared driver prerequisite**.
- **`risk_types` is not yet a vocabulary:** 111 distinct terms over 135 cases, **75 of them used exactly once**, and the most common (`format_comparison`, 60 cases) is a corpus-construction label rather than a failure mode.

### Intended outcome

1. The corpus stops lying — a content gate makes every declared assertion checkable against real bytes, permanently.
2. The vector track, which is the one with external evidence of value, gets the specific things pyogrio asked for.
3. Raster oracle work is recorded as a sequenced backlog, not started on speculation.

### Direction set by the user

- **Vector-first; raster follows.** Focus on the libraries that find geocase useful; accept not all will.
- **Conformance mode is not retired.** It found real bugs in pyogrio and GDAL. The rio-tiler run's "zero bugs" is one library's result, not a universal one.
- **Case size** is fixed with a few curated large vector cases, each still built around one failure mode — not on-demand generators.
- **The content gate covers the whole corpus**, not just the known defects.

---

## Phase 1 — Credibility: the content gate (blocking) — **implemented 2026-08-28**

Nothing else ships first. This is the phase that fixes the trust problem.

### 1.1 The checker module (TDD) — done

**Failing test first:** `tests/unit/test_case_content.py` — build a GeoTIFF via `geocase.raster.raster_fixture(...).write(tmp_path)` declaring `nodata=-9999` with **zero** matching pixels, hand it a `CaseMetadata` with `expect_nodata: true`, assert the checker returns one error naming the case id and `expect_nodata`. Watch it fail (module absent).

**New module:** `src/geocase/catalog/content.py` — pure functions, no CLI:

```
check_raster_content(case_dir, metadata) -> list[str]
check_vector_content(case_dir, metadata) -> list[str]
check_case_content(case_dir, metadata)   -> list[str]   # dispatch on category
```

**Reuse is the design.** Checks delegate to the existing helpers in [src/geocase/assertions/raster.py](https://github.com/farzinashouri/geocase/blob/main/src/geocase/assertions/raster.py) (`assert_no_nodata_pixels` and `assert_nodata_masked` already exist), `assertions/geometry.py`, `assertions/crs.py`, `assertions/footprint.py`, and `assertions/metadata.py`, catching `AssertionError` into a message list. The gate and the user-facing assertions must be the *same code*, or the gate can pass while a user's identical test fails.

It lives in `geocase.catalog.content`, not in `scripts/`, so the pytest job can unit-test it and users can run it against their own manifest cases.

### 1.2 The check matrix — one failing test each, in this order — done

1. `expect_nodata: true` ⇒ nodata tag is set **and** ≥1 pixel matches it (NaN-aware). *Catches all 6 phantom-nodata cases.*
2. `expected_nodata_value` set ⇒ same, against the declared value.
3. `expected_dtype` / `expected_shape` / `expected_band_count` / `expected_band_names` / `expected_epsg` / `expected_compression` / `expected_overviews` / `is_cog` ⇒ agree with the file.
4. **Vector (priority — this is the validated surface):** `expected_geometry_types`, `expect_valid_geometry`, `expect_crs` / `expected_epsg`, and declared feature count against the real count.
5. `expect_loadable: false` ⇒ the case **must** actually raise. An expected-failure that silently stops failing is a corpus defect too.
6. `params.expected_footprint` ⇒ the declared footprint GeoJSON is compared against a footprint derived from the **actual mask**, including hole count. This is the check that catches `hole_center_nodata`.

### 1.3 Risk-type as contract — done

Prose is uncheckable; the vocabulary is not. Keyed on `risk_types`, not on description text:

- any case declaring `nodata_ignored` must contain ≥1 nodata pixel;
- any case declaring `footprint_generation_error` with a declared footprint must have matching hole counts.

### 1.4 Script + CI wiring — done

**New:** `scripts/validate_case_content.py` — walks `metadata/case-index.yaml`, calls `check_case_content`, prints a per-case report, exits non-zero on any error. Flags: `--only <id>`, `--category`, `--json`.

**Where it runs — the `catalog` job.** [.github/workflows/ci.yml](https://github.com/farzinashouri/geocase/blob/main/.github/workflows/ci.yml)'s catalog job already installs `.[raster,vector]` inside `ghcr.io/osgeo/gdal:ubuntu-full-3.10.0`, so it has GDAL, rasterio, geopandas, shapely and pyarrow. The `tests` job on plain `ubuntu-latest` lacks `osgeo` and the Arrow/Parquet driver plugins — a gate there would skip exactly the cases most likely to drift.

`validate_catalog.py` stays reader-dependency-free (it only imports `geocase.catalog.*`) so it keeps running in the `tests` job and in a contributor's `.venv`. Two gates, two dependency profiles.

**Edits:** one line in the catalog job after `validate_catalog.py`; the "Catalog gates" block in [CLAUDE.md](https://github.com/farzinashouri/geocase/blob/main/CLAUDE.md).

### 1.5 Fix the defects the gate turns red — done

- **`hole_center_nodata`** — the real fix is structural: it is hand-committed and sits *outside* the only regeneration gate, which is why it drifted. Bring `footprint_edge_cases` under [scripts/generate_raster_fixtures.py](https://github.com/farzinashouri/geocase/blob/main/scripts/generate_raster_fixtures.py) as a `_footprint_edge_specs()` that emits the raster **and** its `_footprint.geojson` from the same array, so the footprint is derived by construction and cannot drift again. Build the interior void the case has always claimed.
- **`landcover_small`** (`nodata=0`) — **drop the declaration** rather than inject fake nodata. A landcover class of 0 is legitimate; 0 as both a class and a nodata sentinel is the `ambiguous_zero` risk and deserves its own explicit case, not a silent one.
- **`ndvi_scaled_int16_small`, `cog_multispectral_small`, `multispectral_s2_like_small`, `multispectral_mixed_resolution_small`** — inject real nodata pixels in the generator specs. These cases exist to exercise nodata handling and are inert without it.
- **`all_valid_rectangular`** — audit; "all valid" is the point, so it should not declare nodata.
- Regenerate and commit all gated artifacts: checksums, catalog pages, both coverage matrices, `case-index.yaml`.

### Phase 1 outcome (recorded 2026-08-28)

The gate was observed **red on exactly the 6 predicted cases**, then green after
1.5. Full sequence: 34 findings on first run → 10 after two checker bugs were
fixed → 6 (the plan's own list) → 0.

What differed from the plan:

- **`hole_center_nodata` was not caught by the footprint hole-count check
  (1.2.6).** Its committed footprint had been regenerated *from the drifted
  raster*, so declaration and mask agreed — both hole-free — and only the
  description disagreed. Comparing two declarations to each other cannot see
  this. What catches it is the **1.3 risk-type contract**: a case declaring
  `footprint_generation_error` whose nodata is a pure outer-border collar
  cannot exercise the risk it advertises, because cropping to the valid extent
  yields the same polygon either way. This is a stronger check than planned and
  the one that should be extended in Phase 4.
- **Two checker bugs had to be fixed before any case data was touched**, both
  false positives that would have caused real damage if acted on:
  1. Reading vector cases with `geopandas.read_file` failed 19 cases (WKB/WKT/
     CSV_WKT/Parquet/Arrow). The gate now loads through `VectorCase.load()` —
     the same path a user takes. This also means Phase 2.1's `required_drivers`
     is about *consumer* discoverability, not about geocase being unable to
     read its own cases.
  2. `expect_valid_geometry: false` is enforced in **neither** direction. Four
     shipped cases (`null_island_point`, `out_of_bounds_coordinates`,
     `ambiguous_engine_dependent_polygon`, `empty_geometry_gpkg`) are
     OGC-*valid* but semantically suspect, so `assert_invalid_geometry` fails
     them for the schema limitation 1.6 explicitly declined to fix. Only the
     `True` direction is checked; Phase 2.4's documented matrix is the fix.
  Also: NULL geometries report `geom_type` NaN, so the geometry-type check now
  skips them (this is what `empty_geometry_gpkg` exists to carry).
- **`all_valid_rectangular` needed no change.** It declares no nodata
  expectation; the file carries a nodata *tag* with zero matching pixels, which
  is correct for an all-valid scene. The audit resolves as no-op.
- **`landcover_small` also lost `nodata_ignored`** from `risk_types` (and
  `nodata-check` from `expected_capabilities`) — dropping the declaration
  without dropping the risk type would just move the lie.
- **The `footprint_edge_cases` restructure was scoped down.** All five cases
  now come from `_footprint_edge_specs()` under the regeneration gate, but only
  `hole_center_nodata` emits its footprint from its own mask. The other four
  committed footprints record `gdal_footprint`'s *simplified/hull* output —
  `rotated_two_islands`, for instance, is a single polygon spanning the gap
  between two disjoint islands — so regenerating them mask-exact would have
  silently changed what `examples/test_gdal_footprint.py` asserts. Their
  rasters regenerate byte-identically; their footprints are left alone and the
  discrepancy is documented in the folder's `notes.md`.
- **The fix made a real divergence observable.** With the interior void
  restored, `gdal_footprint` fills it — returning 129600 m² solid instead of
  the 115200 m² ring. That is precisely the `nodata_ignored` /
  `footprint_generation_error` behaviour the case advertised and could never
  demonstrate. `examples/test_gdal_footprint.py` gained
  `test_gdal_footprint_fills_interior_nodata_void` asserting it, and
  `hole_center_nodata` was removed from the parametrized test that asserts the
  expected footprint has no holes.
- **Vector feature counts** are keyed on `params.expected_feature_count` (the
  key actually used by the 6 cases that declare one), not a new field.

**End-to-end proof (required by Verification):** reverting
`hole_center_nodata.tif` to its committed bytes makes
`validate_case_content.py --only hole_center_nodata` exit 1 naming both the
footprint and the risk-type check. Restored byte-identical afterwards.

**Gates green:** all six catalog `--check` gates, `pytest tests` (1726 passed),
`pytest examples` (1179 passed), `ruff format`/`ruff check`, `mypy src`,
`mkdocs build --strict`.

### 1.6 Cut from Phase 1

- **Cut** NetCDF content validation beyond dims/CRS — xarray is not in the catalog job's install set and adding it is scope creep for a single case.
- **Cut** the tri-state `expect_valid_geometry` schema change (pyogrio report §4). It is a v1.0 schema break for what is a documentation problem; ship the matrix in docs instead (4.4).

---

## Phase 2 — The pyogrio track (the validated surface)

Everything here is a direct ask from the run that said "worth shipping".

### 2.1 Driver prerequisites — kill the 18% first-contact failure rate — **done**

**Failing test** in `tests/unit/test_public_api.py`: cases whose format is Parquet/Arrow/GeoArrow/Feather expose a checkable driver requirement; WKB/WKT cases declare they are not OGR-openable.

Add `required_drivers: list[str] = []` to `AssertionHints` in [src/geocase/catalog/models.py](https://github.com/farzinashouri/geocase/blob/main/src/geocase/catalog/models.py) (additive pydantic field with a default — safe), populated by a metadata pass. A consumer checks it against `pyogrio.list_drivers()` / `fiona.supported_drivers` before reading.

**Also needed, because `loader_hint` cannot do this job:** the 12 WKB/WKT cases are bare geometry blobs no OGR tool can open, and `loader_hint` marks all 104 vector cases `geopandas`. Either correct those 12 to a `shapely`-shaped hint or express it via `required_drivers` — decide during implementation, but the filter must actually separate them, which today it does not.

### 2.2 `loader_hint` filter on `list_cases` — **done**

Additive `loader_hint: LoaderHint | None = None` on `SuiteSelection`, `matches_selection`, `select_cases`, `list_cases`. `LoaderHint` already exists and is exported. Purely additive. Only useful once 2.1 makes the hints discriminating.

### 2.3 `format="vector"` redirecting error — **done**

**Failing test:** `list_cases(format="vector")` raises an error whose message says `category='vector'`. A pre-check in [src/geocase/api/public.py](https://github.com/farzinashouri/geocase/blob/main/src/geocase/api/public.py) intercepts the `Category` literals before pydantic sees them. **Do not rename `format` to `file_format`** — a v1.0 break for a message problem. ~10 lines removes the library's worst first impression.

### Phase 2.1–2.3 outcome (recorded 2026-08-29)

Implemented in the order 2.3 → 2.1 → 2.2, since 2.2 is inert until 2.1 makes
the metadata discriminate.

**The counts in this plan's Context section are stale and were re-measured.**
Plans 32 and 34 landed between writing and implementing, taking the catalog
from 135 to **150** cases. The corrected figures: **113 vector** cases (not
104), of which **20** cannot be opened by an OGR consumer — **13 WKB/WKT**
(not 12; `polygon_z_wkb` arrived with Plan 34) and **7** Arrow-family.
`loader_hint` is still an exact 1:1 proxy for `category`
(113 `geopandas` / 34 `rasterio` / 3 `xarray`), so §2.2's premise held.

**The premise correction from Phase 1 was re-verified rather than assumed.**
A probe read every vector case twice — once through `pyogrio.read_info`, once
through `VectorCase.load()`. OGR fails exactly those 20; `VectorCase.load()`
opens **all 113**. (The one other load failure, `unclosed_ring_polygon`, is a
curated `expect_loadable: false` case and is correct.) So `required_drivers` is
documented throughout as *consumer* discoverability, never as a geocase
limitation. Notably the conda `geocase` env is itself missing the Arrow/Parquet
OGR drivers, so the field describes a live condition on the dev machine, not a
hypothetical one.

**§2.1's open decision — `required_drivers` vs. a corrected `loader_hint` —
resolved in favour of `required_drivers` alone.** `loader_hint` is not a label:
`loaders/generic.py` dispatches on it, and it is exported in `__all__` as the
`LoaderHint` literal. Adding a `shapely` member would be a v1.0 schema change
plus a new dispatch branch, to express something `required_drivers` states
directly and more precisely — it also distinguishes *why* a case is closed to
OGR (no driver exists at all vs. an installable plugin is missing), which a
loader hint cannot. `loader_hint` stays `geopandas` for all 113, which is
accurate: `VectorCase.load()` does return a `GeoDataFrame` for every one.

**Three tiers, and the sentinel is the design.** `NO_OGR_DRIVER = ""` is a new
module-level constant in `catalog/models.py`. The empty string is deliberately
falsy so the natural consumer filter —
`all(d in available for d in case.assertions.required_drivers)` — excludes
bare-blob cases for *every* possible `available` set, with no need to know the
sentinel exists. The `TestTheFilterActuallySeparates` test class is the plan's
own acceptance bar written down: the three tiers must partition the 113 vector
cases and none may be empty.

What differed from the plan:

- **The catalog page generator needed a change the plan did not anticipate.**
  `_assertion_rows` renders any populated hint automatically, so
  `[NO_OGR_DRIVER]` came out as an empty pair of backticks — the least useful
  cell on the page, on the cases where it carries the most information. Added
  `_required_drivers_cell` to render it as "none — no OGR driver opens this
  format (use shapely)", and to stay silent for the `[]` majority.
- **`list_cases`'s docstring now warns against the obvious misreading of
  2.2.** Having just shipped a `loader_hint` filter, the natural user error is
  to reach for it to answer "can my reader open this?" — which it cannot. The
  docstring points at `required_drivers` with a worked `pyogrio.list_drivers()`
  example.
- **2.3 rejects all four `Category` literals, not just `"vector"`**, and a test
  pins that `format="Nonsense"` still raises the pydantic `ValidationError`, so
  the pre-check does not swallow unrelated bad input.
- The `case.schema.yaml` `assertions` block gained `required_drivers` too —
  `test_assertion_properties_match_assertion_hints_fields` gates schema and
  model against each other, so the field could not land in one alone.

**Gates green** (conda `geocase`, Python 3.14): all ten catalog gates
(`build_case_index --check`, `validate_catalog`, `validate_case_content`,
`catalog_extent --check`, the four fixture generators `--check`,
`generate_checksums --check`, `generate_catalog_pages --check`,
`generate_raster_previews --check`), both coverage matrices regenerated,
`pytest tests` (**1897 passed, 37 skipped**), `pytest examples` (**1389 passed,
36 skipped, 57 xfailed**), `ruff format --check`, `ruff check`, `mypy src`
(99 files, clean — `catalog.*` and `api.*` are strict), `mkdocs build --strict`.

### 2.4 Expected-error taxonomy — make failure *mode* assertable

Today a harness can assert *that* a case failed, never *how*, so it cannot distinguish "failed for the curated reason" from "the driver is missing" from "the consumer has a new bug". During the pyogrio run that distinction was made by hand for all 20 failures.

`ExpectedErrorKind = Literal["unparseable_geometry", "unsupported_format", "missing_driver", "invalid_crs", "invalid_topology"]` as an optional field on `AssertionHints` — a small vocabulary, not concrete exception classes, since those are consumer-specific. Phase 1's content gate then asserts the case *actually* fails that way; the two phases reinforce.

Also document the `expect_loadable` × `expect_valid_geometry` pair as a matrix with the assertion each cell implies (this is the docs answer to the cut in 1.6).

### 2.5 `known_divergences` — make repeat runs cumulative

`empty_geometry_gpkg` will diverge between pyogrio's two paths for every user until GDAL fixes it. Without somewhere to record that, the next person re-investigates from scratch and cannot tell a new bug from the catalogued one.

`KnownDivergence(consumer, version_range, description, upstream_url)`; `CaseMetadata.known_divergences: list[KnownDivergence] = []`. Seed it with the `empty_geometry_gpkg` / pyogrio-Arrow finding and the GDAL issue from [gdal-issue-draft.md](../geocase_validate/gdal-issue-draft.md).

### 2.6 Ship the differential-harness recipe

The pyogrio report: *"The most productive thing built here was ~100 lines: read every case two ways, compare, report divergences."* It generalizes to any library with two code paths (numpy vs Arrow, eager vs lazy, C vs pure Python).

Ship it as `src/geocase/differential.py` + a documented example, with `known_divergences` consulted so a matching divergence is reported as `known` rather than `failed`. **Scope it to the vector/two-code-path shape that is actually evidenced** — not the full raster adapter protocol, which belongs to Phase 4.

---

## Phase 3 — Large curated vector cases

Both reports independently flag this; it is the one thing they agree on. Max 4 features means probes for `skip_features`, `max_features`, Arrow batch chunking and paged reads all *execute but cannot discriminate* — with one feature, every boundary is the same boundary.

A handful of ~10k-feature cases, **each still built around one failure mode** (this is the distributional lesson: `special/` found the bugs, the 61 baselines contributed runtime):

- an invalid geometry at feature 9,999 — past every plausible batch boundary;
- a NULL in a column whose first 10k values are non-NULL, so partial-read type inference disagrees with the full read (pyogrio documents this dtype instability);
- a mixed-timezone datetime column that only becomes mixed after the first batch.

These must be **generated by a script under the regeneration gate**, not hand-committed — that is the lesson of `hole_center_nodata`. Watch `size_class` (`_SIZE_CLASS_MAX_BYTES`: tiny 512 KB, small 5 MB) and the 2.1 MB bundle budget; these are `medium` and may warrant a manifest rather than the wheel.

---

## Phase 4 — Raster backlog (recorded, not started)

The rio-tiler run's recommendations are sound *for raster* and stay sequenced behind the validated vector work. Recorded here so they are not lost:

- `geocase.oracles` — adapter protocol (`RasterReaderAdapter` with a `supports` capability set so unsupported ops skip rather than fail), a rasterio reference adapter, and the 8 metamorphic properties: query purity, band-permutation equivariance, translation equivariance (**geocase already ships the `geotiff_nodata_small` / `_shifted` pair and has never used it as an oracle**), rotation equivariance, `part(full) == read()`, tile-mosaic z+1 consistency, nodata relabelling, overview ≈ decimated.
- Generator parameters on [src/geocase/raster/primitive.py](https://github.com/farzinashouri/geocase/blob/main/src/geocase/raster/primitive.py): `tiled`/`blocksize` (51 of 55 payloads are striped, which makes the entire COG/range-request surface unreachable), `overviews`, mask kind, per-band nodata.
- New axes in [src/geocase/raster/axes.py](https://github.com/farzinashouri/geocase/blob/main/src/geocase/raster/axes.py): `south_up_transform`, `x_flipped_transform`, parameterised `sheared_transform(angle=)`, `interior_hole`, `nodata_equals_valid_value`, `per_band_nodata`.

**Entry condition:** start Phase 4 when a raster consumer reports value, or when Phase 1's gate is green and Phases 2–3 have shipped. Do not start it on the strength of one negative report.

**Cut outright:** the cross-version differential matrix ("the moat"). It is a *service* — scheduled workflow, results store, pinned environments — not a library feature. Build it only once the shipped differential helper has found a defect in a library not maintained here. Building it before that is the four-gates-zero-users pattern [22-portfolio-direction.md](22-portfolio-direction.md) already named.

---

## Phase 5 — Positioning

**Reframe; do not retire.** The declared-assertion mode found real bugs in pyogrio and GDAL, and after Phase 1 it does genuine work catching drift.

- State the split honestly in docs: the corpus's demonstrated yield is on **failure-mode cases** (`vector/special/`), not on baselines or on the current raster set. That is a sharper and more defensible claim than either report's headline.
- Add `docs/validation-findings.md` summarising both runs and linking [`docs/geocase_validate/`](../geocase_validate/geocase-improvement-report.md), including the rio-tiler negative result. An honest README beats a defensive one.
- The README's existing pitch already shows the *user* writing a differential check (`mean_elevation(array)` vs `valid.mean()`) rather than trusting a declared assertion — that framing survives both reports and should be kept.
- **Zero code impact.** Fixtures, all four markers, `assertions/`, and the 27-name `__all__` are untouched.

---

## v1.0 compatibility

| Change | Risk |
|---|---|
| `AssertionHints` new optional fields (`required_drivers`, `expected_error_kind`) | **None** — pydantic defaults. `required_drivers` landed 2026-08-29 with a `[]` default; `expected_error_kind` belongs to 2.4 and is not built. |
| `CaseMetadata.known_divergences` | **None** — additive, defaults to `[]` |
| `SuiteSelection.loader_hint` | **None** — additive, keyword-only |
| `geocase.differential` submodule | **None** — new module, not in `__all__` (`geocase.raster` / `geocase.assertions` set this precedent) |
| `list_cases(format="vector")` raises `ValueError` not `ValidationError` | **Low** — both are errors; note in `CHANGELOG.md` |
| `hole_center_nodata.tif` bytes change | **Behavioural** — checksums change; id/path/filenames stable. Changelog + `notes.md` |
| `landcover_small` loses `nodata=0`; 4 cases gain real nodata pixels | **Behavioural** — checksums change; regenerate catalog pages |
| Fixtures, markers, `__all__` | **Untouched** |

Nothing removes a case id, fixture, marker, or `__all__` entry. **The shipped corpus is not deleted or shrunk** — that would break every `include_ids`, suite, catalog page and checksum for zero benefit. (Note: [U21](development-plan.md) separately contemplates deleting ~128 unreferenced cases; that decision is out of scope here and this plan assumes they stay.)

---

## Verification

```bash
conda activate geocase                       # only env with osgeo

# Phase 1 — the new gate; must be RED before the 1.5 fixes and GREEN after
python scripts/validate_case_content.py
python scripts/validate_case_content.py --only hole_center_nodata --json

# the unit tests for the checker run at the CI floor, without osgeo
pytest tests/unit/test_case_content.py -q

# Phases 2-3
pytest tests/unit/test_public_api.py -q
python -c "import geocase; geocase.list_cases(format='vector')"   # expect the redirecting message
python -c "import geocase; print(len(geocase.list_cases(loader_hint='geopandas')))"

# existing gates must stay green after every regeneration
python scripts/build_case_index.py --check
python scripts/validate_catalog.py
python scripts/generate_raster_fixtures.py --check
python scripts/generate_vector_fixtures.py --check
python scripts/generate_checksums.py --check
python scripts/generate_catalog_pages.py --check
pytest tests -q
ruff format --check src tests && ruff check src tests
mypy src
mkdocs build --strict
```

**End-to-end proof the gate works:** temporarily revert `hole_center_nodata.tif` to its current (inverted) bytes and confirm `validate_case_content.py` fails naming that case. A gate that has never been observed red is not a gate.

**Proof the corpus still finds bugs:** re-run the pyogrio differential using the shipped `geocase.differential` helper and confirm it reproduces the `empty_geometry_gpkg` divergence — now reported as `known` rather than as a fresh failure.

---

## Plan-doc obligations (per CLAUDE.md)

- Write this as `docs/plans/28-vector-first-corpus-trust.md` (28 is the next free number) with the `> **Status: proposed 2026-08-27.**` blockquote and `## Phase N` / `### N.M` structure.
- Add a row to [docs/plans/index.md](index.md).
- Add Plan 28 to the **Active sequence** in [docs/plans/development-plan.md](development-plan.md), ahead of the catalog deployment — a catalog site should not deploy on top of a corpus with a known false-passing case.
- Add one row to [27-close-plan-26-findings.md](27-close-plan-26-findings.md), which already owns the `risk_types` vocabulary problem: each vocabulary entry gains a field naming the content-gate check that enforces it. Do **not** fork that work into this plan.
- Mark progress in the plan doc as each phase lands.
