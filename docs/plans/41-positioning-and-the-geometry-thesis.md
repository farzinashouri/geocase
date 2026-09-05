# Plan 41 — Round 4: The Positioning Is Costing Adopters, and the Paying Component Is the One Called Secondary

> **Status: Phases 1-4 implemented (1-2 on 2026-09-03, 3-4 on 2026-09-04); Phases 5-6 proposed.**
> Phase 5 (the lowest-resolution CI floor job) and Phase 6 (correcting
> [`docs/validation.md`](../validation.md) to the surviving two-finding count) remain open;
> Phase 6 changes no code and should land before [Plan 39](39-going-public-upstream-first.md)
> Phase 4 broadcasts. An internal GDAL-only consumer found **two
> P1 defects in an afternoon**, one of which *overturned a conclusion the
> reporter had already committed to in writing*. But every finding came from
> geometry, CRS and footprint cases — the component this project's own framing
> calls secondary — while the machine-checked spec constants it calls "the
> genuinely novel core" contributed **zero**. The reporter evaluated the
> *described* library and said no; it was a well-reasoned no and it was wrong.
> Two prior evaluations rejected geocase as "pixel-moving, GDAL-native", which
> is the audience it serves best. Three of five recommendations are
> documentation. Phases 1-2 are an afternoon's work with no corpus churn and go
> **ahead of** [Plan 40](40-round-3-packaging-truth-and-vocabulary.md).

## Context

An internal consumer ran `1.0.0rc3` against a company codebase on a **GDAL-only** stack:
`pip install geocase`, a venv, and roughly 250 lines of test code. One afternoon produced **two P1
defects** — one silently corrupting shipped slick measurements, one crashing every dateline scene.

Against the alternative the reporter had themselves recommended — hand-rolling a `driver.Create()`
fixture factory — geocase won on both axes: less work, *and* it held cases the reporter would not
have thought to build.

The load-bearing sentence in the report is not the defect count:

> The fixtures didn't just catch what I missed — they corrected what I'd gotten wrong with
> confidence. That's a different and better product than coverage.

`rotated_two_islands` **overturned a conclusion the reporter had already committed to in
writing.** No prior round has produced that claim, and it is stronger than "found bugs" — a
corpus that only finds what you missed competes with careful review, while a corpus that reverses
a confident written attribution does something review demonstrably failed to do.

### The finding that makes this a plan rather than a note

The value came almost entirely from the component the project positions as secondary. The framing
puts machine-checked spec constants at the centre — "the genuinely novel core". Here they
contributed **zero**: the consumer's `main.py` never interprets a pixel value. Every finding came
from geometry, CRS and footprint cases, which the framing barely mentions.

The adoption cost is measured, not hypothetical:

- The reporter **evaluated the described library and said no.** A well-reasoned no, and wrong —
  because the description was radiometry-first while the shipped package is much broader.
- **Two prior evaluations rejected geocase as "pixel-moving, GDAL-native."** At least one is
  likely a false negative for the same reason: pixel-moving GDAL codebases are *exactly* who
  `bottom_up_dem_small`, `rotated_two_islands` and `pixel_is_area`/`pixel_is_point` are for.
<<<<<<< HEAD
  those rejections were recorded as evidence about the product;
=======
  [Plan 22](22-portfolio-direction.md) recorded those rejections as evidence about the product;
>>>>>>> 1afc5cf (plans 40 and 41 mostly implemented)
  round 4 says at least one was evidence about the *description*.
- The reporter **nearly did not run it at all**, because `requires_dist` shows rasterio,
  geopandas and xarray behind extras and this stack is GDAL-only. That `primary_path` returns an
  ordinary filesystem path — so `gdal.Open` just works, and the base install needs only pydantic
  and pyyaml — was the single most important thing the reporter learned, **and it was learned by
  unzipping the wheel.** That is a one-line README fix standing between the package and its
  natural audience.

### Verified against the tree before writing

Three of the report's five recommendations were checked rather than taken at face value, and two
turned out sharper than reported:

