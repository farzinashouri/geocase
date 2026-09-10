# Plan 42 — Round 5: Choosing the Next Consumers, and the Backlog That Should Go First

> **Status: proposed 2026-09-05.** `1.0.0` is live. The question this plan
> answers was asked directly: *test against another library, or re-run the ones
> already tested?* The measured answer is **neither, first**. Four rounds have
> produced ~32 defects across ten libraries and **17 upstream drafts remain
> unfiled**, while [Plan 39](39-going-public-upstream-first.md) — whose central
> claim is that the filings are the only action producing *external* evidence
> and must precede everything else — has had its Phase 3 (cut `1.0.0`) executed
> **ahead of** its Phase 1 (file three issues). A fifth round adds findings to a
> pile nobody outside this repository has yet agreed with. Phase 1 is therefore
> the backlog, not the round. Phases 2–4 then run the round properly, and the
> consumer selection is derived from evidence rather than from what is popular:
> [Plan 41](41-positioning-and-the-geometry-thesis.md) established that
> **geometry, CRS and footprint** are the paying axis, and
> [Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md) established that the
> strongest instrument is **two independent implementations of one operation**.
> Every prior round's instrument was raster-side; the corpus is **117 vector
> cases against 46 raster**, and the paying axis has never been run with the
> paying instrument.

## Context

The prompting question, answered in order.

### Re-running the already-tested consumers is a regression check, not evidence

It answers *"did `rc3 → 1.0.0` change any consumer's behaviour?"* — a real
question with an almost certainly negative answer, since neither pinned
compatibility surface moved between them. It is worth **one** targeted check
rather than a re-run, and the check is not differential:

[Plan 40](40-round-3-packaging-truth-and-vocabulary.md) §1 recorded a hard
packaging regression — `pip install "geocase[all]"` into a venv with
`--system-site-packages` over GDAL 3.6.2 / geopandas 0.12.2 pulled numpy 2.4.6
against scipy 1.10.1 and left pandas unimportable. Plan 40 is implemented, so
the fix is in `1.0.0` and **has never been verified against the environment that
broke**. That is the single re-run worth doing, it takes minutes, and it is
Phase 2.1. A full differential re-run of pyogrio/rio-tiler/titiler/stackstac/
odc-stac/lonboard/geoarrow-python would consume days to re-derive findings
already recorded in [`docs/validation.md`](../validation.md).

The one genuine risk a re-run would cover is the class
[Plan 40](40-round-3-packaging-truth-and-vocabulary.md) §2 names: the
`polygon_*_baseline` fix was correct and **silently** reddened a downstream
canary. But Plan 40 Phase 5 already addressed that by making `CHANGELOG.md` name
which case geometries changed, and the corpus grew 154 → 166 across these plans.
The mitigation is the changelog convention, not a re-run.

### The backlog is the blocker, and the sequence has already been violated once

| Plan 39 phase | intended order | actual state, 2026-09-05 |
|---|---|---|
| Phase 1 — file 3 of 17 drafts | **first** | **not done** |
| Phase 3 — cut `1.0.0` | after Phase 1 + 2 weeks | **done** |

Plan 39's argument for that order is not stylistic. Its words: the filings are
*"the only action producing external evidence"*, and *"if two of three come back
known, intentional or wrong, that is better learned from a GitHub thread than
from a comment under a LinkedIn post."* That risk is now larger, not smaller,
because `1.0.0` is published: a reader who arrives at
[`docs/validation.md`](../validation.md) reads 26 confirmed defects against named
libraries followed by *"Nothing has been filed upstream. These are drafts."*

Running a fifth round before filing makes the ratio worse — more accusations,
still zero third-party agreement. **Three runs have established that the corpus
finds real defects and zero have established that anyone outside this repository
wants them** ([Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md) §5).
Round 5 does not change that number. Filing does.

### If a round does run, the selection is derivable rather than arbitrary

Two findings from prior rounds constrain it.

**The paying axis is geometry/CRS/footprint.**
[Plan 41](41-positioning-and-the-geometry-thesis.md): every finding from the
GDAL-only consumer came from geometry, CRS and footprint cases, while the
machine-checked spec constants contributed **zero**. The corpus is already
weighted that way — 117 vector, 46 raster, 3 NetCDF — and the top risk terms
after `nodata/ignored` are `crs/zone_selection`, `crs/axis_order`,
`crs/reprojection_error`, `geometry/silent_invalid`, `geometry/topology_error`,
`extent/antimeridian`, `extent/polar`, `footprint/generation_error`.

**The strongest instrument is two independent implementations of one operation.**
[Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md): stackstac against
odc-stac produced the round's sharpest findings *by construction*, because
neither can be assumed correct. Conformance-against-declared-truth found much
less.

