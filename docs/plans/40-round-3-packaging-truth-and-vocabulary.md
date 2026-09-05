# Plan 40 — Round 3: The `[all]` Regression, Ground Truth as an Assertion, and the Vocabulary Plan 27 Never Built

> **Status: implemented 2026-09-04 (Phases 1-2 on 2026-09-03; Phases 3-5 on 2026-09-04).** A third external round produced five items,
> each grounded in something that happened rather than a feature wish. One is a
> hard packaging regression that breaks working environments; three are the
> difference between the corpus being a *stimulus* and being an *oracle*; one is
> cheap and saves downstream debugging. Phase 2 is the substantive phase: the
> reporter's sharpest observation is that computing the right answer for a
> tricky file is the hard part, and the corpus currently ships only the easy
> half. Sequenced against [Plan 41](41-positioning-and-the-geometry-thesis.md)
> in [the roadmap](development-plan.md); Plan 41 Phases 1-2 go first.

## Context

A third round of external use of `1.0.0rc3` produced five recommendations. The reporter's
framing is the most valuable input in the report, and it is not flattering:

> Across three rounds and 30 findings, zero were unreachable without the package, and the worst
> bug in each of the last two rounds came from a literal.

What the reporter says geocase actually does well: **a taxonomy of what can go wrong** (a
reviewer's checklist, "worth more than the files"); **inputs nobody thinks to construct** —
rotated transforms, `nodata=0`, ESRI CRS codes; and **regression fixtures**. That is a catalogue
with fixtures attached, which is honest and useful. The framing that would make it clearly worth
a version number is the one this plan's Phase 2 builds:

> If cases carry ground truth, geocase becomes an oracle you can't hand-roll, because computing
> the right answer for a tricky file is the hard part. Right now the files are the easy half.

The five items, with the evidence behind each.

### 1. `[all]` broke a working geospatial environment

In a venv with `--system-site-packages` over GDAL 3.6.2 / geopandas 0.12.2,
`pip install "geocase[all]"`:

- pulled numpy 2.4.6 against scipy 1.10.1 — incompatible;
- shadowed the system geopandas/pandas;
- left pandas unimportable: `ImportError: C extension: None not built`.

That is a hard break, and it hits exactly the target user: someone with a working geo stack who
wants test cases *for* it. `pip install --no-deps geocase geofacts` worked fine, which proves the
core package needs none of it. The corpus is data plus metadata; enumerating and resolving cases
should never need geopandas, xarray or pyarrow — only *loading* them does, and loading is the
user's job anyway.

### 2. The rc1 → rc3 corpus fix was right, and silently broke a downstream test

[Plan 28](28-validate-geocase.md)'s round documented that `polygon_*_baseline` held four different
geometries under one family name; rc3 fixed it. That is the right response. The follow-on: the fix
silently broke a downstream test. The consumer had a canary pinning the defect, it went red on
upgrade, and there was **no signal as to why**. A CHANGELOG entry naming *which case geometries
changed* — not "fixed baseline consistency" — would have made that a five-second diagnosis.

### 3. Machine-readable ground truth is the highest-value addition

Metadata says `expected_nodata_value: -9999.0`. It never says what a *correct answer* looks like.

The single most useful thing geocase produced for the reporter this round was the number: masked
mean **+48.08** versus naive mean **−152.86**. That turned "the mask is dropped" into a finding a
reviewer cannot wave away. But the reporter had to compute it. We generated these files and know
the truth; shipping it is cheap and it is what makes a case usable as an oracle rather than a
stimulus.

### 4. `risk_types` is the best feature and is not browsable

Unambiguous praise first: the taxonomy is what made the round fast. `affine_transform_bug` and
`ambiguous_zero` pointed at `rotated_two_islands` and `landcover_ambiguous_zero_small` **by name,
in seconds**. It is a search index over failure modes and the part of the package the reporter
would miss most.

Two frictions, both measured against this tree:

- **124 distinct terms over 163 case files, 78 of them singletons** (63%). `format_comparison`
  alone covers 60 cases; the literal string `"none"` is used 9 times. The counts quoted in
  [Plan 28](28-validate-geocase.md) (111/135/75) are now stale.
- **No reverse index.** The reporter resorted to an ad-hoc `Counter` over all cases.
  `list_cases(risk_types_any=...)` exists; a term → cases mapping does not.

Underneath both: only **four** terms are gated against the bytes in
[`catalog/content.py`](../../src/geocase/catalog/content.py) — `nodata_ignored`,
`footprint_generation_error`, `axis_order`, `crs_mismatch`. Everything else is indistinguishable
from a typo, which is the rule [Plan 27](27-close-plan-26-findings.md) §1.2 already wrote down and
never enforced. `docs/adding-a-case.md`'s own worked examples — `topology_breakage`,
`attribute_encoding` — **do not exist anywhere in the corpus**, so the authoring doc teaches
vocabulary drift.

### 5. Cases bundle variables

`rotated_two_islands` was the round's one genuine discovery — a rotated geotransform the reporter
would not have constructed unprompted. But it bundles rotation *with* sparse islands *with*
footprint generation. The reporter wanted rotation alone, with a known-correct bounding box, to
prove `_get_bounds` wrong without arguing about the islands. A failure with one possible cause is
a better bug-finder than a case combining three risks.

### What this plan does not do

Plan 41 carries the positioning and discoverability items from round 4, including the install-story
prose that Phase 1.3 below references rather than duplicates. Cutting `1.0.0` is
[Plan 39](39-going-public-upstream-first.md) Phase 3.

---

## Phase 1 — Make `[all]` safe to install into a working geo stack

Urgent, independent of every other phase, shippable alone.

**Implemented 2026-09-03.**

### 1.1 Test first ✅

New `tests/unit/test_packaging_extras.py`, parsing `pyproject.toml` with `tomllib`:

- core `dependencies` contains **only** `pydantic`, `pyyaml`, `geofacts` — no geopandas,
  rasterio, xarray or pyarrow, because the enumerate-and-resolve path must stay dependency-free;
- every entry in every optional-dependency group carries an **upper bound** (`<`), except the
  self-referential `geocase[...]` entries;
- no top-level import of an optional reader anywhere in `src/geocase/catalog/` or
  `src/geocase/api/` — optional imports are allowed only in `cases/loaders/`.

The bounds assertion fails today for all four groups. Watch it fail before fixing.

**Outcome.** `tests/unit/test_packaging_extras.py`, six tests. The two bounds
assertions failed as predicted — across **all** groups, not only the four reader
ones (`bench`, `dev` and `docs` were unbounded too, and are now capped). The
core-dependency and import-hygiene assertions **passed on first run**, which is
the useful result: the enumerate-and-resolve path was already dependency-free,
so the plain-install claim in [Plan 41](41-positioning-and-the-geometry-thesis.md)
§2 was safe to make. The AST check reads module scope only, so the
function-local optional imports in `cases/loaders/` are correctly ignored.

### 1.2 Cap the extras ✅

In `pyproject.toml` `[project.optional-dependencies]`, bound at the next major:

```toml
vector = ["geopandas>=0.14,<2", "shapely>=2.0,<3", "pyarrow>=14.0,<23"]
raster = ["rasterio>=1.3,<2"]
write  = ["rasterio>=1.3,<2"]
netcdf = ["xarray>=2023.1,<2027", "netCDF4>=1.6,<2"]
```

Leave `ruff>=0.15.7,<0.16` as it is, and **do not touch** `hatchling>=1.27,<2` — its comment
records a release-blocking interaction with the pinned `twine`, documented in
[Plan 25](25-ship-geocase-as-a-package.md) step 6.

**Landed as specified, plus three groups the plan did not mention.** The general
"every extra is bounded" test caught that `bench`, `dev` and `docs` were
unbounded too, so `httpx<1`, `scikit-learn<2`, `pytest<9`, `pytest-cov<8`,
`mypy<2`, `types-PyYAML<7`, `types-shapely<3`, `mkdocs<2` and
`mkdocs-material<10` were added. `mkdocs<2` turns out to be load-bearing rather
than cosmetic: the current docs build emits a Material notice that MkDocs 2.0
removes the plugin system entirely and offers no migration path, so an unbounded
`mkdocs` would break `mkdocs build --strict` on release day. `ruff` and
`hatchling` untouched as instructed.

**Verified the caps still resolve.** `pip install "geocase[all]"` into a clean
3.11 venv succeeds and reads a case end to end: rasterio 1.4.4, geopandas 1.1.4,
xarray 2026.7.0, netCDF4 1.7.4, pyarrow 22.0.0, shapely 2.1.2 — pyarrow landing
at 22 confirms `<23` was placed at the right boundary rather than below the
current release.

### 1.3 Document the install story ✅

Bounds alone **do not** fix the reported break: nothing stops pip resolving a newer numpy under
the bound and shadowing system packages. The fix that matters is documentation — two supported
install shapes:

- **greenfield** — `pip install "geocase[all]"`, pip builds the stack;
- **existing geo stack** — plain `pip install geocase`, now provably enough to enumerate, select
  and resolve cases, because the user already has the readers.

State plainly that `[all]` will re-resolve numpy/pandas and is for greenfield environments.
Mirror it as a comment in the extras block, in the house style of the existing load-bearing
comments in that file.

**Write the prose once, in [Plan 41](41-positioning-and-the-geometry-thesis.md) §2**, which owns
the README and getting-started rewrite for a stronger reason. This step is the `pyproject.toml`
comment plus the cross-reference.

**Done as split.** Plan 41 §2.3 landed the two-shape prose in `README.md` and
`docs/getting-started.md` first; this step added the load-bearing comment at the
top of the extras block, which states that the extras are the convenience
loaders rather than how a case is read, names the exact environment `[all]`
broke, and points at the README section. The greenfield/existing-stack claim was
**verified, not asserted**: a clean 3.11 venv with `pip install -e .` resolves
all 163 cases with numpy, rasterio, geopandas and xarray all absent.

### 1.4 Changelog ✅

`## [Unreleased]` / `### Fixed`, naming the break concretely — GDAL 3.6.2 / geopandas 0.12.2 /
scipy 1.10.1, and the resulting `ImportError: C extension: None not built` — not "improved
dependency handling". A user hitting this searches for the error text.

**Landed.** `[Unreleased]` had no `### Fixed` section; one was added above
`### Changed`. It carries the error text in a fenced block so it is greppable,
lists every new bound, and states plainly that bounds alone do not prevent the
break — the two install shapes are the fix.

---

## Phase 2 — Ship ground truth as typed assertion fields

The substantive phase.

Ground truth goes in **`AssertionHints`**, not `params`. `params` is `dict[str, Any]` with no
validator and no key whitelist, so an unrecognised key is silently ignored — the exact
declared-but-ungated failure mode [`catalog/content.py`](../../src/geocase/catalog/content.py)
exists to eliminate, and the one its own docstring cites as its reason for existing. Typed fields
are gated against real bytes for free.

### 2.1 Test first ✅

- `tests/unit/test_models.py` — the new fields parse, default to `None`, reject wrong types.
- `tests/unit/test_content_gate.py` — a raster case declaring a **wrong** `expected_mean_masked`
  produces a finding; the right one produces none.

Write the wrong-value test first and watch it fail: the gate does not yet look at the field.

### 2.2 Model ✅

Add to `AssertionHints` in [`catalog/models.py`](../../src/geocase/catalog/models.py), beside the
existing raster block (`expected_nodata_value`, `expected_scale_factor`, …):

```python
expected_mean_masked: float | None = None    # mean over valid pixels only
expected_mean_naive: float | None = None     # mean including nodata sentinels
nodata_pixel_count: int | None = None
expected_bounds: list[float] | None = None   # [west, south, east, north] in the case CRS
```

Mirror each in [`metadata/schemas/case.schema.yaml`](../../src/geocase/metadata/schemas/case.schema.yaml),
which is what `validate_catalog.py` enforces and which is gated by **strict set equality** against
`CaseMetadata.model_fields` (the constraint [Plan 31](31-case-geography-and-world-maps.md) found the
hard way) — so the schema moves in the same change.

Docstring each with *why the number is here*: it is the answer, so a consumer can be graded
without re-deriving it. Document the units convention for `expected_bounds` — **the case CRS, not
4326** — because `check_extent` already reprojects to 4326 for the separate `extent:` field, and
conflating the two would be a silent wrong-answer bug in the very field whose purpose is to be
right.

### 2.3 Gate ✅

Extend `check_raster_content` in `catalog/content.py` with `_collect`-wrapped checks on the
existing `if hints.X is not None:` chain:

- `expected_mean_masked` / `expected_mean_naive` — computed from the already-open array, reusing
  the NaN-aware `_nodata_pixel_count`. Compare with a relative tolerance (`_MEAN_RTOL = 1e-6`, in
  the style of the existing `_FOOTPRINT_AREA_TOLERANCE`).
- `nodata_pixel_count` — exact equality against the existing `_total_nodata_pixels`.
- `expected_bounds` — derived from the dataset transform and shape, delegating to a **new**
  `assert_bounds_in_crs` in [`assertions/extent.py`](../../src/geocase/assertions/extent.py).

Do **not** reuse `assert_bounds`: it normalises longitudes for the antimeridian and is
4326-specific. Export the new assertion from `assertions/__init__.py`'s `__all__` — the house rule
is that the gate and the user-facing check are the same code.

### 2.4 Populate ✅

A `--write` / `--check` script pair in the style of `scripts/catalog_extent.py`, including its
`# Generated by ... -- do not edit by hand.` banner in the emitted YAML.

Scope: all bundled rasters where the value is meaningful — `expected_mean_*` only where a nodata
value is declared, `nodata_pixel_count` and `expected_bounds` everywhere. Add the `--check`
invocation to the `catalog` CI job in `.github/workflows/ci.yml` and to the command list in
`CLAUDE.md`.

### 2.5 Surface it ✅

- `scripts/generate_catalog_pages.py` renders the values under a new **"Known answer"** heading on
  each case page, and adds them to the case's JSON-LD.
- `docs/adding-a-case.md` gains a subsection: a case shipping a declared answer is worth more than
  one shipping only a file, and here is how to generate it.

**Outcome (2026-09-03).** Implemented as designed. 43 bundled rasters now carry ground truth;
`validate_case_content.py` passes across all 163 cases with the new checks live.

Three things turned out differently:

- **`BOUNDS_PRECISION` is 12, not `catalog_extent.py`'s 6.** The first `--write` at 6 decimals
  made `crs_family_pair_geographic` fail its own gate: that case is geographic, its box spans
  ~0.005 degrees, and six decimals is a 1e-4 *relative* error against a 1e-9 tolerance. Loosening
  the tolerance was the wrong fix — this is the graded answer, and a gate that tolerates a wrong
  fourth digit is not gating the thing that matters. Writing at full precision was.
- **`expected_bounds` on a rotated raster is the axis-aligned envelope** (rasterio's `src.bounds`),
  not the four corners. A rotated scene has no axis-aligned box that is also its outline; the
  envelope is the reproducible choice. Documented on the model field, since a consumer might
  reasonably expect corners.
- **The means are held out of the "Expected behavior" table** and given their own **Known answer**
  section rather than appended as four more rows. `_assertion_rows` dumps every populated hint, so
  this needed an explicit exclusion list — otherwise the answer would have been buried among the
  dtypes. The JSON-LD carries them as `variableMeasured`.

A fully-nodata raster gets `nodata_pixel_count` and `expected_bounds` but no means: the masked
mean of nothing is NaN, and no consumer can reproduce that as an equality.

---

## Phase 3 — The risk vocabulary: canonical list, synonym merge, reverse index

**Implemented 2026-09-04.**

Executes [Plan 27](27-close-plan-26-findings.md) §1.2–1.3, which claims ownership of this
vocabulary and was never built. The consolidating variant is chosen deliberately, so this phase
touches a v1.0 selector surface and needs an alias layer.

### 3.1 Test first ✅

- `tests/unit/test_risk_vocabulary.py` — every `risk_types` entry across
  `src/geocase/data/core/**/*.yaml` is in the canonical list; no canonical term has zero cases;
  `"none"` appears nowhere.
- `tests/unit/test_selectors.py` — `risk_types_all` filters by intersection-of-all, and a
  deprecated alias (`coordinate_order`) still selects the cases now tagged `crs/axis_order`.

### 3.2 The vocabulary ✅

New `src/geocase/catalog/risk_types.py` exporting `RISK_TYPES: frozenset[str]` and
`RISK_TYPE_ALIASES: Mapping[str, str]`, with a one-line description per term — the descriptions
feed the docs index in §3.5, so they live with the data, not in markdown.

Structure it as the **documented two-level hierarchy** the reporter asked for. Terms are
`family/specific` where a family has more than one member — `crs/axis_order`, `crs/zone_selection`,
`crs/mismatch`, `nodata/ignored`, `nodata/ambiguous_zero`, `transform/rotated`,
`transform/bottom_up`. Flat terms stay flat. Selection matches the full term **or** the family
prefix, so `risk_types_any=["crs"]` selects the whole family. That is what makes 124 terms
browsable without deleting information.

`case.schema.yaml` gains an `enum` on `risk_types` items, so `validate_catalog.py` rejects an
unknown term at schema time — closing the typo hole in the gate that runs *anywhere*, without
needing `osgeo`.

### 3.3 The merge ✅

Each old term is recorded in `RISK_TYPE_ALIASES` so existing user selectors keep working; this is
a pinned v1.0 surface.

| Merged into | From |
|---|---|
| `crs/axis_order` | `coordinate_order`, `lat_lon_swap` |
| `crs/mismatch` | `crs_mishandled`, `crs_mismatch` |
| `crs/units` | `crs_unit_confusion` |
| `crs/zone_selection` | `utm_zone_mismatch`, `utm_zone_ambiguity`, `zone_boundary_artifact`, `zone_selection` |
| `extent/antimeridian` | `antimeridian_split`, `antimeridian_wrapping`, `longitude_not_normalized`, `wrapped_coordinate_retention` |
| `format/limitation` | `format_specific`, `format_limitation`, `format_limited` |
| `precision/loss` | `precision_loss`, `precision_rounding`, `driver_specific_precision_loss`, `integer_precision` |
| `empty_geometry` | `empty_geometry_handling` |

Two judgment calls:

- **Delete `"none"` outright** (9 cases). It is the absence of a risk type, spelled wrong.
- **Keep `format_comparison` (60 cases) but move it to `tags`.** [Plan 28](28-validate-geocase.md)
  already calls it "a corpus-construction label rather than a failure mode", and a label that
  covers 37% of the corpus is not a risk. It should not sit in the risk index at all.

Alias resolution happens at **load** time in [`catalog/loader.py`](../../src/geocase/catalog/loader.py),
so the registry and every generated artifact see canonical terms only, **and** at **selection**
time in [`catalog/selectors.py`](../../src/geocase/catalog/selectors.py), so a user's old string
still resolves. Both directions need a test.

### 3.4 Reverse index in the API ✅

`risk_types_any` **already exists** in `selectors.py` and `api/public.py` — this step is the
missing half, not new filtering:

- add `risk_types_all`, mirroring the existing `tags_all` whose absence is the current asymmetry;
- add a `risk_types()` helper returning `Mapping[str, list[str]]` — term → case ids, the reverse
  index the reporter built by hand.

Both additive; `risk_types()` goes in `__all__`.

### 3.5 Reverse index in the docs ✅

- `scripts/generate_catalog_pages.py` emits a complete **term → cases** table on
  `docs/_generated/catalog/index.md`, grouped by family. Keep `MIN_HUB_CASES = 2` for hub-*page*
  generation if the thin-content SEO concern still stands — but the index itself must be complete,
  since the reporter's complaint is precisely that singletons are invisible.
- Fix `docs/adding-a-case.md`'s fabricated examples and link it to the generated vocabulary index,
  instructing authors to pick an existing term or add one to `risk_types.py` in the same change.

### 3.6 Regenerate ✅

All case pages, both coverage matrices, `case-index.yaml`, checksums. Every `--check` gate green.

---

## Phase 4 — Single-variable cases

**Implemented 2026-09-04.**

Obeys the standing rule from [Plan 37](37-raster-signal-and-differential-adapters.md) and
[Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md): **add no more `from_origin`
baselines.**

### 4.1 Test first ✅

A registry test asserting each new id exists with its declared `expected_bounds`, watched failing
on the missing registry key — the pattern `crs_mismatch_overlay_pair` used in
[Plan 36](36-rc3-release-runbook-and-crs-mismatch.md).

### 4.2 The cases ✅

Three cases, each isolating exactly one variable, each shipping Phase 2's ground truth so the
failure has one possible cause:

| id | isolates | ground truth carried |
|---|---|---|
| `rotated_only_square` | a rotated geotransform, plain filled square, no nodata, no islands | `expected_bounds` (the reporter's explicit ask), `nodata_pixel_count: 0` |
| `nodata_only_dem_small` | one sentinel nodata value, north-up, no rotation | `expected_mean_masked`, `expected_mean_naive`, `nodata_pixel_count` |
| `bottom_up_only_square` | a positive-`e` affine alone, no other divergence | `expected_bounds` |

`rotated_only_square` and `bottom_up_only_square` are the **controls** for the two conventions
Plan 37 found paid: a defect that reproduces on the isolated case and not on the bundled one
localises itself, which is the whole argument for single-variable cases.

Generated by `scripts/generate_raster_fixtures.py` and `--check`-gated, `notes.md` each, added to
`case-index.yaml`, checksums regenerated. 157 → 160 cases.

---

## Phase 5 — Changelog convention: name what changed

**Implemented 2026-09-04.**

The cheapest item, and it prevents Phase 3's merge from repeating the rc1→rc3 problem **within
this very plan**.

- Add a **"Corpus changes"** convention, documented at the top of `CHANGELOG.md`: any change to a
  case's geometry, CRS, dtype, nodata value, id, or risk types is listed **by case id and by what
  changed**, never as a summary. The rc1→rc3 `polygon_*_baseline` entry is the worked example.
- Record this plan's own corpus changes accordingly — Phase 3's risk-type renames are exactly the
  kind of change that breaks a downstream selector silently.
- **Publish the changelog.** Add `docs/changelog.md` and a `mkdocs.yml` nav entry. Today the file
  is not in the docs site at all, so a user hitting a break has no URL to read — only a GitHub
  blob link from `[project.urls]`.
- Add the convention to `CLAUDE.md`'s "Conventions that bite".

---

## Verification

```bash
# Phase 1 — runs anywhere, including .venv/3.11
pytest tests/unit/test_packaging_extras.py -q
python -m venv /tmp/gc-clean && /tmp/gc-clean/bin/pip install -e . \
  && /tmp/gc-clean/bin/python -c "import geocase; print(len(geocase.list_cases()))"
#   ^ must print the full case count with zero optional dependencies installed

# Phases 2-4 — conda `geocase` env (needs osgeo)
pytest tests -q
python scripts/validate_catalog.py
python scripts/validate_case_content.py
python scripts/catalog_extent.py --check
python scripts/catalog_truth.py --check          # new in 2.4
python scripts/build_case_index.py --check
python scripts/generate_raster_fixtures.py --check
python scripts/generate_checksums.py --check
python scripts/generate_catalog_pages.py --check
python scripts/generate_raster_coverage_matrix.py --output docs/_generated/raster-coverage-matrix.md
python scripts/generate_vector_coverage_matrix.py --output docs/_generated/vector-coverage-matrix.md
git status --porcelain    # must be empty after the --check runs

ruff format --check src tests && ruff check src tests
mypy src            # catalog.* and api.* are strict — the new fields and risk_types.py land there
mkdocs build --strict
```

End to end, the two things the reporter asked for by hand:

```python
import geocase
geocase.risk_types()["transform/rotated"]        # the reverse index, no Counter needed
c = geocase.load_case("rotated_only_square")
c.metadata.assertions.expected_bounds            # the answer, shipped
```

## Out of scope

- **Cutting `1.0.0`** — [Plan 39](39-going-public-upstream-first.md) Phase 3. Phase 1 here is a
  fix that release should carry, not a release.
- **Ground truth for vector and NetCDF cases.** The evidence is raster-only; extending
  `AssertionHints` further without a consumer asking repeats the unfilled-vocabulary mistake this
  plan's Phase 3 exists to clean up. [Plan 41](41-positioning-and-the-geometry-thesis.md) §3 adds
  exactly one footprint-side exception, on evidence.
- **`differential.py` and `geocase.stac`** — Plans 37 and 38 own those.

---

## Implementation notes — Phases 3-5 (2026-09-04)

What differed from the plan as written.

### Phase 3

- **104 canonical terms, not the ~100 the merge table implies, and two merges the
  plan proposed were *not* made.** Both were blocked by the corpus's own existing
  tests, which is the useful outcome: the tests were defending a real distinction
  the merge table had flattened.
  - `lat_lon_swap` → `crs/lat_lon_swap`, **not** `crs/axis_order`.
    `tests/unit/test_catalog_axis_order.py` asserts that the six GML baselines
    declare `axis_order` *and* that `out_of_bounds_coordinates` does **not** — the
    GML files genuinely honour an authority-declared axis order, while the latter
    is a swap detectable only because latitude 100 is out of range. That is a
    validity signal, not an axis-order declaration, and the file says so in a
    docstring written precisely so the distinction would not be rediscovered.
  - `crs_mishandled` → `crs/mishandled`, **not** `crs/mismatch`.
    `tests/unit/test_catalog_crs_mismatch.py` gates that
    `crs_mismatch_overlay_pair` is the **only** case claiming the term, because a
    mismatch is *"a relationship between two inputs that one file cannot
    express"*. `crs_mishandled` sits on two ordinary single-layer rasters.
- **Two canonical terms had zero cases, and that was a finding rather than a
  reason to delete them.** `transform/bottom_up` and `transform/pixel_anchor`
  name the two conventions that produced the most severe results of validation
  rounds 1 and 2 — and all four cases carrying them
  (`bottom_up_dem_small`, `rotated_bottom_up_small`, `pixel_is_area_dem_small`,
  `pixel_is_point_dem_small`) declared only `nodata_ignored`. **The corpus's most
  productive axis was unsearchable by the index built to find it.** Backfilled
  from the *declared assertions* (`positive_e` in `expected_transform_signs`,
  and `expected_pixel_anchor`), not by guesswork.
- **The schema `enum` is documentation; the real gate is `validate_catalog.py`.**
  The plan says the enum makes `validate_catalog.py` reject a typo. It does not —
  that script never reads `case.schema.yaml`, which is gated only by
  `tests/unit/test_case_models.py` for model agreement. So the enforcement is a
  new `_risk_type_errors()` in `validate_catalog.py`, which reads the **raw
  YAML** rather than the loaded model: `CaseMetadata` canonicalises on load, so
  checking the model would silently repair a deprecated spelling and let the file
  keep drifting. It distinguishes three cases — unknown, deprecated (naming the
  canonical spelling), and retired (naming what happened to the term).
- **Canonicalisation is a `field_validator` on `CaseMetadata`, not in
  `loader.py`.** The plan puts it in the loader; on the model it also covers
  manifest-backed cases and models built directly in a test, so the registry can
  never see a stale term by any route.
- **48 cases end with `risk_types: []`.** Dropping `"none"` (9 cases) and moving
  `format_comparison` to `tags` (60 cases) leaves 48 with nothing — all baselines
  and canonical valid geometries, which genuinely have no failure mode. Written
  as an explicit `[]` rather than a bare `risk_types:`, which YAML parses as
  `None`.
- **`scripts/migrate_risk_types.py` is kept in the tree**, not deleted after
  running. It is the executable record of what happened to each term, it is
  `--check`-gated in CI, and `CHANGELOG.md` points at it. It edits the YAML
  **block-by-block as text** rather than round-tripping through `safe_dump`,
  which would have destroyed the hand-authored `>` prose, the blank-line
  grouping and the `# Generated by ...` banners that other gates match on. Its
  own self-check caught two real bugs in that text surgery — a bare
  `risk_types:` parsing as `None`, and a multi-line comment sitting *inside* a
  list block on the six GML cases, whose plan-34 note is load-bearing and is
  preserved.
- **The docs index lists every term, including singletons**, grouped by family,
  with up to six case links each. `MIN_HUB_CASES` still gates hub *page*
  generation, as §3.5 asks.

### Phase 4

- **163 → 166, not 157 → 160.** The plan was written before Plan 38 Phase 4
  landed six cases. The count gate fired in the same seven files
  [Plan 36](36-rc3-release-runbook-and-crs-mismatch.md) §2 measured.
- **`rotated_only_square` declares `[negative_e, rotated]`, not `[rotated]`.**
  A 30-degree rotation leaves `e` negative, so the case is north-up *and*
  rotated. The content gate caught the single-value declaration as a claim the
  bytes do not support — the field working exactly as intended.
- **The two rotation/transform controls carry no nodata at all** (`src.nodata`
  is `None`), rather than a declared sentinel that never appears. The latter is
  the declared-but-ungated shape [Plan 28](28-validate-geocase.md) Phase 1 found
  six times, and it would reintroduce the second variable these cases exist to
  remove. `nodata_only_dem_small`'s two sentinels sit in the **interior**, since
  a border sentinel is skipped by any consumer that crops edges.

### Phase 5

- **The changelog is published by a generator, not by a nav entry.**
  `CHANGELOG.md` is at the repository root, outside `docs/`, so
  `scripts/generate_changelog_page.py` copies it to `docs/changelog.md` and
  rewrites the repo-relative links — `docs/foo.md` → `foo.md`, and
  `docs/plans/*` and `src/*` to absolute GitHub URLs, since those are excluded
  from the site and `mkdocs build --strict` fails on them. `--check`-gated in CI
  like every other generated artifact.