- **Six suites exist** — `core-vector`, `crs-edge-cases`, `raster-nodata`, `vector-crs-edge`,
  `vector-schema-encoding`, `vector-topology`. **None covers georeferencing conventions.** The
  recommendation is unmet, not merely undiscoverable, so §1 is a build.
- **`case_id` already exists in this codebase** — on `KnownDivergence` at
  [`catalog/models.py:59`](../../src/geocase/catalog/models.py), while `CaseMetadata` uses `id`.
  The package uses **both spellings for the same concept**. That is a naming inconsistency, not
  just a missing alias, and it explains why the reporter's first call was `c.case_id`.
- **`README.md`'s only GDAL mention** is a note that the *conda* package will not carry the
  extras — the opposite of the reassurance a GDAL-only reader needs.

### The honest deduction, adopted as this plan's standard

The reporter volunteered a subtraction the project should have made itself. Of ten defects: four
needed geocase, three were found by reading and geocase then confirmed, three geocase never
touched. And of its four, **two were sitting in source the reporter had already displayed** — a
careful reader gets those without any fixture.

> The irreducible "only geocase could find this" set is two: the rotated inverse matrix and the
> antimeridian tile. [...] If you're building the case for adoption elsewhere, cite two, not four
> — the stronger claim is the one that survives scrutiny.

Phase 6 writes that number down, because [Plan 39](39-going-public-upstream-first.md) is about to
make this project's argument to strangers who will apply exactly this scrutiny, and a gross count
that deflates under questioning is worse than a smaller one that does not.

---

## Phase 1 — The georeferencing-conventions suite

The four highest-value cases span three directories and are not discoverable as a set. The
reporter reached the two P1s by browsing 34 case ids; a suite would have been faster.

**Implemented 2026-09-03.**

### 1.1 Test first ✅

`tests/unit/test_suites.py`: the new suite resolves through the registry, and contains at minimum
`rotated_two_islands`, `bottom_up_dem_small`, `hole_center_nodata` and `optical_dateline_small`.
Watch it fail on the missing suite key.

### 1.2 Build it ✅

New `src/geocase/catalog/suites/georeferencing-conventions.yaml`, registered in
[`metadata/suite-index.yaml`](../../src/geocase/metadata/suite-index.yaml), following the six
existing suite files exactly.

Membership is the transform / footprint / antimeridian axis: the four cases named above, plus
`pixel_is_area` / `pixel_is_point` and the `footprint_edge_cases` group. Name it for what it tests
— georeferencing conventions — not for a directory.

**Differences from the plan.** Two ids in the plan were wrong: the real cases are
`pixel_is_area_dem_small` and `pixel_is_point_dem_small`, and there is no
`footprint_edge_cases` group — it is the `footprint` tag, whose members are
`all_valid_rectangular`, `nonsquare_diagonal_sparse`, `thin_corridor_shape` and
`hole_center_nodata`. Membership is an explicit `include_case_ids` list of 14
cases rather than `tags_any`, because `include_case_ids` is an **AND** filter in
[`selectors.py`](../../src/geocase/catalog/selectors.py) (a case must be listed),
so it cannot be unioned with a tag selection to pull in `optical_dateline_small`,
which carries `geography:dateline` rather than `transform`/`footprint`. The list
also picks up the other rotation cases (`rotated_two_islands_warped`,
`rotated_bottom_up_small`, `rotated_nonsquare_small`, `rotated_steep_small`,
`geotiff_nodata_small_shifted`). This is the id list §1.2 warns will go stale —
revisit it under [Plan 40](40-round-3-packaging-truth-and-vocabulary.md) Phase 3
and redefine by the `transform/` and `extent/` risk families.

If [Plan 40](40-round-3-packaging-truth-and-vocabulary.md) Phase 3 lands first, define membership
by the `transform/` and `extent/` risk families rather than an id list, so the suite stays correct
as cases are added rather than going stale the first time someone adds a rotated raster.

### 1.3 Document ✅

This suite is the recommended **first** thing a new consumer runs. Say so in
`docs/getting-started.md` and on the catalog index — it is the shortest path from install to a
real finding, which is the number that matters for adoption.