Crossing the two gives the gap: **every instrument built so far is raster-side.**
`geocase.stac` is a STAC-Item adapter; `compare_arrays` compares arrays. The
vector corpus — the larger and, per Plan 41, the better-paying half — has never
been run through an independent-implementation differential. Round 1 read
pyogrio against fiona, which is *one* engine (GDAL) behind two bindings; a
disagreement there is a binding bug, and the absence of one proves nothing about
GDAL.

The independent pairing the corpus has never used is **GEOS against GDAL**, and
**Shapely 2.x vs pyogrio/OGR** is exactly that: two genuinely separate geometry
engines computing the same predicates over the same bytes.

## Candidate consumers, ranked

| # | Consumer / pair | Instrument | Why this one |
|---|---|---|---|
| 1 | **Shapely 2.x (GEOS) vs pyogrio/OGR** | independent-implementation differential | Two separate engines, one operation — validity, area, bounds, `make_valid`, predicates — over the 117 vector cases. Directly targets `geometry/silent_invalid` (4 cases), `geometry/topology_error` (3), `extent/antimeridian` (3). No prior round has crossed engines on the vector side. |
| 2 | **DuckDB `spatial`** | corpus-as-stimulus + differential vs geopandas | Bundles its **own** GEOS/PROJ/GDAL, so it is an independent stack rather than another binding. Rapidly adopted in analytics pipelines that have never seen a rotated transform, an ESRI CRS code, or `nodata=0`. `ST_Read`/`ST_Area`/`ST_Transform` against geopandas is a clean pair. Untested by any round. |
| 3 | **rioxarray vs `WarpedVRT`** | differential against a reference | Plan 38 showed `raster:bands` scale/offset handling diverges between implementations; rioxarray's masking + scale/offset path is widely trusted and untested here. Uses the existing `compare_arrays`, so setup cost is near zero. |
| 4 | **pyproj (re-run, targeted)** | conformance | Came back **clean under both methods** in Plan 38 — the only consumer that did. Worth one narrow re-run against the polar (5) and antimeridian (3) cases specifically, since the clean result may be a coverage artefact of what that run passed it. |

Deliberately excluded: GeoPandas as a *target* (it is the reference in pairs 2
and 3 and cannot be both); QGIS/PostGIS (integration surface too large for a
differential to localise a defect); anything already covered by round 2.

## Phase 1 — File the backlog before running another round

**Entry condition: none. This is the head of the sequence.**

This phase is [Plan 39](39-going-public-upstream-first.md) Phase 1, unchanged
and unstarted, restated here because the roadmap sequence was broken when
Phase 3 shipped ahead of it. It is not new work and this plan claims no credit
for designing it — the three drafts are already selected by
[Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md) §5.1.

### 1.1 File the three selected drafts — **done 2026-09-06**

Per Plan 39 §1: filed **as a person, with no geocase link in the body**. The
maintainer's *"how did you find this?"* is the moment to mention the corpus.

Filed, with **one substitution**:

