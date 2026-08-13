# Plan 20 — Restart, spec-first: split the repo, ship the guard, gate the rest

> **Implementation status (2026-08-13).** Phase 1 is **built and green** in the sibling
> repo `../geospatial-spec` (42 tests, ruff + mypy strict clean, zero dependencies verified by
> isolated install, 60 KB vendored single file with a `--check` drift gate). Phase 2 is
> **scaffolded and open** — `docs/evidence/2026-fixture-interviews/` holds the instrument and
> the pre-committed decision rule; 0 of 5 interviews recorded, and it blocks everything in
> Phase 3 except the nodata carve-out. Phase 3's **nodata carve-out is built**: `geocase.raster`
> (primitive + axes + presets), 46 tests, corpus fixtures still regenerate byte-identically.
> Phase 4 (the $20 frontier run, U19) and **Phase 5 (the deletion) are not started** — per this
> plan's own sequencing, deletion follows Phase 1 shipping *and* Phase 2 reporting.
> Outstanding user actions: **U16** (create the repo / pick the PyPI name), **U17** (run the
> five interviews), **U18**, **U19**, **U20**, **U21**.

> **Status: proposed 2026-08-13.** Overarching. If adopted it supersedes the product framing
> in [Plan 15](15-geocase-as-benchmark.md) Phase 7 / Stage 2, replaces
> [Plan 19](19-spec-table-separate-repo.md) outright, **absorbs**
> [Plan 18](18-eo-product-fixtures.md) — whose Phases 0 and 1 are both implemented — and
> redistributes its output across the two repos (see *Disposition of Plan 18*), and retires
> [`development-plan.md`](development-plan.md), [Plan 11](11-distribution-pypi-and-conda.md),
> [Plan 12](12-docs-site-publication.md) and [Plan 13](13-cross-format-canonical-convergence.md)
> as catalog-era documents. [Plan 16](16-generalize-beyond-geospatial.md) is halted where it
> stands. [Plan 17](17-throughput-automation-and-corpus-as-input.md) survives intact but is
> demoted from product work to instrument maintenance.

## Verdict

**Revive — but not as one thing, and not most of it.**

Three independent evaluations against real EO codebases have now reported. They do not
disagree. Read together they say the project owns exactly one defensible idea, has packaged
it inside four layers of things nobody wants, and has been aiming its best mechanism at the
wrong lifecycle stage.

The recommendation is a **three-way split with a fourth part deleted**:

| Part | Evidence | Action |
|---|---|---|
| **Constants + scope guard** | 3 of 3 evaluations name it as the thing worth having | **Ship first, as a new zero-dependency repo.** Weeks, not months. |
| **Fixture generator** | 1 of 3 — but that one is the only evaluator in the target population | **Gate on one cheap interview round, then rebuild** around a low-level primitive with metadata-adversarial axes. |
| **Benchmark** | 0 of 3 mention it; it is nonetheless what kept the project honest | **Keep as the instrument, not the product.** One run left to finish, then freeze scale-out. |
| **Catalog-as-product** | Rejected by Plan 14's own gate in 2026-08; never revived; ~13k LOC still shipping | **Delete.** |

The stop branch is not taken today, but it is written down in advance and dated: see
**Stop conditions**, which fires against this plan the way Plan 14's Step 0 fired against its
own.

---

## Context — what the three evaluations actually said

The reports are the first external signal the project has had that is not about itself. They
came from three codebases: one **adopter** (Sentinel-2 / Prithvi change detection, computes on
pixels, holds 475 SAFE zips on-prem) and two **rejectors** (an analytics stack consuming an
internal stretched-uint8 visualisation RGB; a ~6.5k LOC PyQGIS cartography/layout generator).

Their convergence is the finding. Independently arrived-at agreement across three unrelated
codebases is worth more than any argument in Plans 14–19, all of which were written from
inside the project.

| Component | Adopter (S2/Prithvi) | Rejector B (analytics) | Rejector C (PyQGIS) | Convergence |
|---|---|---|---|---|
| **Constants table** | Validated as *design*. Reframe: regression protection, not bug discovery | **"Ship `geocase_spec` as the primary artifact"** — the only genuinely novel property | "Your constants are right." Make it curl-vendorable, one file | **3/3 — ship it, standalone** |
| **Scope guard** | **"Make-or-break."** Reachable only by supplying baseline/date — never a bare value | Implied by "constants carrying citation + scope guards" | **"Your only defensible feature"** — and it must be a *runtime* guard | **3/3 — this is the product** |
| **Nodata handling** | **Confirmed live bug.** 0 is both nodata and valid dark pixel; single-band zeros slip the all-six-zero heuristic; bilinear resample with no `src_nodata` smears a 4.6M-pixel region | "All-nodata / degenerate-statistics inputs — a `max()==0` normalizer producing silent NaN"; "pathological nodata" | Listed among the axes | **3/3 — build the first fixture here** |
| **Real-granule store** | Re-freeze. They answered it with `unzip -p`; they already had the archive | "Overclaims — you concede you can't redistribute. Call it cache-and-verify" | "Weakest claim. We have petabytes on network mounts; access was never the problem" | **3/3 — kill as a store** |
| **Low-level primitive + presets** | Implied: arbitrary size, min ~224px | **"Would have moved us from no-possible-import-site to plausible fixture source"** | "Array and geotransform, build it however you like" escape hatch | **2/3 — this is the API shape** |
| **Metadata adversariality** (broken CRS, `GetAuthorityCode()→None`, str-vs-int EPSG, band-count mismatch) | — | **"The axes that would have found real bugs in our code."** Covers "code that *reads* rasters", a much larger set | GDAL-native path, plain GeoTIFF, rasterize-from-vector | **2/3 — the larger market** |
| **Radiometric edge cases** (mixed baseline, dB-vs-linear, SCL transpose) | Drops down the ranking — unevidenced in real data so far | "Only bite code that owns its calibration" | Mixed-baseline pairs is 1 of the 4 worth keeping | **1.5/3 — presets, not the headline** |
| **Cheap synthetic fixtures (32×32)** | Cannot exercise a ViT pipeline at all — **≥224px floor** | Spec-accurate L2A would have been *wrong for our input contract* — worse than nothing | **"Loses to `np.zeros`."** Three real bugs reachable in four lines of numpy | **2/3 — cut the cheap axes** |
| **S1 / SAR** | May be beaten by the ML-EO wishlist; three repos treat it as dead weight | — | — | **freeze** |
| **Vector fixtures** | — | (raster repo) | **"Would roughly double your surface."** Their majority-untested logic is PostGIS/DBSCAN/rasterize | **1/3 — keep, don't lead** |
| **Output assertions / render diff** | — | — | **"Biggest gap… you're unadoptable for the entire visualisation-adjacent half of EO tooling"** | **1/3 — new, unvalidated, gate it** |
| **Norm-stats / cloud-mask tables** | **"Serious roadmap candidates, possibly ahead of SAR."** They had a live cloud-mask inversion bug they called *more dangerous than the offset* | — | — | **1/3, from the only adopter — take it seriously** |

