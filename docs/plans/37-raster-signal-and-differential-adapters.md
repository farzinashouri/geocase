# Plan 37 — The Raster Corpus Earns Its Keep: Two rio-tiler Defects, and the Differential Adapter They Unblock

> **Status: Phases 1-3 implemented 2026-09-01; Phase 4 not started.** Phase 1
> records both rio-tiler divergences and gates the two affines; Phase 2 ships
> `compare_arrays`; Phase 3 lands the three cases (154 -> 157). Phase 4 is
> upstream filing, which [Plan 39](39-going-public-upstream-first.md) Phase 1
> sequences ahead of it and which is not geocase code. See *Implementation
> notes* at the foot of this document for what differed from the plan.
> An external differential run against four
> consumers — pyogrio, rio-tiler, geocube, fiona — found **two real defects in
> rio-tiler 9.4.3**, and both came from the **raster** corpus. That is the
> signal [Plan 28](28-validate-geocase.md) Phase 4 was waiting for and
> [Plan 36](36-rc3-release-runbook-and-crs-mismatch.md) recorded as declined,
> so this plan is the one that spends it. A follow-up review pass without the
> corpus then found four *more* issues across the same libraries with **zero
> overlap**, which is recorded here because it bounds what this corpus can and
> cannot reach. Phase 1 records the divergences and makes them regression-gated; Phase 2 builds the raster adapter protocol Plan
> 28 Phase 4 specified but did not start; Phase 3 widens the transform-convention
> axis that produced both findings.

## Context

A validation run on 2026-08-31 read the 1.0.0rc3 corpus (154 cases) with four
consumers under GDAL 3.12.2 / Python 3.14.3, using the differential shape
[`geocase.differential`](../../src/geocase/differential.py) documents: read each
case two or three ways that must agree, and report the disagreement. Full report,
harness and standalone reproductions are in
`~/projects/geocase_validation/` (`findings/REPORT.md`).

| Consumer | Version | Result |
|---|---|---|
| **rio-tiler** | 9.4.3 | **2 real defects**, both silent, both geographic correctness |
| fiona | 1.10.1 | 1 driver-support gap (`KML`/`LIBKML` excluded from `supported_drivers`; the error message misattributes the cause) |
| geocube | 0.7.1 | clean **to the corpus** — 89 vector cases × 3 rasterization routes, 0 divergences. A later code-review pass found a real defect the corpus did not reach (see *A second method, and zero overlap*). |
| pyogrio | 0.12.1 / 0.13.0 | **2 defects, both missed by this run** — the two [Plan 28](28-validate-geocase.md) already records. Re-verified live on 0.12.1 *and* the latest 0.13.0 / GDAL 3.12.4; neither was fixed upstream. See *The two pyogrio bugs this run missed*. |

### The two defects, and which case found each

**1. Rotated rasters are silently mis-georeferenced (HIGH).** `Reader.read()`,
`.part()` and `.preview()` all return geographically wrong pixels when the affine
carries rotation terms. `read()` returns the raw rotated array while
`ImageData.bounds`/`.transform` describe a north-up grid. Against a `WarpedVRT`
reference of 7 valid pixels: `read()` 9, `part()` 4, `preview()` 9. No error, no
warning. Root cause is two lines: `rio_tiler/io/rasterio.py:100` wraps a dataset
in a `WarpedVRT` only `if self.dataset.gcps[0]`, and `rio_tiler/models.py:606`
builds `ImageData.transform` unconditionally from `from_bounds(...)`, which is
north-up by construction. Nothing in rio-tiler inspects `transform.b`/`.d`.

Found by **`rotated_two_islands`** — the **only** rotated raster in the corpus.

**2. Bottom-up rasters give inverted bounds and break `feature()` (MEDIUM).**
A positive-`e` affine is valid and rasterio reads it. rio-tiler propagates the
inverted `BoundingBox` (bottom > top) onto `Reader.bounds`, so
`bounds[3] - bounds[1]` is negative; `feature()` then raises `WindowError` while
`part()` over the identical area succeeds. `rio_tiler/reader.py:487` calls
`windows.from_bounds` with no ordering normalisation and `:58` computes
`y_res = (bounds[3]-bounds[1])/height` with no `abs()`.

