# Plan 44 — GDAL as a *Target*, Not a Consumer: The Numeric Axis Pays, the Geometry Axis Does Not

> **Status: Phases 2–4 and 1.1 implemented 2026-09-10; Phase 1.2 and Phase 5
> outstanding.** The catalog work landed: the numeric-boundary family (Phase 2),
> the westward dateline raster (Phase 3), the `failure_mode/*` axis (Phase 4)
> and the two `known_divergences` records (1.1). Still owed: the
> [`docs/validation.md`](../validation.md) paragraph stating the negative result
> (1.2), and the whole of Phase 5 — neither GDAL draft has been written, there
> is no `issues/` directory, and the two standalone repro scripts
> (`repro_geojson_1e14_zeroed.py`, `repro_warp_zero_height.py`) do not exist in
> the tree. Nothing has been filed upstream.
> A round-6 run pointed the corpus at **GDAL itself** — the first time any round
> has treated the reference implementation as the target rather than the oracle.
> It produced **two defects in GDAL `d6fd56f52d`**, and the result that matters
> is not the count but *which cases produced them*: neither came from geometry,
> CRS or footprint — the axis [Plan 41](41-positioning-and-the-geometry-thesis.md)
> established as the paying one — and **every marquee raster convention case
> passed**. Phase 1 records the negative result, which is the load-bearing
> output. Phase 2 adds the numeric-boundary family the round exposed as a
> one-case accident. Phase 3 closes the dateline set's missing sign. Phase 4
> marks cases by *whose* failure mode they are, which this round proves the
> catalog cannot currently express. Phase 5 handles the two upstream drafts
> under [Plan 43](43-upstream-filing-queue-and-repo-liveness.md)'s rules.

## Context

A run on 2026-09-06 cloned `OSGeo/gdal` at `d6fd56f52d` and read the `1.0.0rc3`
corpus (166 cases) against it under GDAL Python 3.12.2 / Python 3.14.3, in four
internal differential sweeps plus an independent source-review pass. Harness,
frozen sweep output and standalone reproductions are in
`~/projects/geocase_validation/` (`findings/gdal/REPORT.md`,
`findings/gdal/COMPARISON.md`, `gdal/GEOCASE_FINDINGS.md`).

**This round is structurally different from rounds 1-5 and from
[Plan 41](41-positioning-and-the-geometry-thesis.md).** Plan 41's round was a
*GDAL-only consumer* — someone using GDAL to read the corpus. This one targets
GDAL's own code. That inverts the method: every prior round could use GDAL as
the oracle a consumer is measured against, and here there is no external oracle
at all. Only *internal* differentials are available — two GDAL read paths, or
two GDAL drivers, that must agree with each other. That constraint is the
finding-generator for the whole round and it is not something the corpus
currently ships.

| Sweep | Coverage | Result |
|---|---|---|
| `sweep_vector_arrow` | 91 vector cases, ArrowArrayStream vs `GetNextFeature` on count/FID/WKB | **0 divergences** (26 environmental skips: no `ogr_Arrow`/`ogr_Parquet` plugin) |
| `sweep_raster` | 46 rasters × 6 axes (stats vs numpy, `Info` corners vs affine, translate round-trip, full-buffer `RasterIO`, full-extent `-projwin`) | **0 divergences** |
| `sweep_vector_roundtrip` | 117 cases × 5 target drivers | **1 defect**; all other diffs documented driver behaviour |
| `sweep_reproject` | 46 rasters → EPSG:4326 and 3857, extent vs `pyproj` corners | **1 defect** |

### The two defects, and which case found each