### The single most important sentence in all three reports

From Rejector B, in the closing caveat:

> Ask prospective adopters what's actually preventing their raster tests today. It's often
> dependency injection, not fixture fidelity. Knowing that early saves you from building for
> a problem your users don't have.

Their own blocker was a hardcoded absolute path to a 1.5 GB coastline file inside the function
under test. **No fixture library can fix that.** If that pattern is the norm, the entire
fixture half of this project is building for a problem its users do not have — and that is
knowable for the cost of five conversations, before a line is written. Phase 2's gate exists
for exactly this.

### Two claims the evaluations retired

Both were load-bearing in earlier plans and both must stop being said:

1. **"The BOA offset silently biases model input."** The adopter's histogram test came back
   clean and they retracted the claim: every scene was baseline ≥04.00, the offset was removed
   upstream, and Copernicus' reprocessing erased the pre/post-2022 split. The offset story is
   real *in principle* and frequently already handled by upstream ARD. It is **regression
   protection for an invariant the team satisfies by luck of processing and records nowhere** —
   a weaker claim, still real, and the honest competitor is a one-line dirname assertion
   (`parse N05xx, assert >= 04.00`). Constants must therefore earn their place on nodata
   conventions and the enforced-invariant framing, not on the offset.

2. **"AI can't build these."** [Plan 18](18-eo-product-fixtures.md)'s own gate refuted it for
   frontier models on 2026-08-12: Opus 5 and Sonnet 5 emitted baseline-04.00 radiometry
   unprompted; −1000 is in their weights. It holds only for small/cheap models. Plan 18 already
   records this honestly; nothing downstream may re-inflate it.

---

## Verified ground truth

Measured against the working tree on 2026-08-13, not assumed.

- **130 `case.yaml` files** under `src/geocase/data/` (4.2 MB, bundled in the wheel). The
  README says 134; [Plan 17](17-throughput-automation-and-corpus-as-input.md) says 135. Three
  numbers, one `find`. **The benchmark references 2 of them** — `classic_antimeridian_polygon`
  and `shapefile_field_truncation`. Plan 17 §3.4 already stated the honest yield and its
  structural reason: no `case.yaml` carries an expected *computed* result.
- **`src/geocase/synth/spec.py` exports 15 bare module-level constants**, including
  `S2_BOA_ADD_OFFSET = -1000`. That is precisely the dereferenceable value the adopter calls
  make-or-break to prevent. The witness mechanism around it is excellent; the API shape is
  wrong.
- **`sentinel2_l2a(size: int = 32)`** — the default is below the ≥224px floor the only adopter
  set as a hard requirement.
- **[Plan 19](19-spec-table-separate-repo.md) as drafted reproduces the same defect.**
  `SpecFact` is a frozen dataclass with a public `value` field, exposed through a public
  `FACTS` tuple. `raster.FACTS[0].value` is a bare constant. Plan 19 cannot be implemented as
  written.
- **[Plan 19](19-spec-table-separate-repo.md)'s stated audience is unvalidated and contradicted.**
  It names "an AI coding agent writing unit tests." All three evaluators are humans asking for
  a guard in *production* code. Rejector C, verbatim: *"Constants that only live in tests can't
  catch a bug in code that has no tests."*
- **No frontier bare run exists.** Ten committed runs, all free/small models, all bare, all
  geo. Six are publishable; four carry `api_failures > 0`. [Plan 17](17-throughput-automation-and-corpus-as-input.md)
  Phase 4 — the run that de-confounds Claude's agentic 9/10 against gpt-oss-20b's bare 12/20 —
  has never been executed. It is blocked on U11: **$20**.
- **The Step 0 agentic run is not in the results store.** Plan 15 Phase 2's
  `migrate_step0_results.py` was never run; there is no `*_agentic-manual` run directory. The
  project's single most-quoted number lives outside its own results schema.
- **14 of 25 probe records still have `named_trap: null`** (U7/U12 outstanding). Plan 17's
  `report` stage refuses to run until they are reviewed — correctly, and it is why no report
  exists.
- **Dead weight, measured:** `examples/` 8,036 LOC · `scripts/` 4,786 LOC · `tests/` 9,987 LOC ·
  `src/geocase/benchmark/` 4,621 LOC · everything else under `src/` ~3,600 LOC. Plus a stale
  committed `site/`, a `recipe/` for conda, and `extended-manifests/`.