Found by **`bottom_up_dem_small`** — the **only** bottom-up raster in the corpus,
added by [Plan 34](34-close-reviewed-catalog-gaps.md) §2 with the explicit
rationale that *"all 32 rasters use `from_origin`, so a consumer assuming
north-up passes the entire catalog."* That hypothesis is now confirmed against a
real consumer, by the case written for it, on the first run.

### Why this changes a standing verdict

[Plan 28](28-validate-geocase.md)'s framing is *"the corpus works on the vector
side and does not yet earn its keep on the raster side"*, drawn from a rio-tiler
run that found **0 bugs**. [Plan 36](36-rc3-release-runbook-and-crs-mismatch.md)
then put Plan 28 Phase 4 out of scope with *"entry condition unmet — the only
raster signal declined."*

Both statements were correct when written and are now **falsified by the same
consumer that produced them**. The difference is not the library and not the
version; it is that the earlier run tested *conformance against declared truth*
over format-coverage baselines, and this one ran a *differential over transform
conventions*. Two cases out of 34 carry a non-`from_origin` affine. Both found a
defect. The other 32 found nothing.

That is the same pattern Plan 28 recorded for the pyogrio run — findings come
from cases built around a **named failure mode**, not from format coverage — and
it now holds on the raster side too. The corpus axis that pays is *convention
divergence*, and the corpus currently samples it **twice**.

### A second method, and zero overlap

After the corpus run, the same four libraries were reviewed **without the corpus** — source
at HEAD plus targeted probes. It found four more issues, and **none of them overlap with the
three the corpus found**:

| Library | **GeoCase only** (review missed) | **Review only** (GeoCase missed) | Both | Total |
|---|---|---|---|---|
| rio-tiler | **2** — rotated affine; bottom-up bounds | **1** — `ImageData.mask` contract | 0 | **3** |
| fiona | **1** — KML/LIBKML unreadable | **2** — `Object.__eq__`; `Feature.__eq__` | 0 | **3** |
| pyogrio | **2** — `fid_as_index`+Arrow; GPKG spatial filter | 0 | 0 | **2** |
| geocube | 0 | **1** — `fill` ignored by default point method | 0 | **1** |
| **Total** | **5** | **4** | **0** | **9** |

The two pyogrio findings are the **prior** run's; this run missed them as well (§ below).
The `ImageData.mask` miss is the sharpest of the four: the harness ran *past* it, because it
compared `mask > 0`, which is correct at every dtype and therefore cannot see the defect.
fiona's two `__eq__` defects are **structurally unreachable** by a corpus of test data — no
file appears anywhere in their reproduction, which is a permanent ceiling worth stating in
the docs rather than rediscovering per consumer.

The review findings are `ImageData.mask` violating its documented uint8 0/255 contract for
every non-uint8 dtype; fiona's `Object.__eq__` raising instead of returning `False` (fixed on
`main` by #1488, **unreleased**); fiona's `Feature.__eq__` with the same defect **still
unfixed**, missed by that very fix; and geocube's ignored `fill`.

**Why this matters to geocase and not just to the four libraries.** The two methods fail in
opposite directions, and the split is structural rather than incidental:

- The corpus reaches what only a real file can express. Both rio-tiler transform defects are
  properties of an affine on disk; a reviewer finds them only if he already suspects rotation
  and bottom-up conventions, and a reviewer who suspects them has already found the bug.
- Review reaches what **no file can express**. fiona's two `__eq__` defects have no file
  anywhere in the reproduction. A corpus of test *data* cannot reach a bug in comparison
  semantics, however large it grows. That is a permanent ceiling on this corpus, and it is
  worth stating plainly in the docs rather than discovering per-consumer.
