# Plan 34 — Close the Reviewed Catalog Gaps

> **Status: proposed 2026-08-29.**

## Context

An external geospatial expert reviewed the 143-case catalog and named 16 candidate gaps. Each was verified against the code before planning. The review is high quality: **3 of 16 were already covered, 1 was read backwards, and the remaining 12 are real.** But they are not equal in value, and doing all 12 would be the wrong call.

The plan writes `docs/plans/34-close-reviewed-catalog-gaps.md` and implements it. Net scope: **6 new cases (143 → 149), 1 subtraction, 1 generator built from nothing.**

### Verified: already covered — the expert was wrong (no work)

- **Anisotropic pixels** — `nonsquare_diagonal_sparse` is genuinely 60 m × 30 m (`generate_raster_fixtures.py:426`). The expert hedged ("ensure it tests anisotropic resolution"); it does.
- **Kissing rings** — `ambiguous_engine_dependent_polygon`, shell and interior ring touching at one point.
- **Missing CRS** — 15 WKB/WKT/CSV baselines with `expect_crs: false`.
- **Collinear vertices** — read backwards. `fractal_coastline_polygon` states it has *no* collinear vertices as a deliberate property, and collinearity is already a benchmark trap category. A fixture here would test `simplify()` tolerance, a library behaviour, not a data property. **Cut.**

### Verified missing, but cut or deferred

- **Alpha band as nodata** — cut. `NodataConvention` is a v1.0 `Literal` (`sentinel|nan|mask|none`); extending it for one fixture is a compatibility break. `mask` already means "validity lives outside the pixel values".
- **Overlapping MultiPolygon parts** — cut. Same OGC-validity axis as the bowtie and touching-ring cases already shipped; adds a case, not a discriminating failure mode.
- **Timezone-naive vs aware datetimes** — deferred. The gap is real (no vector fixture has *any* datetime attribute), but [Plan 28](28-validate-geocase.md) Phase 3 already owns it and needs ~10k features to discriminate. A two-feature version would pre-empt that design with a fixture too small to work.
- **Curvilinear 2D coordinate grids** — deferred to a follow-up, unblocked by this plan's Phase 1 generator.
- **int64 > 2^53** — taken as a one-line rider in Phase 4, not a phase.

### The five that survive, ranked by leverage

| # | Gap | Why it leads |
|---|---|---|
| 1 | **NetCDF has no generator** | `latlon_sample.nc` is the **only fixture in the repo that cannot be regenerated** — one "Analyse structure" commit, and its temperature values are unseeded random floats with no recoverable provenance (checked 400 seed/distribution combinations, no hit). Every NetCDF gap is blocked behind this. |
| 2 | **Bottom-up / positive-`e` affine** | Silent-wrong-answer class. All 32 rasters use `from_origin`, which always emits `e < 0`, so a consumer assuming north-up passes the entire catalog. Cheapest possible fixture: one sign flip. |
| 3 | **`AREA_OR_POINT`** | Half-pixel georeferencing error, invisible to every existing gate. `_write_raster` already has an unused `update_tags` path. |
| 4 | **Z coordinates** | Highest breadth-per-fixture of the vector gaps: one `POLYGON Z` exercises WKB byte layout, GPKG geometry flags, and driver-level Z-dropping at once. |
| 5 | **Axis order declaration** | Already owed by [Plan 27](27-close-plan-26-findings.md) §1.3. The GML baselines *genuinely contain* authority-order `(lat, lon)` coordinates on disk — `_spatial_reference()`'s docstring documents it — and **no `case.yaml` says so**. A metadata change over bytes that already exist. |

### The subtraction, which is the highest-value single item

`latlon_small` declares `risk_types: [coordinate_order, dimension_mismatch]` over conventional `(latitude, longitude)` rectilinear data. **The risk is labeled, not exercised** — the same defect class Plan 28 Phase 1 found six times and Plan 32 found in the footprint truths. A case that returns green for a property it cannot test terminates the user's search. The fix is removal, then a new case that actually carries the risk.

