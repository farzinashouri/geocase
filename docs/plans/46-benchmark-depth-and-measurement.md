# Deepening the Benchmark: Measure the Ceiling Before Widening the Slate

> **Status: Phases 0 and 2 implemented 2026-09-10; Phase 1 pilot launched
> 2026-09-10 and running (U27 open until it is read); Phases 3–5 gated on the
> Phase 1 decision rule and not started.** See *Implementation record* at the
> end for what landed and what turned out differently.

## Context

[Plan 45](45-claude-cli-effort-track.md) landed the effort track and every gate is
green, so the question *"is the benchmarking good enough?"* is now answerable, and
the answer splits cleanly in two: **the instrument is good and the measurement is
thin.**

What is genuinely good, and should not be touched: oracles computed from first
principles and never from the corpus, enforced by three independent mechanisms
plus a guard-the-guard test (`tests/benchmark/test_fixture_isolation.py`); the
control/edge pairing with `SILENT` dominating `LOUD`, which targets the one
failure class a test-suite-graded benchmark structurally cannot see; deterministic
assertion with LLM-as-judge deliberately unwired (`runner/sweep.py:17`);
property-based graders where a value oracle would overfit (`buffer_m`,
`cluster_points_m`, `voronoi_cells`); and provenance discipline — `prompt_sha256`,
`module_sha256`, `preamble`, `harness_version`.

What is thin, measured rather than asserted:

- **Two publishable runs, ever.** `results/runs/` holds 10 directories, of which
  five are single-task `s2_fixture` gate runs and three are rate-limit damage. The
  two publishable 20-task runs are both **free** OpenRouter models at **one trial**:
  `openai/gpt-oss-20b:free` at 12 CORRECT / 5 SILENT / 3 LOUD, and
  `nvidia/nemotron-3-ultra-550b-a55b:free` at 14 / 2 / 3 / 1 MISSING.
- **No frontier number on the current slate.** The only frontier evidence is Step 0
  — 10 tasks, agentic, n=1, 9/10 — and the Plan 18 gate on a single task. The
  effort track exists and has never been swept; U27 is open.
- **No way to compare two runs.** There is no report command. A task x model
  matrix, a per-`trap_category` rate, and any notion of reproducibility across
  trials must all be assembled by hand from `run.json` files.
- **One bit of signal per task.** Nearly every task is exactly one control plus one
  edge, so a task yields a single bit and a model that fails the *control* is
  scored the same `SILENT` as one that fell into the trap. The headline metric
  cannot currently distinguish **trapped** from **incompetent**.
- **The catalog is unused.** 2 of 29 tasks read a corpus fixture; 172 of 174 cases
  are unreferenced. `trap_category` (21 terms) and `risk_types` (109 terms across
  15 families) are disjoint vocabularies with no mapping, which is *why* the
  coverage gap below went unnoticed.

**On "would more complicated questions help?" — not in the obvious sense, and the
distinction is the whole design of this plan.** Longer multi-step pipelines raise
`LOUD` and `MISSING`, which are noise against a `SILENT` headline: a model that
crashes has been caught by its own test run, which is the outcome this project
exists to say is *not* the interesting one. Complexity that pays is complexity in
the **trap surface**, not in the call graph. Three axes do that, and they are
Phases 3–5: an edge *battery* per task (one bit becomes a profile), corpus-backed
*input* traps where the file itself carries the defect, and only then composite
tasks carrying several independent traps.

**But the expansion decision depends on a number nobody has.** If frontier models
at `--effort max` already sit near the ceiling of the existing 23 geo tasks, the
slate is saturated and widening it is the only thing worth doing; if they do not,
the existing tasks still discriminate and the reporting is worth more than new
content. So Phase 1 is measurement, Phase 2 is the tooling that makes the
measurement legible, and the expansion phases carry a **decision rule fixed in
advance** — the same discipline as Plan 14 Step 0 and the Plan 18 gate, both of
which fired against the plan that wrote them.

Two live oracle defects are fixed on the way through (Phase 0), because every
number this plan produces is graded by them.