Landed in `docs/getting-started.md` (a new "Start here" section before "Common
patterns") and in `docs/case-discovery.md`, which now also lists all seven suite
keys. **Not** on the generated catalog index: `scripts/generate_catalog_pages.py`
has no suite section at all today, and adding one belongs with
[Plan 40](40-round-3-packaging-truth-and-vocabulary.md) §3.5, which rewrites that
index. The stale "currently 3 suites" line in
`docs/contributing/structure-and-planning.md` was corrected in passing.

---

## Phase 2 — Positioning: lead with geometry and georeferencing

The one-line fixes with the largest measured cost. No code changes.

**Implemented 2026-09-03.** The central claim was asserted rather than trusted:
a clean 3.11 venv with `pip install -e .` enumerates and resolves all 163 cases
and returns a real `primary_path` with **numpy, rasterio, geopandas and xarray
all absent**, and `gdal.Open` on `rotated_two_islands` returns
`(1000.0, 20.0, 5.0, 2000.0, -5.0, -20.0)` — non-zero shear terms, the rotated
transform.

### 2.1 `README.md` ✅

- **Lead with geometry and georeferencing conventions.** S1/S2 radiometry becomes *one vertical,
  not the thesis*.
- Add the missing sentence near the top: **works with plain GDAL.** `primary_path` returns an
  ordinary filesystem path, `gdal.Open` just works, and the base install needs only pydantic and
  pyyaml. The extras are for the convenience loaders, not for reading the files.
- Name the audience the two prior evaluations self-excluded from: pixel-moving, GDAL-native
  codebases.
- Add a `gdal.Open(case.primary_path)` snippet beside the existing rasterio and geopandas ones.

The existing README opener — `geotiff_nodata_small`, where two `-9999` pixels in a hundred turn a
48.08 m mean into −152.86 m — is good and stays. [Plan 25](25-ship-geocase-as-a-package.md) step 8
chose it deliberately; this phase changes what surrounds it, not the example.

### 2.2 `docs/index.md`, `docs/philosophy.md`, `docs/getting-started.md` ✅

The same reordering. `philosophy.md` is where round 4's sentence belongs: the corpus does not only
catch what you missed, it **corrects what you got wrong with confidence** — cited to
`rotated_two_islands` overturning a written conclusion.

### 2.3 Install shapes ✅

Write the two-shape prose here — greenfield (`pip install "geocase[all]"`) versus existing geo
stack (plain `pip install geocase`, which is enough to enumerate, select and resolve).
[Plan 40](40-round-3-packaging-truth-and-vocabulary.md) §1.3 references this rather than
duplicating it; that plan owns the `pyproject.toml` bounds, this one owns the prose.

---

## Phase 3 — Make the best cases hand over their findings

`optical_dateline_small` found a real crash **only because the reporter hand-rolled tile-index
arithmetic to check where the footprint pointed.** The fixture should hand that over. This is
[Plan 40](40-round-3-packaging-truth-and-vocabulary.md) Phase 2's ground-truth principle applied
to the footprint side, on independent evidence.

<<<<<<< HEAD
**Implemented 2026-09-04.**

### 3.1 Test first ✅
=======
### 3.1 Test first
>>>>>>> 1afc5cf (plans 40 and 41 mostly implemented)

Content-gate tests asserting the new declared values are checked against the real bytes, and that
a wrong value is a finding.

<<<<<<< HEAD
### 3.2 `optical_dateline_small` ✅
=======
### 3.2 `optical_dateline_small`
>>>>>>> 1afc5cf (plans 40 and 41 mostly implemented)

Record in the case's `notes.md` and as a `known_divergences` entry: **the footprint is unsplit and
reaches lon 180.22, so naive floor-based tile indexing will request a tile at 180.** State the
consequence, not just the geometry — the geometry is already in the file, and it was not enough.

<<<<<<< HEAD
### 3.3 `rotated_two_islands` ✅
=======
### 3.3 `rotated_two_islands`
>>>>>>> 1afc5cf (plans 40 and 41 mostly implemented)

Ship an **expected pixel↔world round-trip pair** in the metadata, so a consumer asserts directly
instead of writing their own oracle: two `(row, col) → (x, y)` pairs plus the inverse.

This is the case that produced the round's only irreducible finding, and making it self-asserting
is the highest-leverage single edit in either plan.

Carry both as typed fields if Plan 40 Phase 2 has landed (`expected_bounds`, plus a new
`expected_pixel_world_pairs`); otherwise as `params` keys **with a content-gate check**, and
migrate later. Do **not** ship them as prose only — round 3 is explicit that a number the consumer
must re-derive is a number the fixture did not give them.

---

## Phase 4 — `CaseMetadata.id` discoverability

The reporter's first call was `c.case_id`, which raised a bare pydantic `AttributeError`. This is
the same class of problem as the already-special-cased `format=` versus `category=` mistake, which
`selectors.py` calls "the worst first impression".

<<<<<<< HEAD
**Implemented 2026-09-04.**

### 4.1 Test first ✅
=======
### 4.1 Test first
>>>>>>> 1afc5cf (plans 40 and 41 mostly implemented)

`tests/unit/test_models.py`: `CaseMetadata(...).case_id` returns the id, and an unknown attribute
raises a message naming the right one.

<<<<<<< HEAD
### 4.2 Fix ✅
=======
### 4.2 Fix
>>>>>>> 1afc5cf (plans 40 and 41 mostly implemented)

Add a read-only `case_id` property alias on `CaseMetadata` returning `self.id`, **and** a
`__getattr__` raising a directed error for near-misses, in the style of
`_reject_category_as_format` in [`catalog/selectors.py`](../../src/geocase/catalog/selectors.py).

Prefer the alias over a rename: `id` is on the pinned v1.0 surface.

Record the underlying inconsistency — `KnownDivergence.case_id` versus `CaseMetadata.id`, the same
concept spelled two ways inside one package — as a **v1.1 naming item**, not a v1.0 change.

---

## Phase 5 — Minimal-dependency floor check in CI

The reporter's adjacent catch: the consumer's `main.py` needs Shapely ≥ 2.0 while its `meta.yaml`
declares a bare `shapely`. geocase found that repo's defects; the same class of floor mismatch
could bite geocase's own consumers.

The `.venv` (3.11) CI-mirror environment already exists for exactly this kind of question. Add a
job that installs at **lowest resolution** — `pip install --upgrade --resolution=lowest-direct .`
under a recent pip, or a pinned floor requirements file if that resolver flag is unavailable at
the 3.11 floor — and runs the subset of the suite that needs no optional dependency.

This is the mechanical converse of [Plan 40](40-round-3-packaging-truth-and-vocabulary.md) Phase 1:
that phase caps the ceilings, this one proves the floors. Neither is complete alone.

Not urgent. It is last because no consumer has been bitten by it yet — unlike every other phase in
this plan.

---

## Phase 6 — Correct the public claim to the surviving number

[Plan 39](39-going-public-upstream-first.md) is about to broadcast. Round 4's deduction is the
standard to apply to it first.

- In [`docs/validation.md`](../validation.md), report round 4 as **two** irreducible findings —
  the rotated inverse matrix and the antimeridian tile — alongside the four gross, **showing the
  subtraction**. Cite two, not four.
- Apply the same subtraction retroactively to the round-2 and round-3 numbers, or state plainly
  where it has not been applied. The report currently mixes gross counts across rounds, which is
  the weakest form of the strongest available argument.
- Add round 4's sentence about correcting a confidently-wrong conclusion. It is a better headline
  than any count, and it is the one claim a skeptical reader **cannot** deflate by re-deriving the
  finding from source — which is precisely how two of round 4's four gross findings deflate.

This phase changes no code and gates on nothing. It should land before Plan 39 Phase 4's
broadcast, not after.

---

## Verification

```bash
# Phase 2's central claim, asserted rather than trusted
python -m venv /tmp/gc-gdal && /tmp/gc-gdal/bin/pip install -e .
/tmp/gc-gdal/bin/python -c "
import geocase; from osgeo import gdal
c = geocase.load_case('rotated_two_islands')
print(gdal.Open(str(c.primary_path)).GetGeoTransform())"
#   ^ must work with zero optional dependencies installed

# Phase 1 — the four P1 cases as one selectable set
python -c "
import geocase
print([c.id for c in geocase.list_cases(selection='georeferencing-conventions')])"

# Phases 1, 3, 4 — conda `geocase` env (needs osgeo)
pytest tests -q
python scripts/validate_catalog.py
python scripts/validate_case_content.py
python scripts/build_case_index.py --check
python scripts/generate_checksums.py --check
python scripts/generate_catalog_pages.py --check
git status --porcelain    # must be empty after the --check runs

ruff format --check src tests && ruff check src tests
mypy src
mkdocs build --strict
```

## Out of scope

- **Cutting `1.0.0`** — [Plan 39](39-going-public-upstream-first.md) Phase 3. Phase 2 here is a
  fix that release should carry, not a release.
- **Renaming `CaseMetadata.id`** — v1.1, recorded in §4.2 and not done here.
- **The `[all]` bounds and the risk vocabulary** —
  [Plan 40](40-round-3-packaging-truth-and-vocabulary.md) Phases 1 and 3.
- **`differential.py` and `geocase.stac`** — Plans 37 and 38.
<<<<<<< HEAD

---

## Implementation notes — Phases 3-4 (2026-09-04)

What differed from the plan as written.

### Phase 3

- **`expected_pixel_world_pairs` landed as a typed field**, not as `params` keys.
  The plan allows either depending on whether Plan 40 Phase 2 had landed; it had,
  so the typed route was available and is the better one — `params` has no
  whitelist, so a typo there is silence.
- **The pairs are generated, never authored.** `scripts/catalog_truth.py` computes
  them from the file's own affine via `src.xy`, which is the same call a consumer
  makes, so the declared answer is proven by the exact operation it exists to
  grade. A hand-authored pair would drift from the bytes it describes, which is
  the drift that broke `hole_center_nodata`.
- **Written only for rotated rasters — five of them, not just
  `rotated_two_islands`.** On a north-up grid the round trip is
  `origin + col * pixel`, which `expected_bounds` already pins, so declaring it
  everywhere would be noise. All five rotated rasters now carry it
  (`rotated_two_islands`, `..._warped`, `rotated_bottom_up_small`,
  `rotated_nonsquare_small`, `rotated_steep_small`), plus Plan 40 Phase 4's
  `rotated_only_square`.
- **Three samples, not the plan's two**: the origin (where a north-up assumption
  still agrees), the far corner (maximum divergence), and a mid-grid point (which
  no off-by-one at an edge can accidentally satisfy).
- **§3.2's record is a `known_divergences` entry only.** The plan asks for
  `notes.md` as well; `optical_dateline_small` has no notes file and declares
  none, so the record is the right and only home. The gate in
  `tests/unit/test_known_divergences.py` asserts the record states the actual
  bound (**180.22**) rather than "past 180" — a consequence with no number is
  prose the consumer must re-derive, which is the failure the phase exists to fix.
- **The consumer is named `naive-tile-indexing`**, not a library. The defect is
  not attributable to one consumer: it is what *any* code flooring an unwrapped
  longitude into a tile index does. Naming a library would be a false attribution.

### Phase 4

- **The near-miss error covers nine spellings, not just `case_id`.**
  `_ATTRIBUTE_NEAR_MISSES` maps `identifier`, `name`, `risk_type`, `tag`, `path`,
  `primary_path`, `bounds`, `bbox` and `case_identifier` to what the reader
  actually wants. `case_id` itself is a real property and never reaches
  `__getattr__`.
- **The alias is read-only**, as a `@property`. A settable alias would be a second
  source of truth for the id.
=======
>>>>>>> 1afc5cf (plans 40 and 41 mostly implemented)