---

## The split

### Repo 1 — `geospatial-spec` (new, ships first)

Zero dependencies, pure stdlib, Python 3.11+. Ships to PyPI **and** as a single vendorable
file, because the thing it competes with is copy-paste.

This is [Plan 19](19-spec-table-separate-repo.md)'s repo with its API inverted and its audience
corrected.

### Repo 2 — `geocase` (this one, cut to roughly a third)

Four packages under one roof. They belong together because they share one discipline — every
claim is machine-checked against an external witness — and because the benchmark is how you
find out which fixtures deserve to exist.

- `geocase.raster` — the fixture primitive and its presets (replaces `geocase.synth`)
- `geocase.vector` — vector fixture generation (from the surviving corpus generators)
- `geocase.granule` — crop-from-a-granule-you-already-hold (replaces the storage component)
- `geocase.benchmark` — unchanged code, demoted framing

### Deleted

The catalog-as-product surface, in one commit per area: `pytest_plugin/` and the `pytest11`
entry point, `api/`, catalog `suites`/`selectors`/`manifests`, the one-line assertion modules,
`examples/`, `extended-manifests/`, `recipe/`, `site/`, the catalog-page and coverage-matrix
scripts, `docs/design/` (a recommendation-service design for a product that does not exist),
and the ~128 bundled cases nothing references.

This is [Plan 15](15-geocase-as-benchmark.md) Stage 2, finally executed, plus the corpus that
Stage 2 left undecided. Plan 14 rejected this surface on 2026-08-09. It has been shipping for
four months since.

### Disposition of Plan 18

[Plan 18](18-eo-product-fixtures.md) is a two-phase plan and **both phases are implemented** —
there is no unbuilt remainder to schedule. Verified on 2026-08-13: the regenerated
`multispectral_s2_like_small` carries `scales=(1e-4,)*4`, `offsets=(-0.1,)*4`, `nodata=0` and
the `BOA_ADD_OFFSET` / `QUANTIFICATION_VALUE` / `PROCESSING_BASELINE` tags (its verification
item 6); `scripts/generate_raster_fixtures.py` emits four product fixtures through
`geocase.synth`; `tests/synth/test_spec_fidelity.py` passes 12 assertions against the vendored
witnesses. Only `generate_raster_fixtures.py --check` could not be run locally — it needs
`osgeo`, which is an environment gap covered by the GDAL-container CI job, not an
implementation gap.

Plan 18's work is therefore **an asset this plan redistributes**, not a backlog it inherits:

| Plan 18 artifact | Goes to | What changes |
|---|---|---|
| `synth/spec.py` — 15 constants, each spec-cited | `geospatial-spec` §1.1 | **Reshaped.** The 15 bare module-level constants become guard functions; `S2_BOA_ADD_OFFSET` stops being importable (trap 1). The citations survive verbatim. |
| Vendored witnesses + `test_spec_fidelity.py` | `geospatial-spec` §1.3 | **Moves unchanged.** Rejector B calls this the only genuinely novel property in the project; it is the reason the guard is not circular. |
| `synth/sentinel2.py` | `geocase.raster.presets` §3.3 | Becomes a preset over the primitive; imports its facts from the spec package. Default size **32 → 256** (trap 9). |
| `synth/sentinel1.py` | `geocase.raster.presets` §3.3 | Ports across and is **frozen** — three repos call SAR dead weight; the ML-EO tables outrank it. |
| Corpus regeneration + `--check` | Phase 5 | The mechanism survives and becomes the *only* corpus mechanism: generated fixtures with a freshness gate replace curated files. |
| `s2_fixture` benchmark task + its gate result | Phase 4 | **Stays.** It is what refuted "AI can't build these" for frontier models, and that refutation is load-bearing in this plan's Context. |
| Plan 18 trap 3 — "baseline 04.00 is a *dated* change" | `geospatial-spec` §1.1 | Promoted from a caution to the product: `boa_offset(baseline=…)` and `boa_offset(acquired=…)` exist precisely because the answer is 0 before 2022-01-25. |
| Plan 18 trap 5 — scope discipline, S2 + S1 only | §3.3, §1.6 | Preserved and sharpened by the evaluations' ranking. |

**One item is genuinely dropped, and it should be a conscious choice rather than an omission.**
Plan 18's closing section *"Also available, deliberately not in this plan"* names three
silent-failure raster traps verified against real corpus bytes — rotated affine on
`rotated_two_islands.tif` (naive drops the b/d terms → 32.6 m error, in-bounds and in the right
CRS), non-square pixels on `nonsquare_diagonal_sparse.tif` (60×30 m → area exactly 2× wrong),
and int16 scale/offset on `ndvi_scaled_int16_small.tif`. All three fixtures exist today. They
would close the `affine_transform_quirk` gap that
[`development-plan.md:460`](development-plan.md) records as promised-and-never-authored.

They are cheap and they are real. They are also **benchmark scale-out**, which Phase 4 freezes
at three items with no fourth (trap 7) — so they do not enter this plan as tasks. Two of the
three re-enter through a different door: rotated affine and non-square pixels are *geotransform
adversariality*, which is Rejector B's axis and is already in the §3.1 primitive
(`transform=…, # any affine, including rotated / non-square`). The **fixtures** are in scope;
only the **oracles over them** are not. If the benchmark ever unfreezes, these three are the
designated first tasks.

---

## Phase 1 — `geospatial-spec` (no gate; 3/3 evidence)

The only part of this plan that needs no permission from further evidence.

### 1.1 The API is guards, not values

The whole design constraint, from the adopter: *the offset must be reachable only by supplying
a baseline or date, never as a bare dereferenceable value. The point is forcing the call site
to answer "does my data carry the offset?"*