## Phase 0 — Fix the oracles before measuring anything

Nothing here is optional and nothing depends on it landing later: a wrong oracle
mislabels every model, which is the failure this project is named after turned on
itself.

### 0.1 `project_line`: the prompt promises 1 km, the oracle allows 25

`src/geocase/benchmark/tasks/project_line/prompt.md` states the returned line must
trace the geodesic *"to within 1 km everywhere"*. `tasks/project_line/grader.py:45`
asserts `off < 25_000`, with a comment acknowledging the gap
(`# spec allows 1 km; vertex-only projection is >500 km off`). A submission 20 km
off violates the stated contract and scores `PASS`.

**Failing test first:** in `tests/benchmark/test_oracles.py`, add a
`TRAPPED["project_line"]` variant that densifies coarsely — enough to land between
1 km and 25 km — and assert it grades `SILENT` on the edge check. It will pass
today (i.e. the assertion fails) because the oracle admits it.

**Then:** decide which number is true and move the *other* one. The recommendation
is to **widen the prompt to 25 km**, not tighten the oracle: the trap is
densify-before-reproject, whose failure is >500 km, and a 1 km bar additionally
measures how many waypoints a model chose — a second, undeclared axis. State the
tolerance the oracle enforces. **This changes `prompt.md`, so `prompt_sha256`
moves; see §0.3.**

### 0.2 `utm_epsg_for`: the grader contradicts EPSG, and the repo already knows

`tasks/utm_epsg_for/grader.py:9-11` pins Svalbard (10.5, 78) to **32633** and SW
Norway (4.5, 60) to **32632** — the 33X and 32V grid exceptions.
`tests/benchmark/agent_baseline/RESULTS.md` records, in its own prior-art notes,
that `pyproj.query_utm_crs_info` returns **32632** and **32631** for those points:
*"The EPSG areas of use do not encode the Norway/Svalbard conventions."* The prompt
asks only for the CRS *"appropriate for that location"*. So a model that consults
the authoritative EPSG database and answers 32632 for Svalbard is scored `SILENT`
for being right by one defensible reading.

That is precisely what `docs/benchmark/quickstart.md` forbids: *"Reject ambiguous
contracts... pinning one measures reading comprehension rather than correctness."*
The task is also recorded in `RESULTS.md` as solved unprompted by the Step 0 agent.

**Failing test first:** `tests/benchmark/test_oracles.py` gains
`test_utm_epsg_for_contract_is_decidable` — a `GOOD` implementation delegating
entirely to `pyproj.query_utm_crs_info` must grade all-`PASS`. It fails today.

**Then:** rewrite `prompt.md` to pin the contract **without naming the trap** — ask
for the zone *"as assigned by the Military Grid Reference System, whose zone
numbering includes the published grid exceptions"*. That makes 33X/32V decidable
from a named standard rather than from the grader's opinion, keeps the trap intact
(the `lon/6` formula still fails), and makes the pyproj answer wrong for a stated
reason. Retirement is the fallback if that wording still reads as a hint; do not
retire silently, since it is the sharpest bare-vs-agentic contrast in the evidence
(`SILENT` in all three bare runs, `CORRECT` agentically).

### 0.3 Prompt-hash consequences, recorded not absorbed

`tests/benchmark/test_prompt_hashes.py` asserts every committed `prompt_sha256`
still reproduces from today's code. Editing two prompts breaks it by design.

**Do not repin silently.** Add `prompt_version: int = 1` to `TaskMeta`
(`registry.py:43`), bump the two edited tasks to `2`, and change the hash test to
assert that a committed run's hash reproduces **from the prompt version that run
recorded** — a run whose task is at v1 while the tree is at v2 is *expected* to
differ and is reported as such, not as a failure. Record both edits in
`CHANGELOG.md` by task name and by what changed, per the corpus-change convention.

### 0.4 An oracle-verification pass for hand-typed constants

Every oracle is either computed from a library or hand-typed. The hand-typed ones
— the `utm_epsg_for` table and `s2_fixture`'s `BOA_ADD_OFFSET = -1000.0` /
`QUANTIFICATION_VALUE = 10000.0` — are checked by nothing but review, and the repo
has already been wrong about one of them once.

