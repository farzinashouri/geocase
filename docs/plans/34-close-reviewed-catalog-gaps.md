# Plan 34 — Close the Reviewed Catalog Gaps

> **Status: implemented 2026-08-29.** All five phases landed. Catalog 143 → 150
> (7 new cases, one more than the planned 6: the pixel-anchor pair needed an
> explicit control). One subtraction, one generator built from nothing, and
> `expected_scale_factor` gated for the first time since it was introduced.

## Corrections applied before implementation (2026-08-29)

Verifying this plan against the code turned up eight factual errors and five open
decisions. They are recorded here rather than silently fixed in place, because a
plan that was wrong about where a symbol lives is evidence about how it was
written.

**Path corrections.** `AssertionHints` is `src/geocase/catalog/models.py:167-188`,
not `src/geocase/metadata/models.py`. The schema is
`src/geocase/metadata/schemas/case.schema.yaml`. Case data lives under
`src/geocase/data/core/{raster,vector,netcdf}/`; the GML baselines are at
`src/geocase/data/core/vector/<geom>/gml/<geom>_gml_baseline/`.

**§1.0's flagged unknown is resolved.** The worry that `netCDF4>=1.6` might not
resolve against the catalog job's `numpy<2` pin was probed in a throwaway
Python 3.11 venv: `numpy 1.26.4` + `netCDF4 1.7.4` + `xarray 2026.7.0` install
cleanly and round-trip a `to_netcdf`/`open_dataset`. **The `h5netcdf` fallback is
unnecessary**; the generator pins `engine="netcdf4"`.

**§4.3's int64 rider misread `_ID_FIELD`.** That constant
(`scripts/generate_vector_fixtures.py:163`) is the string `"id"` — a *field
name*. The value `1` is hardcoded separately at `:587`, `:647`, `:750` and in the
CSV writer. Editing the constant would change bytes in ~60 baselines and report
the entire family stale. The rider threads a new `VectorSpec.id_value: int = 1`
and overrides it for the Z-GPKG spec alone.

**§4.3's `_decimate` watch-item is already satisfied.** `scripts/catalog_geometry.py:98`
already slices `(c[:2] for c in coords)`, and `catalog_extent.py` reads
`total_bounds`, which is 4-length regardless of dimensionality. The Z test stays
as a regression guard; no work is owed.

**§1.3 was wrong that `expected_scale_factor` has a consumer.** The field is
declared in the model, the schema and three raster `case.yaml`s, but nothing in
`check_raster_content` reads it — a declared-but-ungated hint of exactly the
class [Plan 27](27-close-plan-26-findings.md) §1.2 forbids. See the decisions
table.

**§4.2 was wrong that Plan 27 §1.3 owes an `axis_order` row.** That table holds
one row, `ambiguous_zero`, still owed and untouched by this plan. The real
`axis_order` debt is Plan 27 **§1.1**'s proposed `axis_order_swapped_pair`, which
never shipped. §4.2 therefore *adds* a §1.3 row rather than flipping one.

**`south_up_transform`** is listed in [Plan 28](28-validate-geocase.md) as an axis
in `src/geocase/raster/axes.py`, not as a bundled case. Phase 2.4 delivers a
bundled case covering the same property; the axis itself stays owed.

### Decisions

| Question | Decision |
|---|---|
| `expected_scale_factor` | Gate it on **both** sides. Phase 2.3 adds `assert_scale_factor` and wires it into `check_raster_content`, closing the ungated hint on the three existing raster cases; Phase 1.3 then genuinely reuses it. |
| The `axis_order` debt | §4.2 **adds** a Plan 27 §1.3 row and closes Plan 27 §1.1: the six GML baselines genuinely carry authority-order bytes, so a synthetic `axis_order_swapped_pair` is redundant. |
| `latlon_small`'s `expect_crs` | **Remove** `expect_crs` and `expected_epsg` in the 3.2 subtraction. The file has no `grid_mapping` and no `crs` variable, so they are as undemonstrable as the two `risk_types` being dropped beside them. `check_netcdf_content` gates `expect_crs` **strictly** — an absent CRS variable *is* a finding — rather than carrying the permanent leniency §1.3 proposed. |
| New `risk_types` terms | **Skip** `transform_sign`, `time_parsing` and `integer_precision`. Only `axis_order` is added, and it gets a real check. The typed hints already carry these contracts, and Plan 27 §1.2 warns against singleton vocabulary nothing gates. |
| `expected_dimensions` / `expected_variables` / `expected_time_units` | Stay in **`params`** with matching `content.py` checks, per this plan's own structural constraint 2. §3.2's wording, which reads as though they become typed fields, is corrected. |

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