- One review finding, `ImageData.mask`, was **in front of the harness and hidden by it**: the
  sweep compared `mask > 0`, which happens to be correct at every dtype, so a stricter
  comparison would have caught it and the chosen one could not. Phase 2.2's `compare_arrays`
  should therefore compare masks by **exact equality**, not by truthiness — this is a third
  design requirement alongside the two already listed there.

None of this argues the corpus is not worth it; it argues against quoting a clean corpus run
as evidence a library is clean. geocube is the worked example: 0 divergences over 89 cases,
and a real defect one code-read away.

### The two pyogrio bugs this run missed — and what they prove about the harness

Plan 28 records two real pyogrio defects. **This run found neither**, and both are still
live: re-running the original repros reproduces them on 0.12.1 *and* on the latest **0.13.0 /
GDAL 3.12.4**, so neither was fixed upstream.

- **`fid_as_index=True` + `use_arrow=True` → `ValueError: Index data must be 1-dimensional`.**
  Reproduces on **GeoJSON only** — GPKG, Shapefile, FlatGeobuf and SQLite all pass. This run
  probed it against a single ad-hoc **GPKG**, the one format that works. The corpus holds
  **44 GeoJSON cases**, any of which would have caught it.
- **GPKG spatial filter + Arrow admits the NULL-geometry row (2 vs 3).** This run's
  differential compared *unfiltered* reads only and never passed `bbox=` or `mask=`. The
  corpus contains `empty_geometry_gpkg` for exactly this, and that case **already carries a
  `known_divergences` entry naming `pyogrio >=0.11, GDAL 3.12-3.13`** — the environment this
  run was executing in.

**Neither miss is a corpus deficiency. Both are harness deficiencies**, and they point at the
same root cause: the run **hand-rolled a comparison instead of calling `compare_cases()`**,
and the hand-rolled one varied only *library A vs library B on a plain read*. Both pyogrio
defects live in **option space** — one library, two code paths, under a specific option
(`fid_as_index`, a spatial filter). The harness never entered it.

**This changes Phase 2's scope, and is the most useful thing this run produced for geocase.**
A corpus finding needs a *case* **and** the *option combination that makes the case
discriminate*. `empty_geometry_gpkg` is inert without `bbox=`; 44 GeoJSON files are inert
without `fid_as_index=True`. Shipping files and leaving each consumer to invent the
comparison reproduces exactly this failure — which is what happened here, to a run that had
the documented divergence sitting in the case metadata it had already loaded.

So Phase 2 should ship **documented consumer option-pairs** alongside `compare_arrays`, not
just the array comparator: a small registry of the two-path shapes worth sweeping
(numpy vs Arrow; with and without `fid_as_index`; with and without a spatial filter;
`read()` vs `part()`), so the next run sweeps option space by default instead of rediscovering
that it must. §2.3 currently documents *one* worked example; it should document the set, and
`known_divergences` should be checked to have fired at least once per recorded consumer, since
a run that never enters the option space of a recorded divergence will silently report clean.

### What this plan does not claim

- Not a verdict on raster **oracles**. Both findings came from consumer-vs-itself
  comparison; neither needed geocase to know the right answer. Plan 28's
  scepticism about building raster oracles stands untouched.
- Not a reason to grow the raster corpus generally. The 32 `from_origin`
  baselines produced nothing here and this plan adds no more of them.
- **pyogrio is not clean** — this run missed two live defects the corpus had already
  found once (§ *The two pyogrio bugs this run missed*). No new case work is owed: the
  cases exist. **geocube is not clean either** —
  it read clean under 89 cases × 3 routes, and a code-review pass then found that
  `rasterize_points_griddata`'s default `method="nearest"` silently ignores `fill`. No
  geocase *case* work is owed either way, but the corpus's "clean" verdict on geocube
  should not be quoted as evidence the library is clean.

---

## Phase 1 — Record the divergences, and gate them