**1. Coordinates in `[1e-14, 1e-13)` are silently written as `0` (MEDIUM).**
Both the WKT and the GeoJSON writers. Not a precision floor: the writer's
default is **15 decimal places** and `1e-14` is `0.00000000000001` — 14 places,
comfortably inside it. `ogr/ogrlibjsonutils.cpp:158` formats coordinates through
`OGRFormatDouble(dfVal, OGRWktOptions(15, /*round=*/true), 1)`, which calls
`intelliround()` at `ogr/ogrutils.cpp:161-169`. That branch tests
`s[len-3] … s[len-9]` for zeros, then drops the last **8** characters —
including `s[len-2]`, which it never tested and which for `"0.000000000000010"`
holds the only significant digit. Result `"0.0"`. Relative error **1.0**, no
error, no warning. A brute force over 300 000 coordinates puts the affected
class at exactly `|v| ∈ [1e-14, 1e-13)` — nine hits.

Found by **`precision_loss_geojson_roundtrip`**, feature 3 (`"Very small values
near zero"`, `[1e-14, 1e-14]`) — see Phase 2 for why this was luck.

**2. `AutoCreateWarpedVRT` returns a `23x0` dataset (MEDIUM).** PROJ wraps the
east edge of an antimeridian-crossing EPSG:4326 raster (`180.22°` →
`-20013018 m` in EPSG:3857) so the suggested output spans ~40 000 km in X and
~35 km in Y. `GDALSuggestedWarpOutput2` derives one square pixel size from the
diagonal, and at `alg/gdaltransformer.cpp:1141-1142`
`*pnLines = (int)(dfLines + 0.5)` rounds to **0** and the function returns
`CE_None`. The caller receives an invalid `GDALDataset` with `RasterYSize == 0`;
only a later `Create` produces an error, and it names the symptom
(`"Attempt to create 23x0 dataset is illegal"`), not the cause. The *too large*
direction is guarded twelve lines above; the *rounds to zero* direction is not.
The antimeridian branch that does exist (`gdaltransformer.cpp:1474-1491`) fires
only when the **destination** SRS is geographic, so a projected target gets no
wrap handling at all.

Found by **`optical_dateline_small`** — the only raster in the corpus whose
longitudes exceed ±180, and it reaches **180.22**. Plan 41 §3 already records
this footprint being unsplit as the property that produced that round's P1; this
is the second finding it has generated from the same property.

### The negative result is the load-bearing output

`bottom_up_dem_small`, `bottom_up_only_square`, `rotated_two_islands`,
`dem_nan_nodata_small`, `geotiff_int8_small`,
`landcover_ambiguous_zero_small`, `water_mask_small`, and the
`pixel_is_point`/`pixel_is_area` pair — **every one passed**. The
identity-warp axis flagged the two bottom-up rasters and the flag is a false
positive: warp flips the array *and* flips `gt[5]` to match, so the
georeferenced result is identical.

This is not a disappointing result, it is the correct one, and it should be
stated in the docs rather than buried. Round 1 found rio-tiler mis-handling
`bottom_up_dem_small`; Plan 41's round found a P1 from `rotated_two_islands`.
GDAL handles both. **Those cases are failure modes *for consumers of GDAL*, not
for GDAL** — their value is that they catch everyone downstream who assumes a
normalisation GDAL performs and they do not. The corpus currently has no way to
say that, which is Phase 4.

### And the numeric axis, which nothing has named

Both findings came from cases that are barely geospatial: a point at `1e-14` and
a longitude of `180.22`. **Numbers at a representational boundary, not
geometry.** Plan 41 concluded that geometry/CRS/footprint is the paying axis and
the machine-checked spec constants contributed zero; this round agrees that the
constants pay nothing and *disagrees* about geometry — against a reference
implementation, geometry pays nothing either, and a third axis nobody has named
pays twice.

Two rounds is not a trend. What is defensible today: the *productive* axis
depends on whether the target is a consumer or a reference implementation, and
the catalog is organised as though only the first kind of target exists.

### The review pass, and zero overlap for the third time