## Phase 1 — Make NetCDF reproducible (unblocking) — **implemented 2026-08-29**

**As built.** All of 1.0–1.5 landed as described, with three deviations worth recording.

*The `_semantic_signature` NaN trap.* The first working generator reported its own freshly written fixture as stale, on every run. xarray gives unpacked coordinate variables a `_FillValue` of NaN, and `nan != nan`, so a signature carrying a raw NaN can never compare equal to itself. `_round` now maps NaN to a sentinel string. A byte gate would never have surfaced this; a semantic one had to.

*`expect_crs` was decided here, not deferred.* §1.3 originally proposed treating an absent CRS variable as not-a-finding. Implemented strictly instead, and the check immediately failed `latlon_small` — which is the correct outcome, and exactly what the lenient reading would have hidden. Phase 3.2's subtraction of `expect_crs`/`expected_epsg` was pulled forward into this phase because the check could not be landed green without it.

*`_load_for_category` needed the branch predicted in the hazard list.* Added with the reasoning in a comment, in the same change as the carve-out removal.

Gates after this phase: 1820 passed / 37 skipped, `validate_case_content.py` green across all 143 cases (netcdf now genuinely checked rather than skipped), `mypy src` clean, every `--check` up to date. No case count change.

### 1.0 CI can run it

`.github/workflows/ci.yml:137` → `.[raster,vector,netcdf] "numpy<2"`, commented in the style of the existing `numpy<2` note.

**Verified 2026-08-29, so the `h5netcdf` fallback is dropped.** The concern was that netCDF4 wheels are built per-numpy-ABI. Probed in a throwaway Python 3.11 venv: `numpy 1.26.4` + `netCDF4 1.7.4` + `xarray 2026.7.0` resolve, import, and round-trip a `to_netcdf`/`open_dataset` without complaint. The generator pins `engine="netcdf4"`.

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

**`_load_for_category` must move in the same commit.** It (`content.py:576`) handles only `RasterCase` and `VectorCase` and ends in `raise TypeError`. Removing the carve-out without giving it a `NetCDFCase` branch breaks netcdf in *both* directions: an `expect_loadable: true` case falls through to `check_vector_content` and fails, while an `expect_loadable: false` case passes for the wrong reason, via the bare `except Exception`. `NetCDFCase.load()` already exists (`src/geocase/cases/netcdf.py:33`), so this is a three-line branch — but omitting it makes the phase's own gate lie.

Checks, all through `_collect`: `params.expected_dimensions` (**in declared order** — that is what makes dim-ordering checkable at all), `params.expected_variables`, `expect_nodata` → the variable declares `_FillValue`, `expected_scale_factor`, `params.expected_time_units`.

`expected_scale_factor` is **not** the reuse of a working check that this plan first assumed. The field is declared in `models.py`, in the schema, and by three raster `case.yaml`s, and nothing reads it — Phase 2.3 writes `assert_scale_factor` and wires it into `check_raster_content`, so that by the time this check exists the field is gated on both sides.

**`expect_crs` is checked strictly**, reversing this plan's first instinct. `latlon_small` declares `expect_crs: true` and `expected_epsg: 4326` with *no* `grid_mapping` or `crs` variable in the file, and the proposal was to treat an absent CRS variable as not-a-finding so the phase would not go red. That is the same leniency the plan condemns elsewhere: it would ship a check that cannot fail on the only case it runs against. Phase 3.2 removes the two undemonstrable declarations from `latlon_small` instead — beside the two `risk_types` it was already removing for the identical reason — and the check stays strict.

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

## Phase 2 — Transform sign and pixel anchor — **implemented 2026-08-29** (143 → 146)

**As built.** 2.1–2.5 landed as described. Four things to record.

*The bounds test was written backwards, and the fixture corrected it.* §2.1 specified `test_bottom_up_case_bounds_are_still_normalised`, asserting `bounds.bottom < bounds.top` "despite positive `e`". rasterio does **not** normalise: `BoundingBox` is computed straight from the affine, so `bottom_up_dem_small` reports `bottom = 4200360` against `top = 4200000`. The test is now `test_bottom_up_case_reports_inverted_bounds`, pinning the real behaviour, because that inversion *is* the trap — anything computing a height as `top - bottom` gets a negative number, and every other fixture in the catalog hides it. `catalog_extent.py` normalises independently, so the published extent is still correct.