The two findings are consumer defects, not corpus defects, so nothing in
`case.yaml` is wrong. What is missing is the record: a repeat run must report
them as `known` rather than re-deriving them, which is exactly what
`CaseMetadata.known_divergences` exists for.

### 1.1 Record both, keyed on the consumer (TDD) -- **done**

**Failing test first:** `tests/unit/test_known_divergences.py` — assert that
`get_case("rotated_two_islands").known_divergences` contains a record with
`consumer == "rio-tiler"`, and the same for `bottom_up_dem_small`. Watch both
fail on an empty list.

Then add a `known_divergences` entry to each `case.yaml`, describing the defect,
the affected API surface, and the version observed (9.4.3). Follow the existing
`empty_geometry_gpkg` record, which is the only one in the corpus today, for
wording and field use.

`_match_known` matches on consumer name alone, so both records must name
`rio-tiler` exactly as a differential run's `consumer=` argument will.

### 1.2 Regenerate and re-gate -- **done**

`known_divergences` is part of the model, so the per-case catalog pages and the
content gate both move. Run `scripts/build_case_index.py --check`,
`scripts/validate_catalog.py`, `scripts/validate_case_content.py` and
`scripts/generate_catalog_pages.py --check`; regenerate and commit what they name.

### 1.3 Land the reproductions as fixtures, not prose -- **done**

**Failing test first:** `tests/unit/test_transform_conventions.py` — assert that
`rotated_two_islands` has non-zero `transform.b`/`transform.d`, and that
`bottom_up_dem_small` has `transform.e > 0`, reading the real bytes. Watch it
fail if either case is ever regenerated north-up.

This is the guard that matters most: both defects were found *because* those two
files carry a convention nothing else in the corpus carries, and a future
fixture regeneration that quietly normalises them would delete the corpus's only
coverage of the axis with a 2-for-2 hit rate.

---

## Phase 2 — The raster adapter protocol (Plan 28 Phase 4)

[`differential.py`](../../src/geocase/differential.py) is explicitly *"scoped to
the vector / two-code-path shape the evidence covers; the raster adapter protocol
is Phase 4 and is not started."* The entry condition was raster evidence. It now
exists, and the validation run had to hand-write the raster comparison that
should be library code.

### 2.1 What the hand-written harness did, and what to keep

The run's `run_riotiler.py` compared, per case: `read()` vs `part()` at native
size, `read()` vs `preview()`, and rio-tiler's mask vs `rasterio.dataset_mask()`.
Three things it got wrong on the first pass are the design requirements:

- **NaN-vs-NaN must compare equal.** `np.array_equal` reports every NaN-nodata
  raster as diverged; two of the three initial "findings" were this and nothing
  else. `default_compare`'s `_is_missing` already solves the scalar case; the
  array case needs the same treatment.
- **Masks are a separate finding from values, and must be compared exactly.**
  `rotated_two_islands` diverged on both; a comparator that only checks values reports
  half the defect. Compare masks by **equality, not truthiness** — the harness's
  `mask > 0` is correct at every dtype and for that reason stepped over rio-tiler's
  `ImageData.mask` contract defect entirely.
- **Shape mismatch must short-circuit**, exactly as `_frames_differ` checks shape
  before contents, or the reported difference is unreadable.

### 2.2 `compare_arrays` (TDD) -- **done**

**Failing test first:** `tests/unit/test_differential_raster.py` — two arrays
equal but for a NaN in the same position compare **equal**; two differing in one
cell report that cell; two of different shape report the shape. Watch it fail on
a missing function.

Add `compare_arrays(left, right)` to `differential.py` beside `default_compare`,
returning the same `str | None` contract so it drops into `compare_case`'s
`compare=` parameter with no change to `compare_case` itself.

### 2.3 A raster reader signature -- **done**

`Reader` is `Callable[[Path], Any]` and already fits — a raster reader is a
callable taking the primary file's path. Confirm with a test that
`compare_cases(..., category="raster", compare=compare_arrays)` runs end to end
over the 34 raster cases, and **document** the two-path raster shape in the module
docstring beside the pyogrio example, using the rio-tiler `read()` vs `part()`
pair that found the defect as the worked example.