**Failing test first:** `tests/benchmark/test_oracle_constants.py` asserting each
hand-typed constant carries a machine-readable citation (document, section) in a
module-level `SOURCES` dict, and that every such constant in a grader appears in
it. Not a network check — a completeness check, so a new constant cannot arrive
uncited.

## Phase 1 — Measure the ceiling first (the effort-track pilot, U27)

**This precedes every expansion phase, and the ordering is the argument.** Whether
to write new tasks depends on whether the existing ones still discriminate at the
top, and that number does not exist. Running it is also nearly free: the effort
track bills nothing, its ceiling is rate limits, and Plan 45 already built and
end-to-end verified the instrument.

### 1.1 The pilot as specified

One model x five efforts x 23 geo tasks, per Plan 45's sequencing note:

```bash
python -m geocase.benchmark run --config configs/models-claude-effort.yaml \
  --track effort --domain geo --dry-run
python -m geocase.benchmark run --config configs/models-claude-effort.yaml \
  --track effort --domain geo --out results/runs
```

`ANTHROPIC_API_KEY` must be unset; the client refuses to start otherwise. Paced at
6 rpm because the sweep competes with the operator's own seat.

### 1.2 k=3, not k=1

Raise `defaults.trials` to `3` for the pilot. Single-trial evidence cannot separate
a reproducible defect from an unlucky sample, which is exactly the distinction
Step 0 needed a second blind trial to establish for `buffer_m`. This triples the
pilot to ~345 invocations for one model; if that is too much seat contention, run
k=3 at `low` and `max` only and k=1 in between — the middle levels are for the
monotonicity curve, the ends are for the verdict.

### 1.3 The decision rule, fixed before the run

Let **C** be the CORRECT rate of the best arm on the 23 geo tasks, and **S** its
silent rate.

- **C >= 85%** (<= 3 tasks missed): the slate is saturated at the top. **Proceed to
  Phases 3–5**, and treat the surviving tasks as the seed for the edge batteries.
- **60% <= C < 85%**: the slate still discriminates. **Phases 2 and 3 only** —
  reporting and edge batteries on the tasks that are already failing. Defer new
  corpus-backed tasks (Phase 4) until a second model family is measured.
- **C < 60%**: the traps are harder than assumed, or the harness is contaminating
  the run. **Stop and diagnose**, do not expand. Suspect the preamble (U28 is
  negative at only moderate confidence) before concluding anything about models.

And U27's own question, which is orthogonal to C: **if `low` and `max` produce the
same per-`trap_category` profile, the effort axis is dead** and Plan 45's remaining
ten arms are not run — regardless of what C says.

### 1.4 The cheap measurements that ride along

Three blocked items cost almost nothing and each removes a caveat from every number
this plan produces:

- **U20** — review the 14 null `named_trap` records in
  `results/probes/2026-08-11_nvidia-nemotron-3-ultra-550b-a55b-free.json`. Manual by
  design (`scripts/review_probes.py`); `sweep`'s report stage is blocked until they
  are done.
- **U9** — one bare run of the six `stdlib` tasks. They have a full harness and have
  **never been run against any model**, so the claim that the instrument detects
  silent failures outside geospatial code is currently unsupported.
- **U29 (optional, needs funding)** — an Anthropic API provider for the *bare*
  track. ~60 lines behind the `ChatClient` Protocol Phase 1 of Plan 45 already
  extracted, and the only way to get a frontier Claude model into the *bare*
  numbers, where the effort track structurally cannot go. A $5–10 top-up covers a
  full sweep.

## Phase 2 — Make runs comparable (the report command)

Gated on nothing; can land in parallel with Phase 1 and is what makes Phase 1
readable.

### 2.1 `trapped` vs `incompetent`, derived not stored

A task whose control check fails and one whose edge check fails both aggregate to
`SILENT` today. Those are different findings: the first is a model that cannot do
the job, the second is the phenomenon the benchmark is about.