*`expected_scale_factor` is now gated on both sides,* per the decision above: `assert_scale_factor` in `assertions/raster.py`, wired into `check_raster_content`. Three raster cases that had declared it since the raster action plan are checked against real band scales for the first time.

*`_COUNT_CLAIMS` was widened from 7 patterns to 12.* Four statements of the case count matched no pattern and would have drifted silently through this plan's three renumberings — README's "curated vector, raster and NetCDF files", `docs/index.md`'s description line and its "Browse all N cases" link, `getting-started.md`'s "browse all N cases". Verified by mutating one and watching the gate name it. This was not in the plan; it is the durable fix for a hazard the plan only worked around.

*Break/restore proof (verification steps 1–2), both passed.* Flipping `bottom_up_dem_small`'s `e` sign → exit 1 naming `expected_transform_signs`. Stripping `pixel_is_point_dem_small`'s `AREA_OR_POINT` tag → exit 1 naming `expected_pixel_anchor`, reading `'area'` rather than `None`, which is the documented default doing its job. Both restored byte-identical (`generate_raster_fixtures.py --check` and `generate_checksums.py --check` clean).

Gates: 1835 passed / 37 skipped, content validation green across 146 cases, every `--check` up to date, `ruff`/`mypy`/`mkdocs --strict` clean.

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

**And four sites it does not enforce.** `_COUNT_CLAIMS` (`validate_catalog.py:351`) gates seven files by regex, but `README.md:34` ("143 curated vector, raster and NetCDF files"), `docs/index.md:2` and `:29`, `docs/getting-started.md:16`, and `docs/contributing/releasing.md:62,122` all state the count in forms no pattern matches — they will go stale silently through all three renumberings. Run a plain `grep -rn '\b143\b'` (then 146, 148) after each regeneration rather than trusting the gate, and **widen `_COUNT_CLAIMS` to cover them** so the next plan does not rediscover this. The ungated *test* count (1701, in `getting-started.md:202` and `workflow.md:9`) also drifts as this plan's ~25 tests land.

---

## Phase 3 — NetCDF coverage, and the subtraction — **implemented 2026-08-29** (146 → 148)

**As built.** Both fixtures shipped and the subtraction landed (in Phase 1, as noted there). Four things to record.

*The packed fixture was first written with pre-packed integers, and xarray rejected it.* Handing `to_netcdf` `int16` storage values *and* a `scale_factor` encoding makes it try to pack them a second time; it fails on the dtype cast. The spec now carries **physical** values in `[-1, 1]` and lets the declared encoding do the packing — which is also the correct mental model: the spec says what the data means, the encoding says how it is stored.

*CF time units belong in `attrs`, not `encoding`.* The netCDF4 backend rejects `units` and `calendar` as encoding parameters outright. Since the coordinate holds raw integers rather than datetimes there is nothing for xarray to encode, so they are written as attributes and land on disk verbatim.

*A brittle test elsewhere broke, and it was the test that was wrong.* `test_select_by_category_netcdf` asserted `len(result) == 1` — true only while netcdf had exactly one case. Adding two broke a test of the *selector* for a reason unrelated to the selector. Rewritten to derive its expectation from the corpus, matching the sibling raster test one function above it.

*Break/restore proof (verification steps 4–5), both passed.* Perturbing `ndvi_packed_netcdf`'s `scale_factor` to 0.5 → exit 1 naming `expected_scale_factor` and printing the observed value. Transposing `cf_time_ordering_netcdf` to conventional `(time, latitude, longitude)` → exit 1 naming `expected_dimensions` and printing both orders. Both restored, `--check` and checksums clean.

**No netcdf coverage matrix**, as planned: a 3-row matrix carries less than the case pages already do, and generalising the matrix generator is a separate deliverable. Recorded here so it is not mistaken for an oversight. Both new cases carry a hand-written `region`, so their pages render a Location row despite `catalog_extent.py` computing no extent for the category (verified).

Gates: 1843 passed / 37 skipped, content validation green across 148 cases, every `--check` up to date, `ruff`/`mypy`/`mkdocs --strict` clean.

## Phase 3 — NetCDF coverage, and the subtraction

Depends on Phase 1 being green.