An independent source-review pass over
`swig/python/gdal-utils/osgeo_utils` found three API-contract defects the corpus
cannot reach — `ColorPalette.__eq__` raising `AttributeError` on unrelated types
(`color_palette.py:43`), `GeoRectangle` defining `__hash__` over fields it lets
you mutate so an instance is lost from its own set (`rectangle.py:263` against
`rectangle.py:66`), and `get_ovr_idx(ovr_res=(x, y))` raising `TypeError`
because `float(ovr_res)` runs three lines above the `Sequence` branch written
for it (`util.py:197` against `:203`).

**Zero overlap, again** — round 1 got 9 findings with zero overlap, round 6 gets
5. [Plan 37](37-raster-signal-and-differential-adapters.md) already bounds this;
round 6 adds one datum to it and nothing new, and the honest note is the scoping
cost: GDAL is ~1.5M lines, the review pass has no natural stopping point, and
finding 5's severity reflects exactly that — a real defect in a corner nobody
calls.

---

## Phase 1 — Record the negative result, and say what it means

**1.1** Add `known_divergences` entries for both GDAL findings, so a repeat run
is quiet: the `1e-14` coordinate class against
`precision_loss_geojson_roundtrip`, and the projected-target warp against
`optical_dateline_small`. Follow [Plan 37](37-raster-signal-and-differential-adapters.md)
Phase 1's shape, and note that `KnownDivergence` spells the case reference
`case_id` while `CaseMetadata` uses `id` — the mismatch
[Plan 41](41-positioning-and-the-geometry-thesis.md) records and has not fixed.

**1.2** Add a short section to [`docs/validation.md`](../validation.md) stating
the GDAL result plainly: *the convention cases pass against GDAL, and that is
the point.* This is the strongest available answer to the two prior evaluations
Plan 41 records rejecting geocase as "pixel-moving, GDAL-native" — it says
directly what the cases are for. Keep it to a paragraph; the file is already
carrying two corrections owed by [Plan 43](43-upstream-filing-queue-and-repo-liveness.md).

**1.3** Do **not** claim GDAL as a validated consumer in the count. Two findings
against a reference implementation, one of which required a brute-force sweep to
characterise, is a weaker claim than the consumer rounds and inviting the
scrutiny Plan 41 §6 anticipates. Record it as a *method* result.

## Phase 2 — The numeric-boundary family

`precision_loss_geojson_roundtrip` found finding 1 **by luck**. It carries three
points, and the third happens to be `1e-14` — the single magnitude where the
significant digit lands on the one string position `intelliround` does not test.
A case chosen for "very small values near zero" is not the same as a case
designed to sit on a formatting boundary, and the difference is the whole
finding.

**2.1** Add a numeric-boundary case family, single-variable per
[Plan 40](40-round-3-packaging-truth-and-vocabulary.md)'s control principle, with
coordinates chosen against the *formatter*, not against intuition:

- values needing exactly 15 vs 17 significant digits to round-trip;
- values whose decimal expansion at 15 places ends in five `0`s, and five `9`s —
  the two patterns `intelliround` special-cases, which is why
  `0.000000010000001` also loses its tail through this path;
- a value at each of `1e-13`, `1e-14`, `1e-15` so the boundary is bracketed
  rather than hit.

**2.2** Carry the expected round-trip value as a typed `AssertionHints` field,
**not** `params` — Plan 40 §2 is explicit that `params` is `dict[str, Any]` with
no validator and an unrecognised key is silently ignored. Without the hint every
consumer re-derives what "survived" means, which is the work Plan 41 §3 says the
best cases should hand over.

**2.3** Add a `numeric_precision` risk-type family under Plan 40 Phase 3's
canonical `RISK_TYPES` hierarchy. Today the corpus has one such case and calls
it `precision_loss`, a singleton among the 78 Plan 40 measured.

## Phase 3 — The dateline set's missing sign

`optical_dateline_small` is the only raster past ±180 and it crosses one way
(179.9 → 180.22). This run could not answer whether finding 2 is symmetric,
because there is no negative-wrap counterpart.

**3.1** Add a raster crossing westward (x from `-180.2` to `-179.9`), same size
and CRS, as a control. One file, and it directly tests the branch
`gdaltransformer.cpp:1474-1491` skips.