| draft | issue |
|---|---|
| `odc-stac-crs-without-resolution-units.md` | [odc-stac#288](https://github.com/opendatacube/odc-stac/issues/288) |
| rotated-affine, root-cause half | [rio-tiler#993](https://github.com/cogeotiff/rio-tiler/issues/993) |
| `titiler-invalid-format-500.md` | [titiler#1493](https://github.com/developmentseed/titiler/issues/1493) |

`stackstac-proj-code-unsupported.md` was **withdrawn before filing**: the repo's
last commit is 2024-08-10 (25 months) and the finding is already
[#262](https://github.com/gjoseph92/stackstac/issues/262) with an unmerged
[PR #263](https://github.com/gjoseph92/stackstac/pull/263). The rio-tiler report
took its slot. The scheduling of the remaining fourteen, and the liveness
criterion that caught this, are
[Plan 43](43-upstream-filing-queue-and-repo-liveness.md).

### 1.2 Correct `docs/validation.md`'s closing claim

`docs/validation.md` currently ends *"Nothing has been filed upstream. These are
drafts."* That sentence is accurate today and false the moment 1.1 runs. This is
[Plan 39](39-going-public-upstream-first.md) §4's recorded debt and
[Plan 41](41-positioning-and-the-geometry-thesis.md) Phase 6's open item, which
also corrects the finding count to the surviving irreducible **two**. Land both
edits together — one pass over one file.

### 1.3 Wait

Plan 39's entry condition for broadcast is *filed plus two weeks*, not
*accepted*. Phase 2 runs during the wait; it does not depend on the outcome.

## Phase 2 — The cheap checks, during the wait

### 2.1 Verify the `[all]` fix against the environment that broke

TDD: the failing case first. Reproduce
[Plan 40](40-round-3-packaging-truth-and-vocabulary.md) §1's environment — a
venv with `--system-site-packages` over an older GDAL/geopandas — assert
`pip install "geocase[all]"` leaves `import pandas` and `import geopandas`
working, and confirm the assertion fails against `1.0.0rc3` before confirming it
passes against `1.0.0`. Without the rc3 leg this verifies nothing: a pass on
both means the reproduction is wrong.

Record the result in `CHANGELOG.md` under `1.0.0` if the fix is confirmed. If it
is **not** fixed, this becomes `1.0.1` and Phases 3–4 stop until it is.

### 2.2 Do not re-run rounds 1–2

Recorded as a decision so it is not revisited: the eight consumers of
[Plan 37](37-raster-signal-and-differential-adapters.md) and
[Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md) are not re-run
against `1.0.0`. Neither pinned surface moved; the corpus changes since rc3 are
**additions** (154 → 166) plus Plan 40 Phase 3's vocabulary renames, which are
alias-covered at both load and selection time. The regression risk that would
justify a re-run is the silent-corpus-change class, and Plan 40 Phase 5's
changelog convention is the mitigation for it.

## Phase 3 — The vector differential the corpus has never run

**Entry condition: Phase 1.1 filed. Phase 2.1 green.**

### 3.1 The failing test first

Before any harness: a unit test asserting the comparison predicate reports
`diverged` for two geometry results that genuinely differ and `equal` for two
that differ only by representation — WKB byte order, ring winding, a closing
coordinate, `POLYGON EMPTY` vs `None`. Watch it fail.

This is not ceremony. [Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md)
§3.2 records that the lonboard sweep produced **five false findings against two
true ones** because the comparator read a correct reprojection as a coordinate
error, and [Plan 37](37-raster-signal-and-differential-adapters.md) records two
of three initial "findings" being only NaN-vs-NaN. The geometry equivalent of
that trap is representation-vs-value, and it will fire on the first run if the
predicate is written after the harness.

### 3.2 Shapely (GEOS) against pyogrio (OGR)

Over the 117 vector cases: `is_valid`, `make_valid`, `area`, `bounds`,
`envelope`, and the pairwise predicates, computed once through each engine on
the same bytes. A disagreement is a finding by construction — neither engine is
the oracle.

Consult `CaseMetadata.known_divergences` as
[`differential.py`](../../src/geocase/differential.py) already does, so a
catalogued divergence reports `known` rather than `diverged`. Note that
[Plan 37](37-raster-signal-and-differential-adapters.md) records both pyogrio
defects living in **option space** (`fid_as_index=True` + `use_arrow=True`;
`bbox=`/`mask=` spatial filters) and being **missed** by a run that varied only
library-vs-library on a plain read. Vary the options, or repeat that miss.

### 3.3 DuckDB `spatial` against geopandas

`ST_Read` / `ST_Area` / `ST_Transform` / `ST_IsValid` against the geopandas
result over the same cases. Weight toward `crs/axis_order`, `crs/zone_selection`
and `extent/antimeridian`, which are where a bundled-PROJ stack is most likely
to diverge from a system one.

### 3.4 Record what the round finds, and what it does not

Whatever the outcome, record it in this plan's *Implementation notes* — including
a clean result. Plan 38 recorded pyproj clean and that is load-bearing evidence
about the corpus's reach, not a null result to be dropped.

`known_divergences` entries only where a **specific case** found the divergence.
[Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md) Phase 1 deliberately
recorded none against the three findings no case found, since an entry on an
arbitrary case is a false claim about which case found what.

## Phase 4 — Corpus additions, only if the round earns them

**Entry condition: Phase 3 complete.**

No cases are added speculatively. If Phase 3 produces a finding the corpus could
not express — the pattern that justified Plan 38 Phase 4's four cases and
Plan 40 Phase 4's three — add it, single-variable, following
[Plan 40](40-round-3-packaging-truth-and-vocabulary.md) Phase 4's control
principle: `rotated_two_islands` bundles rotation *with* islands *with* footprint
generation, and the isolated controls are what let a defect localise itself.

Then the gates: `build_case_index.py`, `validate_catalog.py`,
`validate_case_content.py`, `catalog_extent.py`, `catalog_truth.py`, the
generators, and both coverage matrices — regenerated and committed.
`CHANGELOG.md` names each case **by id and by what changed**.

## Open questions for the user

| id | question |
|---|---|
| ~~U18~~ | **Answered by events, 2026-09-06.** Three filed. The Plan 38 §5.1 selection was *not* still right: `stackstac` is abandoned and its finding already filed, so the rio-tiler rotated-affine report replaced it. See [Plan 43](43-upstream-filing-queue-and-repo-liveness.md). |
| U19 | Phase 3 needs an environment with shapely, pyogrio and duckdb-spatial. Run it in the conda `geocase` env, or a separate validation workspace as rounds 1–2 used (`geocase_validator/`)? |
| U20 | Is a fifth round wanted at all before any of the 17 drafts returns a response? This plan's own argument is that it is not — Phases 3–4 are written to be run *after* Phase 1, not instead of it. |

## Implementation notes

*To be completed as phases land.*