### 3.1 Tests first — extend `tests/unit/test_netcdf_fixtures.py`

- `test_packed_variable_unpacks_to_physical_units` — `mask_and_scale=False` gives `int16`; the default gives floats in [-1, 1]. **The pair is the test** — a consumer reading raw sees plausible integers, which is the failure mode.
- `test_cf_time_decodes_to_the_expected_calendar` / `test_cf_time_undecoded_is_raw_numbers` — same differential shape via `decode_times=False`.
- `test_dimension_order_is_non_conventional` — `list(ds["t2m"].dims) == ["longitude", "latitude", "time"]`, x before y.
- `test_latlon_small_no_longer_claims_undemonstrable_risks` — regression guard on the subtraction.

### 3.2 The subtraction — `netcdf/latlon_small/case.yaml`

Remove `coordinate_order` and `dimension_mismatch` from `risk_types`, **and `expect_crs`/`expected_epsg` with them** — the file carries no `grid_mapping` and no `crs` variable, so those two are undemonstrable on exactly the same grounds (see 1.3).

Rename the unvalidated `params.dimensions`/`params.variables` to `params.expected_dimensions`/`params.expected_variables`, which 1.3's check reads. They stay in `params` rather than becoming typed `AssertionHints` fields: structural constraint 2 prefers `params` plus a matching check, and a typed field would have to land in Phase 2.2's schema commit instead.

Record in `notes.md`. Same correction Plan 28 made to `landcover_small`.

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

**Fix the stale notes in the same pass.** Five of the six `notes.md` still quote pre-[Plan 33](33-relocate-canonical-geometries.md) geometry — `linestring_gml_baseline/notes.md` says `LINESTRING (10 50, 10.5 50.3, 11 50.1)` while its own `case.yaml` extent is Patagonia, and multipoint, multilinestring and multipolygon are wrong the same way. Only `point` was updated. Rewriting these notes without correcting the coordinates would re-certify the stale numbers. `_spatial_reference()`'s docstring has the same problem — its worked example is the pre-relocation Copenhagen point — so reproduce its *argument*, not its numbers.

`out_of_bounds_coordinates` **does not** gain `axis_order`: it catches a swap only because lat=100 is out of range, which is a validity signal. Record the distinction in its notes rather than leave it to be rediscovered.

**This adds a Plan 27 §1.3 row; it does not flip one.** That table holds a single row, `ambiguous_zero`, which stays owed and is not this plan's business. The `axis_order` debt that does exist is Plan 27 **§1.1**'s proposed `axis_order_swapped_pair`, which never shipped — and declaring the six GML baselines discharges it, because those bytes genuinely carry authority order on disk. A synthetic swapped pair would demonstrate less. Mark §1.1 delivered here.

### 4.3 The Z fixtures — `scripts/generate_vector_fixtures.py`

Not family members (no `canonical_source_case_id`, no `cross_format_canonical`) — same choice Plan 33 made for the procedural cases, for the same reason: they vary a property the family holds constant. Add `_write_dimensional_cases()` beside `_write_procedural_cases()`.

- **`polygon_z_wkb`** — a 5-vertex closed ring with a Z ramp, e.g. `POLYGON Z ((12.50 55.70 0.0, 12.52 55.70 12.5, 12.52 55.72 25.0, 12.50 55.72 12.5, 12.50 55.70 0.0))`. Pure-shapely WKB, so `--check` stays a strict byte comparison.
- **`polygon_z_gpkg`** — the same WKT through `_write_ogr` with `wkbPolygon25D`. `_OGR_GEOMETRY_TYPES` has no Z entries; extend it keyed on a new `VectorSpec.has_z: bool = False` rather than by inventing a `"PolygonZ"` string, so `geometry_type` stays inside the values `SuiteSelection.geometry_type` filters on. Getting this wrong silently writes 2D — which is what the transcoding test catches.

**Rider (int64 > 2^53):** give the GPKG sibling the id value `9007199254740993` instead of `1`, with `params.expected_id_value` and a check asserting exact read-back. It covers the expert's int64 gap without minting a case.

**Not by editing `_ID_FIELD`, as this plan first said.** That constant (`generate_vector_fixtures.py:163`) is the *field name* `"id"`; the value `1` is written separately at `:587` (OGR), `:647` (geopandas), `:750` (GeoJSON) and in the CSV writer. Changing the constant would rewrite the id column in ~60 baselines and report the whole family stale. Thread a new `VectorSpec.id_value: int = 1` and override it for this one spec at `:587`.