```python
from geospatial_spec.sentinel2 import (
    boa_offset, quantification, to_reflectance,
    nodata_value, assert_baseline_consistent,
)

boa_offset(baseline="04.00")            # -1000
boa_offset(baseline="03.01")            #     0   <- the reason the guard exists
boa_offset(acquired="2022-03-01")       # -1000   <- date form, resolved via the baseline table
boa_offset()                            # TypeError: supply baseline= or acquired=

to_reflectance(dn, baseline="04.00")    # the composed operation, offset applied once

# Runtime guard — Rejector C's ask. Importable from production, not just tests.
assert_baseline_consistent(metadata, assumes="pre-04.00")
# -> BaselineMismatch: product declares 04.00; this code assumes pre-04.00 DN scaling.
#    Threshold constants tuned on pre-04.00 data are off by BOA_ADD_OFFSET (-1000).
```

**No module-level constant is exported.** Not `S2_BOA_ADD_OFFSET`, not a `FACTS` tuple with a
public `.value`. The values live in a private table; every public name is a callable that
requires the scope. A test asserts the public surface contains no non-callable except
exceptions and enums — mechanically, not by review (trap 1).

`SpecFact` survives as an *introspection* type returned by `explain(...)`, carrying the
citation and the witness line, for tooling and error messages. It is a return value, never a
constant.

### 1.2 Nodata conventions get equal billing with radiometry

The adopter's evidence is strongest here and the offset's is weakest. The nodata surface ships
in 1.0, not as a follow-on:

```python
nodata_value(product="S2_L2A", baseline="04.00")     # 0
is_ambiguous_zero(product="S2_L2A", baseline="04.00")  # True — 0 is nodata AND a valid dark pixel
resample_nodata_policy(product="S2_L2A")              # names src_nodata/dst_nodata as required
assert_nodata_declared(dataset_profile)               # runtime guard against the smearing bug
```

`assert_nodata_declared` is the direct mitigation for the adopter's confirmed live bug —
bilinear resampling with neither `src_nodata` nor `dst_nodata` set, smearing a 4.6M-pixel
nodata region into valid neighbours.

### 1.3 The witness mechanism moves across unchanged

`tests/synth/data/{MTD_MSIL2A_N0400.xml, s1a-iw-grd-vv-annotation.xml}` and
`test_spec_fidelity.py` migrate as-is. Rejector B calls this **"your only genuinely novel
property — the one thing that breaks the circularity where a hand-authored fixture asserts
your own assumptions back at you."** It is already built and it is the best thing in the
repository. Every fact carries both a spec citation *and* a machine-checked witness, or it does
not ship.

### 1.4 Extensible beyond ESA

Rejector B: *"the mechanism is exactly what they need, and nothing about it is ESA-specific…
That's the difference between a lookup table and a tool."*

```python
from geospatial_spec import FactTable, witness

MY_FACTS = FactTable("acme-taxonomy")

@MY_FACTS.guard(cite="ACME-DD-014 §4.2", witness=witness.from_json("schema/domains.json"))
def domain_code(*, region: str) -> int: ...
```

The witness protocol takes any callable returning `dict[str, object]`, so a team can check
their constants against their own DB schema, OpenAPI doc, or spec JSON. The Sentinel table is
then just the first table, not the point of the package.

### 1.5 Compete with copy-paste

- `pip install geospatial-spec` — zero dependencies, target <100 KB.
- `curl -O …/geospatial_spec.py` — a **single generated file**, byte-identical in behaviour,
  regenerated by `scripts/build_vendored.py` with a `--check` gate in CI so it cannot drift.
  Rejector C: *"If vendoring is one command, we'd have taken it."*
- README leads with the runtime guard and the nodata conventions. It does **not** lead with
  bug discovery, and it states plainly that a one-line dirname assertion covers the offset case
  — then says what the package adds over it (nodata semantics, the enforced invariant,
  the citation, the witness).

### 1.6 Roadmap, in the adopter's stated order

Ranked ahead of S1/SAR, on the only compute-side evidence available:

1. **Foundation-model normalisation statistics** — Prithvi, SatMAE, Clay — spec-cited and
   tagged with which radiometric convention each was trained under. As load-bearing and as
   uncited as any sensor constant.
2. **Cloud-mask output conventions** — OmniCloudMask, s2cloudless, Fmask. The adopter had a
   **live inversion bug they called more dangerous than the offset**. Same guard shape:
   `cloud_mask_polarity(producer="s2cloudless")` never returns a bare bool.

Both are the same machine-checked-constant mechanism aimed one layer up the stack, and neither
deflated when the offset claim did.

---

## Phase 2 — The fixture gate (blocks all fixture work)

**Five conversations. No code. Pre-committed decision rule.** This is Rejector B's caveat
turned into the same instrument Plan 14 Step 0 and Plan 18 Phase 0 already established as
house discipline.

Ask five EO codebase maintainers — mixed compute-side and read-side — one question:

> What stops you unit-testing your raster code today?

Record the answer verbatim under `docs/evidence/2026-fixture-interviews/`. Classify each into
one of: **fixture fidelity** · **dependency injection / hardcoded paths** · **environment
(GDAL/PROJ/QGIS)** · **output assertion** · **nothing, we test fine**.

| Result | Action |
|---|---|
| **≥3 of 5 say fixture fidelity or output assertion** | Build Phase 3 as scoped. |
| **≥3 of 5 say DI / hardcoded paths** | **Do not build the generator** beyond the nodata carve-out below. Ship Phase 1 plus the nodata fixture only, publish the interview finding, and revisit the rest only if an adopter arrives with a fixture-shaped need. Consider whether the honest deliverable is a short piece on testable-raster-code structure rather than a package. |
| **Split / environment-dominant** | Build only the nodata fixture (3/3 evidence, standalone value) and stop there pending a second adopter. |