**3.2** Consider the vector equivalent against the existing antimeridian set —
lower priority, since the vector cases already cross both ways.

## Phase 4 — Say *whose* failure mode a case is

This round's central structural gap. A consumer sweeping the corpus against GDAL
spends a full run discovering that the convention cases pass; a consumer
sweeping a downstream library needs exactly those cases first. The catalog
cannot currently express the difference, and the metadata to express it already
half-exists.

**4.1** Add a case-level marker distinguishing *reference-implementation
failure modes* (a defect in GDAL/PROJ/GEOS itself) from *consumer failure modes*
(a correct normalisation downstream code assumes did not happen). The
convention cases — bottom-up, rotated, pixel-is-point/area, NaN nodata,
ambiguous zero, int8 — are all the second kind, and this round is the evidence.

**4.2** Prefer extending Plan 40 Phase 3's `RISK_TYPES` `family/specific`
hierarchy over inventing a parallel field, and make it selectable, so a harness
can ask for the right half before it runs rather than after.

**4.3** This is the concrete form of the suite ask
[Plan 41](41-positioning-and-the-geometry-thesis.md) Phase 1 identified as a
*build* rather than a discoverability fix. Sequence after Plan 40 Phase 3, which
owns the vocabulary.

## Phase 5 — The two GDAL drafts, under Plan 43's rules

**5.1** Write both drafts to `issues/`. Both have standalone reproductions that
build their own files and do not import geocase, both verified failing:
`repro_geojson_1e14_zeroed.py` and `repro_warp_zero_height.py`.

**5.2** Apply [Plan 43](43-upstream-filing-queue-and-repo-liveness.md)'s liveness
and duplicate check before either is filed. GDAL is unambiguously live, so the
real question is duplicates — search the tracker for `intelliround`,
`SuggestedWarpOutput` and zero-size warp output first.

**5.3** Rank finding 2 **above** finding 1 and expect them to land differently.
Finding 2 is clean: an invalid dataset returned with `CE_None`, a missing clamp
next to an existing guard, a fix under 20 lines with no API design choice — a
**file+PR** candidate under Plan 43's fourth action. Finding 1 is real silent
data loss with a source-confirmed cause, but the magnitude class is narrow and
`intelliround` is deliberate legacy heuristic whose own comment concedes the
intent is not understood; **expect a "won't fix, use `SIGNIFICANT_FIGURES`"
response**, and file it anyway, because that response is itself the external
evidence [Plan 39](39-going-public-upstream-first.md) §1.3 says is the output.

**5.4** The three `osgeo_utils` review findings are **not** worth a maintainer's
time individually. Fold them into one PR against `swig/python/gdal-utils` or
drop them; do not add three drafts to a backlog
[Plan 42](42-round-5-consumer-selection-and-the-unfiled-backlog.md) already
argues is too long.

**5.5** Honour Plan 43's week-1 embargo — the three open threads *are* the
experiment, and these filings wait for 2026-09-20 rather than contaminating it.

## Open questions

- **U24.** Is a third data point wanted before "the productive axis depends on
  target kind" is treated as settled rather than suggestive? Plan 42 Phase 3
  already selects Shapely-vs-pyogrio and DuckDB-vs-geopandas as *consumer*
  pairings; the reference-implementation equivalent would be **PROJ or GEOS as a
  target**, and neither is currently scheduled.
- **U25.** Does the corpus want an internal-differential instrument at all?
  Every instrument built so far (`geocase.stac`, `compare_arrays`) assumes an
  external oracle. Round 6's two productive sweeps — cross-driver round-trip and
  formatter round-trip — had to be hand-rolled, which is the mistake
  [Plan 37](37-raster-signal-and-differential-adapters.md) records as round 1's
  central failure.
- **U26.** Phase 4 changes a **pinned v1.0 selector surface**. Does it go in
  `1.1` with Plan 39 §3's other additive items, or does it wait?