**Failing test first:** `tests/benchmark/test_taxonomy.py` gains
`test_trapped_requires_controls_to_pass` — a checks list with a `SILENT` control
and a `PASS` edge must classify as `broken`, not `trapped`.

**Then:** add a pure function `classify_trial(checks) -> Literal["correct",
"trapped", "broken", "loud", "missing"]` to `taxonomy.py`. **Computed at report
time from the `checks` already stored in `run.json`, never written into a record** —
Plan 45's byte-identical regeneration requirement stands, and every existing run
already carries the check-level detail needed to derive it. No schema change, no
migration.

### 2.2 `python -m geocase.benchmark report`

New module `src/geocase/benchmark/runner/report.py`, dispatched from `cli.py`,
reusing `status.scan_runs()` and the schema v2 `run.json`.

```bash
python -m geocase.benchmark report --runs results/runs --domain geo
python -m geocase.benchmark report --runs results/runs --track effort --by-effort
```

**Failing test first:** `tests/benchmark/test_report.py` builds two synthetic run
directories and asserts the matrix cells, the per-category rates, and that a run
with `publishable: false` is **excluded from every rate and named as excluded** —
a rate computed over rate-limit damage is the benchmark's own silent failure.

Four tables, and no blended headline number:

1. **task x model matrix** — one cell per task, the k-trial verdicts side by side
   (`C C S` reads as one flaky task; `S S S` reads as a defect).
2. **per-`trap_category` rollup** — silent rate per category per model. This is the
   unit U27's question is asked in.
3. **reproducible-silent** — tasks `SILENT` in **every** trial at k>=3. The
   strongest single output the benchmark can produce, and `buffer_m`'s 2/2 is the
   prior art for why.
4. **Wilson score intervals** on every rate. 5 of 20 is not a percentage worth
   quoting bare; at n=20 the interval is wide enough to change what the number
   licenses you to say. Hand-rolled, ~10 lines, no scipy dependency.

Cross-domain aggregation stays refused, per the existing rule. Effort rows carry
their `preamble` marker into the table header, so an effort column can never be
read beside a bare column without the reader seeing why not.

### 2.3 Coverage: map `trap_category` to `risk_types`

The two vocabularies are disjoint, which is why nobody noticed that `transform/*`,
`dtype/*` and `precision/*` have zero benchmark coverage despite purpose-built
corpus cases.

**Failing test first:** `tests/benchmark/test_trap_coverage.py` asserting every
`trap_category` maps to at least one canonical `risk_types` term and that every
mapped term still exists in `src/geocase/catalog/risk_types.py` (an unaliased
rename must fail loudly).

**Then:** a `TRAP_TO_RISK: dict[str, tuple[str, ...]]` in `taxonomy.py`. It imports
**nothing** from `geocase.catalog` — the test does the cross-check, so
`test_fixture_isolation.py`'s sole-importer rule is untouched. `report --coverage`
prints which risk families no task exercises.

## Phase 3 — Edge batteries: one bit becomes a profile

**Gated on Phase 1's decision rule (C >= 60%).** The highest-leverage change in this
plan, because it deepens what a task measures without changing what a model sees.

Today `area_m2` asks one question: does the antimeridian box work? A battery asks
six: antimeridian eastward and westward, the poles, the equator, the southern
hemisphere, a high-latitude sliver. **`prompt.md` does not change**, so no
`prompt_sha256` moves and no committed run is invalidated at the prompt level.

### 3.1 Additive-only, no `checks_version`

Three options exist; take the third. A `checks_version` field puts a knob in
`task.yaml` that every consumer must then interpret. Deliberately regrading the
committed runs rewrites recorded provenance for a benefit that is purely
cosmetic. **Append only: existing check names never change meaning, new names are
added after them.**

`tests/benchmark/test_results_pin.py` re-grades committed modules and asserts the
gradings reproduce. Under append-only, an old module gains verdicts on checks that
did not exist when it ran — so the pin test compares **only the check names present
in the committed record**, and reports new checks as informational. That is a
one-function change to the pin, and it is the honest one: the old run genuinely did
not answer the new questions.