No change to `compare_case`, `compare_cases` or `Outcome` is expected. If one
turns out to be needed, that is a finding worth recording in this plan rather
than absorbing silently.

---

## Phase 3 — Widen the axis that paid

Two cases, two defects. The axis is under-sampled, and unlike case *count* this
is a cheap, bounded addition: each case is a small synthetic GeoTIFF differing
from an existing one only in its affine.

### 3.1 The gap, measured

Of 34 rasters: **1** rotated, **1** bottom-up, **32** `from_origin`. No case
combines rotation with a bottom-up affine, none carries a rotation large enough
to move a pixel more than one cell at the corpus's 8–16 px sizes, and none pairs
a rotated source with its correctly-warped reference.

### 3.2 Add, in this order (TDD, one failing content-gate assertion each) -- **done**

1. **`rotated_bottom_up_small`** — both conventions at once. rio-tiler's two
   defects have adjacent root causes and a single `WarpedVRT` guard fixes both;
   a case carrying both is what proves a fix is complete rather than partial.
2. **`rotated_steep_small`** — a rotation angle large enough that a north-up
   assumption misplaces pixels by several cells, so the failure is unmistakable
   rather than a one-pixel edge effect. `rotated_two_islands` at 8×8 diverged on
   17/64 pixels; that is already good, and a steeper case makes the *direction*
   of the error legible in a report.
3. **`rotated_two_islands_warped`** — the `WarpedVRT` of `rotated_two_islands`,
   shipped beside it as the declared correct answer, following the
   `crs_mismatch_overlay_pair` precedent from
   [Plan 36](36-rc3-release-runbook-and-crs-mismatch.md) §2: a relationship
   between two inputs, expressed as a pair.

Each needs a `case.yaml`, a generator entry in
`scripts/generate_raster_fixtures.py`, checksums, and a content-gate assertion
that reads the real affine. `risk_types` reuses the vocabulary Plan 34 §2
established for the bottom-up case rather than minting new terms — Plan 28 §
"risk_types is not yet a vocabulary" applies.

### 3.3 Do not add

No more `from_origin` baselines, no larger rasters, and no new formats. The 32
existing baselines produced nothing in this run and the finding is about
convention, not coverage or scale.

---

## Phase 4 — Close the loop upstream

The defects are rio-tiler's and are fixed in rio-tiler; geocase's obligation is
the reproduction and the record.

### 4.1 Upstream reports

Both reproductions are standalone — they build their own GeoTIFF and import only
`rasterio`, `affine` and `rio_tiler`, so neither asks a maintainer to install
geocase. File them with the root-cause line numbers and the suggested single-guard
fix. The upstream planning is delegated to `opensource-contributor-7db927`, which
holds the report and the scripts.

### 4.2 Record the outcome where the claim lives

`docs/geocase_validate/` holds the two prior external runs and is what
[Plan 28](28-validate-geocase.md) reasons from. Add this run's report beside them,
and add a line to Plan 28's verdict table recording that its raster verdict was
overturned, by which cases, and on what date. A plan whose premise has been
falsified and does not say so is the failure mode Plan 28 itself was written
against.

### 4.3 The fiona gap

Low value and not a crash: `KML`/`LIBKML` are commented out of
`fiona/drvsupport.py`, so the exclusion is deliberate and the defect is the error
message. No geocase case work is owed. The 7 KML cases already behave correctly —
they read under pyogrio and fail under fiona, which is a true fact about fiona.
Worth one line in `docs/dataset-catalog.md` noting that KML cases are not
readable by a fiona-based consumer, since a user hitting it today gets a driver
error that blames GDAL.

---

## Verification

```bash
conda activate geocase
pytest tests -q
python scripts/build_case_index.py --check
python scripts/validate_catalog.py
python scripts/validate_case_content.py
python scripts/generate_raster_fixtures.py --check
python scripts/generate_checksums.py --check
python scripts/generate_catalog_pages.py --check
ruff format --check src tests && ruff check src tests
mypy src
mkdocs build --strict
```