**The nodata fixture is exempt from this gate.** §3.2 Tier 1 rows 1–3 (nodata border, ambiguous
zero, all-nodata/degenerate stats) carry 3/3 convergence *and* a confirmed live bug in the only
adopter — bilinear resampling with neither `src_nodata` nor `dst_nodata`, smearing a 4.6M-pixel
region. That evidence does not become weaker because five maintainers answer a question about a
different obstacle. Whatever Phase 2 returns, the nodata fixture may be built; every other axis,
preset, `geocase.vector`, `geocase.granule` and output assertion waits on the result.

This gate can kill roughly two-thirds of the remaining plan for the price of a week of
calendar time, and the discipline of running it is the thing the adopter singled out as
paying off twice already: *"run the cheap check before building on the assumption, and
downgrade claims when the check comes back clean."*

---

## Phase 3 — The fixture generator, rebuilt (only if Phase 2 clears)

Reports B and C both asked for the same thing and it resolves the adopter's ≥224px objection
for free: **stop making spec-accurate products the API, and make them presets over a
primitive.**

### 3.1 The primitive

```python
from geocase.raster import raster_fixture

raster_fixture(
    path,
    bands=4, dtype="uint16", size=(256, 256),
    crs="EPSG:32633",             # or: None, "bogus", 4326 as int vs str
    transform=...,                # any affine, including rotated / non-square
    nodata=0, nodata_border=48,   # the axis with 3/3 evidence
    tags={...},
)
```

Size is a parameter, so the ≥224px floor is satisfied by *asking for it*, not by re-freezing.
Default rises to **256** — above the floor, and a power of two.

**Emit plain GeoTIFF on disk, plus an escape hatch.** Rejector C already imports `osgeo.gdal`
and will not take a rasterio dependency for a test helper. So:
`raster_fixture(...) -> FixtureSpec` where `.array`, `.transform`, `.crs_wkt`, `.profile` are
public and `.write(path)` is optional. Anyone can build the file however they like. The
writer's rasterio import stays lazy and lives behind the `[write]` extra.

### 3.2 The adversarial axes — decoupled from radiometry

This is the change that widens the addressable set from "code that computes on pixels" to
"code that reads rasters", which is where all three evaluated repos actually live.

**Tier 1 — build first (3/3 or 2/3 evidence):**

| Axis | Bug it catches | Source |
|---|---|---|
| **Nodata border** | Bilinear resample without `src_nodata`/`dst_nodata` smears nodata into valid neighbours | Adopter, confirmed live |
| **Ambiguous zero** | 0 as both nodata and valid dark pixel; single-band zeros slipping an all-bands-zero heuristic | Adopter, confirmed live |
| **All-nodata / degenerate stats** | `max()==0` normalizer → silent NaN | Rejector B |
| **Missing / non-EPSG CRS** | `GetAuthorityCode()` returns `None` → `int(None)` crash | Rejector B, confirmed live |
| **str-vs-int EPSG round-trip** | Silent identity mismatch | Rejector B |
| **Mismatched band counts** | `IndexError` from hardcoded band reordering | Rejector B, Rejector C |
| **Scene-edge / boundary clipping** | Off-by-one and empty-window paths | Rejector B |

**Tier 2 — the four Rejector C says are genuinely expensive to hand-roll:**
UTM-zone-straddling scene groups · mixed-baseline pairs with real differing metadata ·
resolution-mismatched 10/20/60 m band sets · transposed/ambiguous SCL.

**Cut, explicitly:** anything reachable in four lines of numpy. `np.zeros((4,32,32))`,
`np.full(...)`, a 3-band array. Rejector C found three real bugs with exactly those and
concluded the generator added nothing. Shipping them invites that conclusion.

### 3.3 Presets, not the API

```python
from geocase.raster.presets import sentinel2_l2a, sentinel1_grd
```

`geocase/synth/` becomes `geocase/raster/presets/`. Its constants stop being local and
**import from `geospatial-spec`** — so the spec table has exactly one home and the generator
becomes its first consumer. Fidelity checking stays where it is: in the spec package, against
the witnesses.

Rejector B's miss is closed here too: their analytics consumed an internal stretched-uint8
visualisation RGB, and a spec-accurate L2A fixture *would have been wrong for their input
contract* — "worse than nothing, because it looks plausible while testing the wrong thing."
The primitive expresses a stretched-uint8 quicklook in one call. Presets sit above it; they
are never the only door.

**S1/SAR is frozen.** Three repos call it dead weight and the adopter ranks the ML-EO tables
ahead of it. `sentinel1_grd` ports across and is not extended.

### 3.4 Vector fixtures (1/3 — real, second in line)

Rejector C: *"would roughly double your surface."* Their majority-untested logic is PostGIS,
DBSCAN, `RasterizeLayer` density grids. Same primitive shape, same adversarial-axis discipline:
empty layers, mixed geometry types, invalid geometries, CRS mismatch, antimeridian crossing —
at unit-test scale, emitting GeoPackage/GeoJSON/Shapefile on disk. **Rasterize-from-vector gets
first-class support**, since it is the bridge between the two halves and a common enough
pattern to deserve it.

Build after Tier 1 raster lands and only if Phase 2's interviews corroborate.

### 3.5 `geocase.granule` — component 4, reframed and gated