**Failing test first:** `tests/benchmark/test_results_pin.py::test_new_checks_do_not_break_the_pin`,
constructed with a synthetic committed record missing a check the grader now emits.

### 3.2 Batteries for the four antimeridian tasks

`area_m2`, `buffer_m`, `position_at`, `split_antimeridian` each go from one edge to
four to six, spanning: westward crossing (the sign Plan 44 Phase 3 found missing
from the corpus entirely), a pole-adjacent geometry, an equator crossing, a
southern-hemisphere instance. Every new check is a `(name, "edge", callable)`
appended to the existing return, with a `GOOD`/`TRAPPED` pair in
`test_oracles.py` — mandatory, and the existing registry test already enforces that
declared checks match emitted ones.

**This also fixes the redundancy.** `area_m2` and `split_antimeridian` currently
share a byte-identical edge input and reference polygon
(`area_m2/grader.py:20-23` == `split_antimeridian/grader.py:31-33`). Under batteries
they diverge, and the corpus stops paying twice for one question.

### 3.3 Batteries for the raster and predicate tasks

`sample_at`, `zonal_mean`, `tag_points`, `label_point`, `fix_geometry` get the same
treatment, drawing edge inputs from the trap families Phase 4 will cover with real
files: a bottom-up transform, a non-square pixel, a pixel-is-point anchor, an
all-nodata window, a NaN sentinel beside a numeric one.

## Phase 4 — Corpus-backed input traps

**Gated on Phase 1 returning C >= 85%.** This is where "harder questions" actually
belongs: the difficulty is in the *input file*, not the call graph. The model gets a
path and a plain contract; the trap is in the bytes.

Plan 44's negative result is the argument for this phase. It found
`bottom_up_dem_small`, `rotated_two_islands`, `dem_nan_nodata_small`,
`geotiff_int8_small`, `landcover_ambiguous_zero_small` and the
`pixel_is_point`/`pixel_is_area` pair all **passing** against GDAL — correctly,
*"because those are failure modes for consumers of GDAL, not for GDAL."* Model-written
code is exactly such a consumer. The corpus already holds the cases; the benchmark
has never pointed at them.

`fixtures.py` needs no change: `stage_fixtures` already copies data bytes with a
sha256 pin and refuses `case.yaml`. `TaskMeta.origin` is a closed `Literal` and
gains a `"plan46"` member.

### 4.1 The task specs

Each is one control (a benign case, passed by defective code) plus 2–3 edges. Every
oracle is computed from first principles or from the file's own header — **never**
from `case.yaml`. Fixture existence under
`src/geocase/data/core/{raster,vector,netcdf}/<case_id>/` is verified as step 4.0
before any is written.

| Task | Signature | Contract (neutral) | Fixture case | Trap isolated |
|---|---|---|---|---|
| `raster_extent` | `raster_extent(path) -> tuple` | Corner coordinates of a GeoTIFF's footprint in its own CRS | `bottom_up_dem_small` | Negative-north transform; `abs()` on the y step flips the extent |
| `pixel_center_at` | `pixel_center_at(path, row, col) -> tuple` | Map coordinate of a pixel's centre | `pixel_is_point_small` | `AREA_OR_POINT`; a half-pixel shift is silent |
| `valid_fraction` | `valid_fraction(path) -> float` | Fraction of pixels carrying real data | `landcover_ambiguous_zero_small` | Zero is a legitimate class, not nodata |
| `band_mean` | `band_mean(path) -> float` | Mean of valid pixels | `dem_nan_nodata_small` | NaN sentinel; `!= nodata` is true for NaN |
| `scaled_values` | `scaled_values(path) -> ndarray` | Physical values, scale/offset applied | `ndvi_scaled_int16_small` | Raw DN returned unscaled |
| `dtype_range_ok` | `dtype_range_ok(path) -> bool` | Whether stored values fit the declared type | `geotiff_int8_small` | Signed int8 read as unsigned |
| `footprint_parts` | `footprint_parts(path) -> int` | Number of disjoint valid-data regions | `footprint_edge_cases/case_rotated_two_islands` | Rotated transform; a bbox hull merges two islands into one |
| `roundtrip_coords` | `roundtrip_coords(geojson_str) -> list` | Parse and re-emit coordinates losslessly | `precision_loss_geojson_roundtrip` | Formatter boundary near 1e-14 |
| `polar_bounds` | `polar_bounds(path) -> tuple` | WGS84 bounds of a polar raster | `optical_polar_small` | A pole cap's 180-degree bbox is arithmetically honest and geographically a lie |
| `same_crs` | `same_crs(a, b) -> bool` | Whether two files share a CRS | `crs_family_pair_geographic` / `_projected` | String comparison of WKT; equivalent CRSs differ textually |