Plus the finding this plan exists for, re-run end to end:

```bash
# in the validation env, with rio-tiler installed
python ~/projects/geocase_validation/findings/repro_riotiler_rotated.py
python ~/projects/geocase_validation/findings/repro_riotiler_bottomup.py
```

Phase 3 lands 154 → **157** cases; the count gate fires in seven files
([Plan 36](36-rc3-release-runbook-and-crs-mismatch.md) §2 measured this) and each
must be updated.


---

## Implementation notes (2026-09-01)

What differed from the plan as written.

**Phase 1 had partly landed under Plan 38, and the gap was invisible.** The
round-2 pass added `titiler` and `rio-stac` records to `rotated_two_islands` and
`bottom_up_dem_small`, so both cases had a non-empty `known_divergences` and
looked done. Neither carried a **`rio-tiler`** record. `_match_known` matches on
consumer name alone, so a differential run passing `consumer="rio-tiler"` -- the
run this plan exists to serve -- would have reported both defects as new and
re-derived a closed investigation. The records are now separate and explicit,
gated by `TestRoundOneConsumerDivergences` in
`tests/unit/test_known_divergences.py`. *A case with a divergence record for
some other consumer is not the same as a case with a record for yours.*

**Phase 2 landed as specified.** No change was needed to `compare_case`,
`compare_cases` or `Outcome`, as the plan predicted. `compare_arrays` was added
beside `default_compare` with the same `str | None` contract, plus a private
`_nan_positions` helper -- `np.isnan` raises `TypeError` on integer and object
arrays rather than returning all-`False`, and a raster corpus carries plenty of
both. Two behaviours beyond the plan's three:

- **Masked arrays are handled.** `rasterio.read(masked=True)` returns them
  routinely, so the mask is compared first and as its own finding, and data
  *under* the mask is ignored. Two masked arrays whose fill values differ under
  an identical mask therefore agree -- otherwise every `-9999` vs `nan` fill
  pairing reports as a divergence, which is the same class of noise as the
  NaN-vs-NaN mistake.
- **The detail reports the count of differing cells**, not only the first index.
  `rotated_two_islands` diverged on 17 of 64 pixels; "1 cell" and "17 cells"
  need different triage and the first index alone does not distinguish them.

**Phase 3's third case is a separate case, not a sidecar.** The plan said
`rotated_two_islands_warped` ships "beside" `rotated_two_islands`. It is a
distinct case id with the warped reference as its own sidecar, because adding a
reference to `rotated_two_islands` would change what that case tests -- its
value is that a consumer meets a rotated affine with **no** reference at all,
which is the condition under which rio-tiler returned three different answers.
`RasterSpec` gained `emit_warped_reference`, so the reference is derived from
the primary's own bytes rather than authored and cannot drift from the source it
is the answer to.

**Measured, not assumed:** `rotated_steep_small` displaces the far corner by
**10.07 cells** against a north-up reading (the plan asked for "several"), and
`rotated_bottom_up_small` by 3.2 cells while also carrying `e > 0`. Both are
asserted from the real bytes in `tests/unit/test_transform_conventions.py`
rather than from `case.yaml`.

**The count gate fired in exactly the seven files Plan 36 §2 measured** --
`README.md`, `docs/contributing/{releasing,structure-and-planning,workflow}.md`,
`docs/getting-started.md`, `docs/index.md`, `recipe/meta.yaml` -- all updated
154 -> 157.

**Phase 4 is not started.** §4.1 (upstream filing) is sequenced by
[Plan 39](39-going-public-upstream-first.md) Phase 1, which deliberately puts
filing ahead of the rest of that plan; §4.2 (recording the run beside the other
two, and correcting Plan 28's verdict table) and §4.3 (the one-line fiona note
in `docs/dataset-catalog.md`) remain open.