**Gated on Phase 2; do not start before the interviews report.** The store framing is re-frozen
outright — 3/3 killed it, and the adopter's re-freeze was explicit: for a team with its own
archive it adds ~nothing, and they answered the question it was meant to answer with `unzip -p`.
What survives below is a *different* component supported by *rejector* evidence only, and the
honest reading is that a team holding an archive can already crop with `gdal_translate`. It
therefore does not inherit the store's slot; it competes for Phase 3 priority like any other
1/3 item and builds only if Phase 2 corroborates a fixture-shaped need.

All three reports killed the storage framing and two proposed the same replacement:

```python
from geocase.granule import crop

crop("/mnt/archive/S2B_MSIL2A_….SAFE", bbox=…, size=256, out="tests/fixtures/")
# -> a spec-faithful crop with metadata preserved, committable to the repo
```

Points at a granule the user already holds or fetches with their own credentials. Extracts,
verifies against the spec table, caches the derived fixture. **Redistributes nothing**, so the
licensing objection evaporates. Rejector C: *"That solves the actual pain and sidesteps your
licensing constraint entirely."*

No fetch-on-demand, ever — the adopter's CI is offline/on-prem, and anything that reaches the
network cannot gate a merge.

### 3.6 Output assertions — the one gap nobody has built

Rejector C's biggest-gap finding: *"you generate inputs, but say nothing about asserting
outputs… Without it you're unadoptable for the entire visualisation-adjacent half of EO
tooling."*

Evidence is 1/3 and the scope is large (golden images, tolerance handling, perceptual diff,
"this legend classified into the wrong bins"). **Do not build it on one report.** But note the
seed already exists: `src/geocase/assertions/footprint.py` is the only true golden-file
comparator in the repository, and it survives the deletion pass for this reason. Add "output
assertion" as an explicit answer category in the Phase 2 interviews; if it scores ≥3 of 5,
it displaces §3.4 in priority.

---

## Phase 4 — The benchmark, demoted to instrument

The benchmark is the best-built thing in the repo and **no evaluator asked for it.** That is
not a contradiction — it is a different product with a different audience, and running it as
a *product* means a leaderboard, sustained model spend, and a contamination treadmill that a
solo maintainer will lose.