Ten tasks covering seven risk families that currently have zero coverage:
`transform/*`, `dtype/*`, `precision/*`, `nodata/ambiguous_zero`,
`nodata/nan_mishandled`, `extent/polar`, `crs/mismatch`.

### 4.2 NetCDF is deferred, deliberately

`cf_time_ordering_netcdf` and `ndvi_packed_netcdf` are attractive traps — CF time
origins and packed scale/offset — but they need `xarray`/`netCDF4` in the sandbox.
That changes `configs/sandbox-requirements.txt` and therefore
`sandbox_requirements_sha256`, which is recorded provenance on every agentic run.
**Not in this plan.** Revisit once Phase 4's raster tasks have produced evidence
that corpus-backed tasks discriminate at all; a sandbox change is cheap to make and
expensive to unmake.

### 4.3 Contamination probes are mandatory for all ten

Each new task ships a `probe.md`, and `named_trap` is set **by hand** — string
matching cannot do this job and `judge_probes.py` stays unwired. A task every probed
model names unprompted measures recall until the run shows models fall in anyway.

## Phase 5 — Composite tasks (only if Phase 4 earns them)

**Gated on Phase 4 producing at least one reproducible silent failure at k>=3 on a
task the contamination probe did not flag.** Same shape as the Plan 15 rule for
adding a domain, and for the same reason.

Two or three tasks whose contract carries several independent traps — read a
rotated raster, reproject its footprint across the antimeridian, report area in
square metres. **The design constraint is that each trap must remain separately
observable:** every edge check isolates exactly one, so a composite task yields a
vector of findings and not a single mushy bit. A composite task whose failure cannot
be attributed to one trap is a worse instrument than the three simple tasks it
replaced, and must not be written.

## Out of scope, deliberately

- **LLM-as-judge anywhere in the scoring path.** `runner/sweep.py:17` states why:
  it would corrode a benchmark whose entire premise is deterministic assertion.
- **A "review this buggy code" task format.** It measures recognition, not
  production, and the phenomenon here is code a model wrote *and verified*.
- **Cross-domain aggregate rates.** Already refused by the tooling
  (`orchestrator.py:248`); nothing here relaxes it.
- **A leaderboard or public results site.** Two publishable runs do not populate a
  leaderboard, and building one first would create pressure to fill it.
- **Parametric prompt variants.** `quickstart.md` already records that they defend
  against prompt memorisation, not concept memorisation. They are not the
  contamination mitigation and must not be presented as one.
- **NetCDF tasks** (see §4.2) and **retiring the non-discriminating tasks**
  `label_point` / `tile_bounds` / `parse_delimited` / `group_means` — Phase 2's
  matrix is what should decide that, on data rather than on the Step 0 notes.

## Verification

```bash
pytest tests/benchmark -q                      # the harness's own suite
pytest tests -q                                # the full suite (2338 at HEAD)
ruff format --check src tests && ruff check src tests
mypy src
mkdocs build --strict
python -m geocase.benchmark status --config configs/models-free.yaml --domain geo
python -m geocase.benchmark report --runs results/runs --domain geo
```

No catalog gate is affected: this plan adds no case and changes no `case.yaml`.
Phase 4 reads corpus bytes through `stage_fixtures`, which pins sha256 and is
already covered by `test_fixture_isolation.py`.