~~Watch for: `_decimate` now receives 3-tuples.~~ **Already safe** — `catalog_geometry.py:98` slices `(c[:2] for c in coords)` before `_decimate` sees a coordinate, and `catalog_extent.py` uses `total_bounds`, which is 4-length regardless of dimensionality. `test_z_case_extent_ignores_the_third_dimension` stays as a regression guard on a path that is already closed.

### 4.4 Regenerate

Same order, substituting the vector generator and `generate_vector_coverage_matrix.py`. 148 → 150. Update count claims to whatever is **real**, not to this estimate.

---

## Phase 4 — Vector: Z and axis order — **implemented 2026-08-29** (148 → 150)

**As built.** 4.1–4.4 landed. Four things to record.

*The `_ID_FIELD` misread was real and was avoided.* §4.3 said to set `_ID_FIELD = 9007199254740993`. That constant is the field *name* `"id"`; the value `1` is written separately in four places. Following the plan literally would have rewritten the id column in ~60 baselines. A `VectorSpec.id_value` field now carries it, overridden for the GPKG sibling alone — `generate_vector_fixtures.py --check` reports all 65 fixtures up to date, which is the evidence that nothing else moved.

*The stale GML notes were worse than reported.* Five of six quoted pre-Plan-33 geometry; the sixth, `point`, quoted Copenhagen while its file is Wellington — so **all six** were wrong. Each notes file now states its real geometry, read back from the fixture rather than retyped, alongside the new axis-order section. `_spatial_reference()`'s docstring has the same stale example; its *argument* was reproduced, not its numbers.

*Plan 27 §1.1 is partially closed, not wholly.* The `axis_order_swapped_pair` item is superseded — the GML baselines carry the property on real bytes, so a synthetic pair would demonstrate less. `crs_mismatch_overlay_pair`, the other case that section proposed, is untouched and still owed. §1.3 gained `axis_order` and `integer_precision` rows naming their checks; the pre-existing `ambiguous_zero` row stays owed, as it was not this plan's business.

*The `_decimate` watch-item was confirmed closed, not fixed.* Z never reaches the projection maths — `catalog_geometry.py:98` slices `c[:2]`, `catalog_extent.py` uses `total_bounds`. Both Z cases got correct extents on the first run. The test remains as a regression guard.

*Break/restore proof (verification step 3), passed.* Rewriting `polygon_z_wkb` as 2D → exit 1 naming `expect_z` and the offending row. Restored byte-identical.

Gates: 1873 passed / 37 skipped, content validation green across 150 cases.

## Phase 5 — Record what was cut

**Implemented 2026-08-29.** Cross-referenced from `development-plan.md`'s backlog.

| Item | Disposition |
|---|---|
| **Alpha band as nodata** | **Deferred to v1.1.** `NodataConvention` is a v1.0 `Literal`; extending it for one fixture is a compatibility break. `mask` already carries "validity lives outside the pixel values". |
| **Mixed-timezone datetimes** | **Deferred — owned by [Plan 28](28-validate-geocase.md) Phase 3.** The gap is real (no vector fixture has any datetime attribute), but it needs ~10k features to discriminate, and a two-feature version here would pre-empt that design with a fixture too small to work. |
| **Curvilinear 2D coordinate grids** | **Deferred, and now unblocked.** This was the strongest argument for building the NetCDF generator first. With Phase 1 landed it is the natural next NetCDF case, and it is the one this plan most regrets not reaching. |
| **Collinear vertices** | **Declined.** The review read this backwards: `fractal_coastline_polygon` states it has *no* collinear vertices as a deliberate property, and collinearity is already a benchmark trap category. A fixture would test `simplify()` tolerance — a library behaviour, not a data property. |
| **Overlapping MultiPolygon parts** | **Declined.** Same OGC-validity axis as the bowtie and touching-ring cases already shipped. It would add a case without adding a discriminating failure mode. |
| **`crs_mismatch_overlay_pair`** | **Still owed** by [Plan 27](27-close-plan-26-findings.md) §1.1 — noted here because Phase 4.2 closed that section's *other* item, and the remainder should not be lost with it. |
| **`ambiguous_zero`'s enforcing check** | **Still owed** by Plan 27 §1.3. Untouched by this plan; recorded so the two new rows beside it are not read as closing it. |

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