Its actual value is proven and narrow: it is what told the project Plan 14 was wrong, and what
told it (Plan 18's gate) that frontier models already know the BOA offset. **Both times it
prevented months of building on a false premise.** That is worth keeping and worth roughly
zero further investment in scale.

**Finish exactly three things, then stop:**

1. **The frontier bare run.** ~$7 of the $20 in U11. Claude on the bare track, all 20 geo
   tasks, k=3, `integrity.publishable: true`. This settles Plan 17's Phase 4 confound
   (agentic 9/10 vs bare 12/20 is currently apples to oranges) and fires Plan 17's
   pre-committed appendix gate on whether a correctness library ever comes back. It is the
   cheapest unresolved question in the project.
2. **Migrate the Step 0 run into the results store.** `scripts/migrate_step0_results.py` was
   written and never run; the project's most-quoted number lives outside its own schema.
3. **Review the 14 null `named_trap` records** (U7/U12) and publish **one** findings write-up.
   The headline is not the silent rate — it is *knowing-but-not-applying*: 11 of 11 probe
   replies named the antimeridian trap unprompted and the generated code failed anyway. That
   is the most interesting result the project has and it is unpublished.

**Frozen:** Plan 15 Phase 6 (leaderboard, Pages deploy), Plan 15 Phase 8 (parametric variants),
Plan 16 Phase 3+ (the `stdlib` run and any domain 3). Plan 16's own Phase 5 gate forbids a
third domain before every existing domain has ≥3 models × k=3; the same logic forbids further
investment in domain 2 before domain 1 has a single frontier run.

**Kept, in full:** [Plan 17](17-throughput-automation-and-corpus-as-input.md)'s throughput and
integrity work. `publishable: false` on rate-limit damage is the discipline that keeps the
instrument trustworthy.

---

## Phase 5 — The deletion

Executed in reviewable commits, one area each, after Phase 1 ships and Phase 2 reports.

**Delete outright:** `src/geocase/pytest_plugin/` + the `pytest11` entry point + the
`Framework :: Pytest` classifier · `src/geocase/api/` · catalog `suites`/`selectors`/`manifests`
· the one-line assertion modules · `examples/` (8,036 LOC) · `extended-manifests/` · `recipe/`
· `site/` · `docs/design/` · the catalog-page and coverage-matrix scripts · every test covering
the above, in the same commit as the code.

**Keep, demoted to private:** `assertions/format_compliance.py` (352 LOC — the most original
code in the repo, and Plan 14/15 both said keep) and `assertions/footprint.py` (the golden-file
comparator, now the seed of §3.6). Catalog loader core survives only as far as
`benchmark/fixtures.py` needs it.

**The corpus:** keep the 2 cases the benchmark stages plus whatever the new generators emit;
drop the other ~128. Plan 17 §3.4 already established the structural reason nothing uses them —
no `case.yaml` carries an expected *computed* result — and Rejector C established that the
cheap ones lose to numpy. Generated fixtures with a `--check` gate replace curated files as
the corpus mechanism.

**Archive, don't delete:** Plans 11–19 keep their status banners and move to
`docs/plans/archive/`, with outcomes recorded. `development-plan.md` and `execution-order.md`
are marked catalog-era and archived. The plans folder's own rule — *supersede, don't delete* —
applies to this plan too.

**PyPI:** `geocase` 1.0.0rc1 is published. Leave it, with a notice pointing at the new scope.
Do not yank; yanking breaks the one thing a stranger might already have pinned.

---

## Stop conditions, fixed in advance

Written now so they can fire against this plan the way Plan 14's Step 0 fired against its own.
This plan's own risk section is that it is the **fifth** relocation of where the value sits.
The difference from the previous four is that this one moves toward external evidence rather
than away from a refutation — but that is an argument, and arguments are what the gates exist
to replace.

| Date | Condition | Action |
|---|---|---|
| **Phase 2 report** | ≥3 of 5 interviews say DI / hardcoded paths | Fixture work does not start. Phase 1 only. |
| **2026-11-13 (90 days)** | `geospatial-spec` has **zero external adopters** — no issue, no dependent, no vendored copy in a public repo | **Stop.** Archive both repos, publish the write-ups (benchmark findings, interview findings, the three evaluation reports). The idea was checked properly and the answer was no. |
| **Any time** | The adopter (S2/Prithvi) does not integrate the guard after it ships | Treat as the strongest possible disconfirmation. One confirmed in-population user who still does not adopt means the population is not there. |
| **Any time** | A fifth reframing is proposed without new external evidence | Refuse it. Plan 14's injunction — *do not look for another place to put the value* — now applies at the project level, not the module level. |

The 90-day clock starts at the first `geospatial-spec` release, not today.

---

## Files

### New repo — `geospatial-spec`

- `src/geospatial_spec/{__init__,_table,_witness,_types}.py`
- `src/geospatial_spec/{sentinel2,sentinel1,common}.py` — guard functions only
- `src/geospatial_spec/exceptions.py` — `BaselineMismatch`, `ScopeRequired`, `NodataUndeclared`
- `tests/witnesses/{MTD_MSIL2A_N0400.xml, s1a-iw-grd-vv-annotation.xml, PROVENANCE.md}` — moved
  from `tests/synth/data/`
- `tests/test_spec_fidelity.py` — moved from `tests/synth/`
- `tests/test_no_bare_constants.py` — **new, and the load-bearing one** (trap 1)
- `scripts/build_vendored.py` + `geospatial_spec.py` (generated, committed, `--check` in CI)

### This repo — new

- `src/geocase/raster/{__init__,primitive,axes}.py`
- `src/geocase/raster/presets/{sentinel2,sentinel1}.py` — from `src/geocase/synth/`
- `src/geocase/vector/{__init__,primitive,axes}.py` (Phase 3.4)
- `src/geocase/granule/{__init__,crop,verify}.py`
- `docs/evidence/2026-fixture-interviews/` — Phase 2 verbatim records
- `docs/evidence/evaluations/` — the three reports, committed as the evidence base

### This repo — modified

- `pyproject.toml` — drop `pydantic`/`pyyaml` from core; depend on `geospatial-spec`; drop the
  `pytest11` entry point and the pytest classifier; description and keywords rewritten
- `README.md`, `docs/index.md` — fixtures + instrument, catalog demoted to one history paragraph
- `.github/workflows/ci.yml` — drop the GDAL-container catalog job
- `mkdocs.yml`, `docs/plans/index.md`, `CHANGELOG.md`

### This repo — deleted

Per Phase 5.

---

## Traps

1. **A bare constant will re-enter the spec package the first time it is inconvenient.**
   Someone will want `S2_BOA_ADD_OFFSET` for a f-string. `tests/test_no_bare_constants.py`
   asserts mechanically that every public name is callable, an exception, or an enum — because
   the make-or-break feature cannot be defended by code review alone. This is the single most
   important test in either repo.
2. **The witness mechanism must move with the constants, not after them.** A spec package whose
   facts are one person's reading of a PDF is the defect this project is named after, wearing a
   better costume. No fact ships without a witness assertion.
3. **The offset must stop being the pitch.** It was retracted by the only evaluator who
   measured it. Every README, docstring and talk leads with nodata conventions and the enforced
   invariant. Anyone who reintroduces "silently biases model input" is reinstating a claim that
   was checked and came back clean.
4. **Do not let the primitive grow into a raster library.** `raster_fixture` writes small test
   files with deliberately awkward metadata. The moment it acquires resampling, reprojection or
   band math it is competing with rasterio and will lose. Scope boundary: it produces bytes and
   metadata; it never processes them.
5. **Phase 2's interviews must not be leading.** "Would fixtures help you?" measures politeness.
   The question is "what stops you unit-testing your raster code today?" — open, unprompted,
   recorded verbatim. Same discipline as Plan 14 trap 6 and Plan 18 trap 2, applied to humans.
6. **`geocase` depending on `geospatial-spec` must not become bidirectional.** The spec package
   has zero dependencies, permanently. That is its entire adoption argument. A convenience
   import of anything from `geocase` destroys the product.
7. **The benchmark will try to become the product again.** It is the most finished code here
   and the most fun to extend. Every hour spent on a leaderboard is an hour not spent on the
   thing three evaluations asked for. Phase 4's list has three items and no fourth.
8. **The 90-day clock must be honoured.** A project that has relocated its thesis four times
   needs a date, not a feeling. Write it in the README of the new repo so it is visible, not
   buried in a plan.
9. **The adopter's ≥224px floor is a hard requirement, not a default.** A 32×32 fixture cannot
   exercise a ViT pipeline at all. If a preset ships below 224 without the caller asking, the
   one confirmed user cannot use it.
10. **Do not build output assertions on one report.** Rejector C is right that it is a real gap
    and it is also 1 of 3. It gets an interview category in Phase 2 and a decision after, not a
    place in the initial build.

---

## Verification

```bash
# --- Phase 1: geospatial-spec (new repo) ---

# The make-or-break property, mechanically enforced
python -m pytest tests/test_no_bare_constants.py -q
python -c "
import geospatial_spec.sentinel2 as s2
s2.boa_offset()                       # must raise TypeError
assert s2.boa_offset(baseline='04.00') == -1000
assert s2.boa_offset(baseline='03.01') == 0
"

# Facts are checked against the real granule, not against our reading of a PDF
python -m pytest tests/test_spec_fidelity.py -q

# Zero dependencies, and the vendored single file has not drifted
pip install --no-deps -t /tmp/spec-only geospatial-spec && \
  python -c "import sys; sys.path.insert(0,'/tmp/spec-only'); import geospatial_spec"
python scripts/build_vendored.py --check

# --- Phase 2: the gate ---
ls docs/evidence/2026-fixture-interviews/*.md | wc -l    # must be >= 5 before Phase 3 starts

# --- Phase 3: fixtures (only if the gate clears) ---
python -c "
from geocase.raster import raster_fixture
f = raster_fixture(bands=4, dtype='uint16', size=(256,256), crs=None, nodata=0, nodata_border=48)
assert f.array.shape == (4,256,256) and f.crs_wkt is None   # escape hatch, no rasterio needed
"
python -m pytest tests/raster -q
python -c "import geocase.raster.presets.sentinel2 as p; assert p.DEFAULT_SIZE >= 224"

# --- Phase 4: the instrument, three items ---
python -m geocase.benchmark sweep --config configs/models.yaml --domain geo \
  --trials 3 --stages run,grade --yes          # the frontier bare run (U11)
python scripts/migrate_step0_results.py
python -m geocase.benchmark status --config configs/models.yaml --domain geo   # 0 null named_trap

# --- Phase 5: the surface actually shrank ---
python -c "import geocase; print(geocase.__all__)"
pytest --co -q                                  # in a scratch project: plugin no longer registers
git grep -l "pytest_plugin\|geocase_case\|extended-manifests" -- ':!docs/plans'   # empty

# Full gate, both repos
python -m pytest tests -q && ruff format --check src tests && ruff check src tests \
  && mypy src && mkdocs build --strict
```

Two items matter most. **`test_no_bare_constants.py`** — without it the one feature all three
evaluations called defensible erodes on the first convenient exception.
**`ls docs/evidence/2026-fixture-interviews/`** — without it, two-thirds of this plan is built
on the same kind of confident reading that Plan 14's Step 0 and Plan 18's Phase 0 both
punctured.

---

## User-action checkpoints

| # | Phase | What you do |
|---|---|---|
| **U15** | 0 | Approve the split, the deletion scope, and the 90-day stop date |
| **U16** | 1 | Choose the PyPI name (`geospatial-spec` may be taken); create the repo |
| **U17** | 2 | **Run the five interviews.** Not automatable, not delegable — the whole gate is judgement about what people actually said |
| **U18** | 1 | Send the shipped guard to the S2/Prithvi adopter and ask directly whether it goes in. Their answer is the strongest signal available |
| **U19** | 4 | Spend the $20 (U11 carried forward); run the frontier bare track; spot-check two modules per model |
| **U20** | 4 | Review the 14 null `named_trap` records (U7/U12 carried forward) |
| **U21** | 5 | Approve the corpus deletion — the ~128 unreferenced cases — and the PyPI notice wording |

---

## Deliberately not doing

- **A fourth home for the correctness-library thesis.** Plan 17's appendix gate stands
  untouched; it fires on the Phase 4 frontier run, not on this plan.
- **The leaderboard, Pages deploy, and parametric variants** (Plan 15 Phases 6/8). Product-shaped
  work on the part with zero external demand.
- **Domain 3, or further `stdlib` investment** (Plan 16). Its own Phase 5 gate forbids it.
- **S1/SAR extension.** Frozen behind the norm-stats and cloud-mask tables, on the adopter's
  explicit ranking.
- **Fetch-on-demand anything.** The confirmed user's CI is offline; a fixture that reaches the
  network cannot gate a merge.
- **Redistributing real imagery.** `geocase.granule` extracts from what the user already holds.
  The licensing objection is designed out, not argued around.
- **Renaming `geocase`.** It is published. The identity question is answered by the split, not
  by a name.
- **A monorepo for both packages.** The zero-dependency, 100 KB, curl-vendorable property is
  the spec package's entire adoption argument and it is a *distribution*-level property. Plan 19
  got this right and it is the one thing from Plan 19 carried over unchanged.

---

## Main risks, stated plainly

**1. This is the fifth relocation of the thesis.** Catalog → correctness library → benchmark →
EO fixtures → spec guard. Four of those were argued from inside the project; this one is argued
from three external reports that agree with each other and disagree with the project. That is a
materially better basis — and it is still a fifth. The 90-day stop date and the Phase 2 gate
exist because that argument is not, by itself, sufficient.

**2. The strongest claim keeps shrinking on contact.** Twice now — Plan 14's Step 0, Plan 18's
offset — a hazard that sounded severe deflated the moment someone measured it. Assume it will
happen a third time, to the nodata claim, and design so that measurement is cheap: U18 asks the
adopter directly rather than inferring from a report.

**3. `n=1` on the adopter.** One confirmed compute-side user, who already had their own archive
and whose headline hazard was already neutralised upstream. Every claim about the compute-side
population currently rests on that single repo. U18 is the cheapest test of whether it is real.

**4. The spec table may be too small to be a product.** Fifteen facts and six guard functions is
a weekend of work, and Rejector C is right that a ten-line local module does the same job for
one call site. The defence is the mechanism, not the table: extensibility (§1.4) plus witnesses
(§1.3) is what makes it a tool rather than a lookup, and the ML-EO roadmap (§1.6) is what makes
it grow. If neither lands, the honest answer is a blog post and a gist, and the 90-day gate will
say so.

**5. Deleting 13k LOC is irreversible in practice.** Git remembers, but nobody goes back. That
is the intent — the catalog surface was rejected by this project's own gate four months ago and
has been shipping since — and it should still be done in reviewable commits, one area at a time,
after Phase 1 ships and Phase 2 reports.