`results/runs` and `tests/benchmark/agent_baseline/generated` stay ruff-excluded and
byte-identical; nothing here rewrites a committed record.

## Docs to update, in the same change

- `docs/benchmark/quickstart.md` — the report command, `trapped` vs `broken`, the
  edge-battery convention in *Adding a task*, and the Phase 1 numbers once measured.
- `CLAUDE.md` — the benchmark paragraph gains the report command and the
  `trap_category` <-> `risk_types` mapping.
- `CHANGELOG.md` — the two Phase 0 prompt edits, by task name and by what changed.
- `docs/plans/index.md` — a row for this plan.
- `docs/plans/development-plan.md` — the open-actions table currently lists U20,
  U7, U9, U10 and does **not** carry U27. Add U27, and the new items below.

## Implementation record

### Phase 0 — done 2026-09-10

- **0.1 `project_line`** — done. The prompt now states 25 km; `LIMIT_M = 25_000`
  in the grader is the same number, and
  `test_project_line_oracle_enforces_the_promised_tolerance` parses the km figure
  out of `prompt.md` and asserts equality (it failed at 1 vs 25 before the edit).
  **Differs from the plan:** the plan's "coarse densify between 1 and 25 km must
  grade `SILENT`" variant was not written, because the decision was to widen the
  prompt — under a 25 km contract that submission is *correct*. The test instead
  pins the oracle against the stated tolerance from both sides: 7 waypoints on the
  edge leg (~75 km off) grades `SILENT`, 30 waypoints (~3 km) grades `CORRECT`.
  Measured while writing it: 15 waypoints lands at 19 km and 20 at 7 km, so the
  old prompt was violated by any densification coarser than ~50 waypoints.
- **0.2 `utm_epsg_for`** — done, the MGRS wording as specified. Verified first
  that `pyproj.query_utm_crs_info` returns 32632 / 32631 for the two edge points.
  `test_utm_epsg_for_contract_is_decidable` asserts the prompt names the standard
  and still names no place; the pyproj-delegating implementation is now the task's
  recorded `TRAPPED` pair (SILENT on both edges, PASS on both controls) and a
  grid-exceptions implementation its `GOOD` pair — the Step 0 ports had no pair of
  their own. Not retired.
- **0.3 prompt versions** — done. `TaskMeta.prompt_version: int = 1`; both tasks
  at `2`. **Beyond the plan:** the superseded text is archived as
  `tasks/<name>/prompt.v1.md` and `TaskMeta.prompt_template_at(version)` /
  `bare_prompt(task, version=)` read it, so the pin *literally* reproduces a v1
  run's hash rather than merely tolerating a mismatch. A run recorded at v1 under
  a v2 tree is reported as a pytest skip naming both versions; a bump whose text
  is unchanged fails. New bare/effort metas and the manual manifest record
  `prompt_version`; `run.json` does not, so every committed record still
  regenerates byte-identically. Both edits are in `CHANGELOG.md` by task name.
- **0.4 oracle constants** — done as `tests/benchmark/test_oracle_constants.py`.
  The scan rule: every public ALL-CAPS module-level name in a grader bound to a
  numeric literal (or a container of them) must be a key of that grader's
  `SOURCES`, as a `(document, section)` tuple or an `author-chosen: ...` string.
  **Differs from the plan:** the plan named two constants; the mechanical rule
  found ten graders with such names (`TOL`, `DST`, `CORNERS`, `PTS`, …), which are
  parameters rather than facts — hence the `author-chosen` marker, so the
  completeness check stays total without pretending a tolerance has a citation.
  `utm_epsg_for`'s table was hoisted to a module-level `ZONE_EXCEPTIONS` to be
  scannable.

### Phase 1 — launched 2026-09-10, running