### Structural constraints

1. **`AssertionHints` is doubly gated** — `tests/unit/test_case_models.py:407,414` assert strict set equality between `case.schema.yaml`'s properties and both `CaseMetadata.model_fields` and `AssertionHints.model_fields`. Any new field moves both files in one commit. This is the test, not an obstacle.
2. **Prefer derived predicates and `params` to new fields** (Plan 33's `_is_pole_cap` precedent). Two new typed fields total; everything else uses `params` **with a matching `content.py` check** — `params` is unvalidated, so anything put there without a check is decoration.
3. **The `catalog` CI job installs `.[raster,vector]`, not `netcdf`** (`ci.yml:137`). The `netcdf` extra exists (`xarray>=2023.1`, `netCDF4>=1.6`) but is never installed in CI, which is the documented reason `check_case_content` returns `[]` for netcdf (`content.py:542`). **A NetCDF generator cannot be gated until that line changes.** Phase 1.0 changes it.

### Compatibility

Nothing touches `src/geocase/__init__.py`'s `__all__` or the four pytest fixtures/markers. New `AssertionHints` fields are `None`-defaulted and additive. `PixelAnchor` is a *new* `Literal`; no promised one is extended.

---

## Phase 1 — Make NetCDF reproducible (unblocking)

### 1.0 CI can run it

`.github/workflows/ci.yml:137` → `.[raster,vector,netcdf] "numpy<2"`. **Verify first** in `.venv` (3.11) that `netCDF4>=1.6` resolves against `numpy<2` — netCDF4 wheels are built per-numpy-ABI and this is the likeliest thing to break the job. Fallback: add `h5netcdf` (pure h5py, no numpy ABI coupling) to the extra. Comment in the style of the existing `numpy<2` note.

### 1.1 Tests first — new `tests/unit/test_netcdf_fixtures.py`

- `test_generator_output_matches_the_shipped_fixture` — build `latlon_small` into `tmp_path` and compare **semantically** (see 1.3) against the shipped file. Red until 1.4 lands the replacement, green after, and the standing `--check` gate thereafter. Write it against the *regenerated* fixture, not the pre-replacement bytes.
- `test_latlon_small_keeps_its_declared_shape` — the replacement holds dims `(5, 8)`, `float64`, `_FillValue = -9999.0`, and exactly two fill cells. Pins the properties 1.4 promises to preserve, so a future regeneration cannot quietly drift the case out from under its own `case.yaml`.
- `test_netcdf_generator_is_deterministic` — two builds compare equal; plus a source grep for no `random`/`time`/`uuid`/`datetime.now`, matching `test_generated_geometry.py`'s structural-determinism pattern.
- `test_check_case_content_validates_netcdf_dimensions` — `params.expected_dimensions: [latitude, longitude]` → `[]`; `[time, x]` → exactly one error naming the field.
- `test_netcdf_content_check_is_skipped_without_xarray` — monkeypatch the import to raise; must return `[]`, not raise.

### 1.2 Code — new `scripts/generate_netcdf_fixtures.py`

Modelled on `generate_raster_fixtures.py`. A `NetCDFSpec` dataclass (`case_id`, `dims`, `variables`, `var_attrs`, `global_attrs`, `encoding`), `_write_netcdf` building an `xarray.Dataset` and calling `.to_netcdf(dest, encoding=..., engine=...)` with the **engine pinned explicitly** — auto-selection makes output depend on which library is installed, defeating the reproducibility being bought.

`--check` is **semantic, not byte**: HDF5 stamps a library-version string and varies chunk ordering by build, so a byte gate fails on a dependency bump with no data change. `generate_vector_fixtures.py` already gives this exact reasoning for GPKG/SQLite/Parquet — cite it. Compare a `_semantic_signature(path)` tuple over sorted dims+sizes, var names+dtypes+`_FillValue`/`scale_factor`/`add_offset`, coordinate arrays at 9 dp, and global attrs. Exit codes match the siblings (0/1/2).

### 1.3 Code — retire the netcdf carve-out — `src/geocase/catalog/content.py`

Replace `if metadata.category == "netcdf": return []` (line 542) with a dispatch to a new `check_netcdf_content`, added beside `check_raster_content`/`check_vector_content` and exported in `__all__`. It returns `[]` on `ImportError` — a missing optional reader is not a finding.

Checks, all through `_collect`: `params.expected_dimensions` (**in declared order** — that is what makes dim-ordering checkable at all), `params.expected_variables`, `expect_nodata` → the variable declares `_FillValue`, `expected_scale_factor` (reusing the existing raster field), `params.expected_time_units`.

**Do not check `expect_crs` naively.** `latlon_small` declares `expect_crs: true` and `expected_epsg: 4326` with *no* `grid_mapping` or `crs` variable in the file. A strict check turns this phase red on an unrelated case. Treat an absent CRS variable as not-a-finding, and record in "As built" whether the declaration or the check is wrong. Do not silently change the case.

Update the module docstring — its "netcdf is not content-checked (Phase 1 cut)" paragraph becomes false in the same change.

### 1.4 Replace `latlon_sample.nc` — user decision, 2026-08-29

The coordinates are `linspace`-reconstructable (`40→50` × 5, `10→20` × 8) but the 40 temperature values are **not**: unseeded random floats in ~[10, 35] with two `-9999.0` fills. 400 seed/distribution combinations were searched; none matched.

That rules out *reconstruction*. It does not by itself force *replacement* — the alternatives were to leave the binary and add a new reproducible case beside it, or to exempt `latlon_small` from `--check` and document it as predating the generator. **The user chose replacement**, accepting the trade-off below.

This is the plan's only non-additive change. `latlon_small` is `status: validated` and ships in the package, so anyone who pinned a release and asserted against specific temperature values will break. Nothing in this repo does — the case's own assertions are structural (dims, variables, `_FillValue`, `expect_nodata`) — but external users are not visible from here.

Emit a deterministic ramp with the same shape, dtype, `_FillValue` and fill positions (row 0 col 0, row 3 col 5) so every declared assertion still holds, then regenerate `checksums.sha256` for the case. Nothing else changes.

Record the replacement in the case's `notes.md` and in the release notes for the next version — a bytes change to a published fixture that the changelog does not mention is indistinguishable from corruption.

### 1.5 Wire into the gates

`CLAUDE.md`'s catalog-gate block, `ci.yml`'s catalog job (after `generate_vector_fixtures.py --check`), `docs/contributing/workflow.md`, and `docs/adding-a-case.md` — which has never had a NetCDF path.

---

## Phase 2 — Transform sign and pixel anchor

### 2.1 Tests first

`tests/unit/test_case_models.py`: the two strict-equality tests go red the moment `models.py` gains fields — that *is* the test. Add `test_pixel_anchor_enum_matches_literal`, mirroring `test_nodata_convention_enum_matches_literal` at :417.

New `tests/unit/test_raster_transform_cases.py`:
- `test_bottom_up_case_has_positive_y_resolution` — `src.transform.e > 0`.
- `test_bottom_up_case_bounds_are_still_normalised` — `bounds.bottom < bounds.top` despite positive `e`. Catches a consumer computing bounds from `f + e*height` without ordering.
- `test_declared_transform_signs_match_the_file` — mutate declared signs → exactly one error.
- `test_pixel_is_point_case_declares_the_tag` — `src.tags()["AREA_OR_POINT"] == "Point"`; the sibling reads `"Area"`.
- `test_pixel_anchor_half_pixel_offset_is_observable` — the pair shares transform and array; the two conventions differ by exactly half a pixel. This proves the pair is *useful*, not merely present.

### 2.2 Code — `models.py` + `case.schema.yaml`, one commit

```python
PixelAnchor = Literal["area", "point"]
```
On `AssertionHints`, after `is_cog`:
```python
    expected_transform_signs: list[str] | None = None   # {"positive_e"|"negative_e"} + "rotated"
    expected_pixel_anchor: PixelAnchor | None = None
```
A *list* because a rotated affine is not describable by one sign — it carries non-zero `b`/`d` too. Mirror both in `case.schema.yaml`'s `assertions.properties`, with the enum matching `PixelAnchor`.

### 2.3 Code — the assertions

Put `assert_transform_signs` and `assert_pixel_anchor` in `src/geocase/assertions/raster.py`, **not** `content.py` — the gate and the user-facing check must be the same code, as `content.py`'s docstring requires. `check_raster_content` calls them through `_collect`. `AREA_OR_POINT` reads `src.tags().get("AREA_OR_POINT", "Area")` — the default matters, since GDAL omits the tag for the area convention.

### 2.4 Code — fixtures — `scripts/generate_raster_fixtures.py`

Add `RasterSpec.tags: dict[str, str]` and, in `_write_raster`, `if spec.tags: dst.update_tags(**spec.tags)` — converging with `raster/_writer.py:56`, which already does this.

Three cases in one `transform_conventions/` directory (following `_FOOTPRINT_DIR`'s precedent — siblings whose whole value is comparison share a folder and a `notes.md`):

- **`bottom_up_dem_small`** — 12×12 float32, nodata `-9999.0`, EPSG:32633, `Affine(30.0, 0.0, 500000.0, 0.0, 30.0, 4200000.0)`. Positive `e`, origin bottom-left. **Row 0 is the southernmost row**, so build the array as `np.flipud` of the north-up ramp and comment why — getting this backwards yields a file that is self-consistent and geographically inverted, the exact bug the case exists to catch.
- **`pixel_is_point_dem_small`** — same geometry, `tags={"AREA_OR_POINT": "Point"}`.
- **`pixel_is_area_dem_small`** — the control, with `"Area"` written **explicitly** so the pair is a true differential.

**Backfill** `expected_transform_signs` on `rotated_two_islands` (`["negative_e", "rotated"]`) and `nonsquare_diagonal_sparse` (`["negative_e"]`) — two lines each, turning a property the corpus always had into one it declares.

### 2.5 Regenerate — order is load-bearing

`generate_raster_fixtures.py` → `build_case_index.py` → `catalog_extent.py --write` → `validate_catalog.py` → `validate_case_content.py` → `generate_raster_previews.py` → `generate_catalog_pages.py` → `generate_raster_coverage_matrix.py` → `generate_checksums.py`.

`validate_catalog.py` **will fail** on its case-count claims (Plan 33 hit this): bump every claim it enforces across `README.md`, `docs/`, and `recipe/meta.yaml`. 143 → 146.

---

## Phase 3 — NetCDF coverage, and the subtraction

Depends on Phase 1 being green.

### 3.1 Tests first — extend `tests/unit/test_netcdf_fixtures.py`

- `test_packed_variable_unpacks_to_physical_units` — `mask_and_scale=False` gives `int16`; the default gives floats in [-1, 1]. **The pair is the test** — a consumer reading raw sees plausible integers, which is the failure mode.
- `test_cf_time_decodes_to_the_expected_calendar` / `test_cf_time_undecoded_is_raw_numbers` — same differential shape via `decode_times=False`.
- `test_dimension_order_is_non_conventional` — `list(ds["t2m"].dims) == ["longitude", "latitude", "time"]`, x before y.
- `test_latlon_small_no_longer_claims_undemonstrable_risks` — regression guard on the subtraction.

### 3.2 The subtraction — `netcdf/latlon_small/case.yaml`

Remove `coordinate_order` and `dimension_mismatch` from `risk_types`. Replace the unvalidated `params.dimensions`/`params.variables` with the now-gated `expected_dimensions`/`expected_variables`. Record in `notes.md`. Same correction Plan 28 made to `landcover_small`.

### 3.3 Two fixtures

- **`ndvi_packed_netcdf`** — `ndvi(latitude=6, longitude=10)` stored `int16`, `scale_factor=0.0001`, `add_offset=0.0`, `_FillValue=-32768`, raw values spanning [-10000, 10000]. Set the encoding **explicitly** or xarray re-derives packing on write and the fixture's point becomes an artefact of the library version. Deliberately mirrors the raster `ndvi_scaled_int16_small`, giving the catalog a **cross-container pair** for one failure mode — say so in both `notes.md` and cross-link via `params.analogous_case_id`.
- **`cf_time_ordering_netcdf`** — `t2m(longitude=8, latitude=5, time=3)`, dims x-before-y with time last, `time` encoded `"hours since 2020-01-01 00:00:00"`, calendar `gregorian`, values `[0, 24, 48]`. **Combining time-units and dim-ordering in one fixture is deliberate**: a `time` dimension has to go somewhere in the ordering, so a CF-time case is already making a dim-order statement. Two cases would each carry both properties while declaring only one — the exact defect 3.2 fixes.

### 3.4 Regenerate

Same order as 2.5, with `generate_netcdf_fixtures.py` at step 1 and no raster previews. `catalog_extent.py` writes no extent for netcdf — confirm `generate_catalog_pages.py` renders those pages without an empty Location row. 146 → 148.

**No netcdf coverage matrix.** A 3-row matrix carries less than the case pages already do, and generalising the matrix generator is a separate deliverable. Record the decision so it is not mistaken for an oversight.

---

## Phase 4 — Vector: Z coordinates and the owed axis-order declaration

### 4.1 Tests first — `tests/unit/test_vector_dimensionality.py`, `tests/unit/test_catalog_axis_order.py`

- `test_polygon_z_case_carries_z_coordinates` — `geom.has_z`, every coord a 3-tuple.
- `test_polygon_z_survives_the_gpkg_transcoding` — `has_z` True with identical Z to 6 dp. This is what makes the pair worth two fixtures: WKB carries Z in its byte header, GPKG in its geometry flags, and a driver can drop it silently.
- `test_content_gate_enforces_expect_z` — `params.expect_z: true` against 2D → one error.
- `test_z_case_extent_ignores_the_third_dimension` — guards a real crash path in `catalog_extent.py`.
- `test_gml_baselines_declare_authority_axis_order` — parametrized over all six `*_gml_baseline`: `"axis_order" in risk_types`. Fails on all six today.
- `test_gml_file_contains_authority_order_coordinates` — **the whole gap in one test**: the raw bytes carry `urn:ogc:def:crs:EPSG::4326` with `gml:pos` lat-first, `VectorCase.load()` returns lon-first, and nothing in the catalog told the user that a naive text parse of these bytes gets a swap.

### 4.2 The axis-order declaration (bytes unchanged)

Add `axis_order` to `risk_types` on the six `*_gml_baseline` cases, and reproduce in their notes the explanation currently reachable only by reading `_spatial_reference()`'s docstring. Add a `check_vector_content` branch that reads the raw bytes for the URN form and asserts the first `gml:pos` ordinate is the latitude — without it the risk type is a label, which Plan 27 §1.2 forbids.

`out_of_bounds_coordinates` **does not** gain `axis_order`: it catches a swap only because lat=100 is out of range, which is a validity signal. Record the distinction in its notes rather than leave it to be rediscovered.

**This closes Plan 27 §1.3's owed row** — update that table from "Owed" to the check's name.

### 4.3 The Z fixtures — `scripts/generate_vector_fixtures.py`

Not family members (no `canonical_source_case_id`, no `cross_format_canonical`) — same choice Plan 33 made for the procedural cases, for the same reason: they vary a property the family holds constant. Add `_write_dimensional_cases()` beside `_write_procedural_cases()`.

- **`polygon_z_wkb`** — a 5-vertex closed ring with a Z ramp, e.g. `POLYGON Z ((12.50 55.70 0.0, 12.52 55.70 12.5, 12.52 55.72 25.0, 12.50 55.72 12.5, 12.50 55.70 0.0))`. Pure-shapely WKB, so `--check` stays a strict byte comparison.
- **`polygon_z_gpkg`** — the same WKT through `_write_ogr` with `wkbPolygon25D`. `_OGR_GEOMETRY_TYPES` has no Z entries; extend it keyed on a new `VectorSpec.has_z: bool = False` rather than by inventing a `"PolygonZ"` string, so `geometry_type` stays inside the values `SuiteSelection.geometry_type` filters on. Getting this wrong silently writes 2D — which is what the transcoding test catches.

**Rider (int64 > 2^53):** give the GPKG sibling `_ID_FIELD = 9007199254740993` instead of `1`, with `params.expected_id_value` and a check asserting exact read-back. One line, and it covers the expert's int64 gap without minting a case.

Watch for: Plan 33's `_decimate` in `catalog_geometry.py` now receives 3-tuples. Confirm it indexes `coord[0]`/`coord[1]` rather than unpacking, or page generation raises on the Z case.

### 4.4 Regenerate

Same order, substituting the vector generator and `generate_vector_coverage_matrix.py`. 148 → 150. Update count claims to whatever is **real**, not to this estimate.

---

## Phase 5 — Record what was cut

Append to the plan doc and cross-reference from `development-plan.md`'s backlog: alpha-band nodata (needs a v1.0 `Literal` break; revisit at v1.1), mixed-timezone datetimes (owned by Plan 28 Phase 3), curvilinear 2D grids (unblocked by Phase 1, the correct next NetCDF case), collinear vertices (assessed and declined — the expert's reading was inverted), overlapping MultiPolygon parts (declined).

---

## Verification

Every gate green under **conda `geocase`** (`osgeo` required — without it ~1200 tests silently skip), plus a `.venv` 3.11 run because Phase 1.0 changes the CI install set and the floor environment is what proves netCDF4 resolves against the pinned NumPy.

```bash
pytest tests -q && pytest examples -q
python scripts/build_case_index.py --check
python scripts/validate_catalog.py
python scripts/validate_case_content.py
python scripts/catalog_extent.py --check
python scripts/generate_raster_fixtures.py --check
python scripts/generate_vector_fixtures.py --check
python scripts/generate_netcdf_fixtures.py --check      # new
python scripts/generate_checksums.py --check
python scripts/generate_catalog_pages.py --check
python scripts/generate_raster_previews.py --check
python scripts/generate_vector_coverage_matrix.py --output docs/_generated/vector-coverage-matrix.md
python scripts/generate_raster_coverage_matrix.py --output docs/_generated/raster-coverage-matrix.md
ruff format --check src tests && ruff check src tests
mypy src && mkdocs build --strict
```

A clean `--check` sweep with a clean `git status` is the pass condition — any drift means a generator was skipped.

**End-to-end proof, required before marking any phase implemented** (the standard Plans 28 and 32 met — break it, watch the gate name the field, restore byte-identical):

1. Rewrite `bottom_up_dem_small.tif` with a negative-`e` transform → gate exits 1 naming `expected_transform_signs`.
2. Strip the `AREA_OR_POINT` tag → gate names `expected_pixel_anchor`.
3. Rewrite `polygon_z_wkb` as 2D → gate names `expect_z`.
4. Perturb `ndvi_packed_netcdf`'s `scale_factor` → gate names `expected_scale_factor`.
5. Reorder `cf_time_ordering_netcdf`'s dims to conventional → gate names `expected_dimensions`.

**Docs follow code, same change:** `docs/plans/index.md` gains a Plan 34 row; Plan 27 §1.3's table gains `transform_sign`, `time_parsing`, `integer_precision` and flips the owed `axis_order` row; Plan 28 Phase 4's backlog notes `south_up_transform` as delivered here; `CLAUDE.md`'s gate block gains the NetCDF generator; `docs/adding-a-case.md` gains the NetCDF path.