- The pilot runs **Haiku 4.5**, the model `configs/models-claude-effort.yaml`'s
  own sequencing note says to start with, at §1.2's fallback: k=3 at `low` and
  `max`, k=1 at `medium`/`high`/`xhigh` — 207 invocations, serial, 6 rpm. Two
  configs (`models-claude-effort-pilot-k3.yaml`, `-k1.yaml`) because
  `defaults.trials` is per-config; both land in the same per-arm run directories.
  Verified before launch that nested `claude -p` runs from a Claude Code session
  (one `PONG` call, 37 thinking tokens at `low`).
- **Caveat on the decision rule:** §1.3 speaks of *frontier* models at `--effort
  max`, and Haiku is not one. Its `max` arm is a **lower bound** on the ceiling —
  if Haiku already reaches C >= 85% the frontier does too; if not, an Opus 5
  `@max` arm at k=3 (69 calls) is the next measurement before applying the
  60–85% or < 60% branches. U27's own question (same per-category profile at
  `low` and `max`) is answerable from Haiku alone.
- Read it with `python -m geocase.benchmark report --runs results/runs --by-effort`.
  Until every arm has written its `graded.json` and `run.json`,
  `tests/benchmark/test_results_pin.py` fails on the in-progress directory —
  expected, and the reason the results pin exists.
- **§1.4:** U20 is untouched — manual by design and the operator's action. U9
  needs `OPENROUTER_API_KEY`, which is not set in this environment. U29 is not
  built (needs funding, U30).

### Phase 2 — done 2026-09-10

- **2.1** — `classify_trial` in `taxonomy.py`, with `test_trapped_requires_controls_to_pass`
  first. Order: `missing` > `broken` (any control not `PASS`, so a LOUD control
  is also `broken`) > `trapped` (any edge `SILENT`) > `loud` > `correct`. A test
  pins that it never contradicts `aggregate_outcome` where they overlap.
- **2.2** — `runner/report.py`, dispatched from `cli.py`, discovery through
  `status.scan_runs`. All four tables; Wilson hand-rolled (reference values
  pinned: 5/20 → 11.2%–46.9%). Unpublishable runs are excluded and named.
  `--by-effort` restricts to the effort track and orders columns `low → max`;
  the per-category rollup with columns in that order *is* the U27 comparison, so
  no separate low-vs-max table was added. Refuses mixed domains without
  `--domain`.
- **2.3** — `TRAP_TO_RISK` in `taxonomy.py` (imports nothing from the catalog;
  `test_trap_coverage.py` does the cross-check against `RISK_TYPES` and
  `RISK_TYPE_ALIASES`). **Differs from the plan:** three categories map to
  nothing honestly — `ordering` (an output-index contract), and the stdlib
  `normalization` / `quoting` — and are declared in `UNMAPPED_TRAPS` with a
  reason rather than force-fitted, because an optimistic mapping would hide the
  gaps the coverage report exists to show. `y-flip` maps to
  `extent/bbox_misinterpretation` only (TMS row order is not a raster
  geotransform), so `transform`, `dtype` and `precision` remain uncovered, and
  the test pins that finding. `report.py` restates the family list as data,
  pinned equal to `families()`.

### Docs — done 2026-09-10

`quickstart.md` (report command, `trapped` vs `broken`, prompt versioning,
`SOURCES`, the pilot configs), `CLAUDE.md`, `CHANGELOG.md`, `index.md`, and the
roadmap's open-actions table (U20/U9 sharpened; U27, U30–U32 added). The
edge-battery convention is **not** yet in *Adding a task*: Phase 3 is gated.

## Open questions

- **U30 — will the operator fund U29?** A $5–10 OpenRouter/Anthropic top-up puts a
  frontier Claude model into the *bare* numbers, which the effort track structurally
  cannot do. Without it, every frontier number this plan produces carries the
  harness preamble.
- **U31 — is single-family evidence still the standing weakness after Phase 1?**
  Every effort arm is a Claude model by construction, and Claude authored both
  GeoCase and this harness. Phase 1 does not lift that caveat; only a second family
  on the bare track does.
- **U32 — does Phase 3's append-only rule hold at the second battery?** It is clean
  for one round of appends. If a battery ever needs to *change* what an existing
  check means, the pin test's premise fails and `checks_version` comes back.
