# Plan 15 — GeoCase as a benchmark for silent failures in LLM-generated geospatial code

> **Archived — implemented 2026-08-10. Retained as an implementation log.** Phases 1, 3 and a stripped Phase 4 are built. Superseded as strategy by [Plan 20](../20-restart-spec-first.md), which demotes the benchmark from product to instrument.
>
> The single active roadmap is [`docs/plans/development-plan.md`](../development-plan.md).

> **Status: proposed.** This plan executes the salvage path left by
> [Plan 14](14-reposition-as-correctness-library.md), which its own Step 0 gate rejected.
> If adopted it supersedes the catalog-as-product framing in
> [`development-plan.md`](../development-plan.md) and retires most of
> [Plan 11](11-distribution-pypi-and-conda.md)'s and [Plan 12](12-docs-site-publication.md)'s
> catalog-shaped scope; [Plan 13](13-cross-format-canonical-convergence.md) becomes optional
> rather than a precondition, because the benchmark's oracles are computed from first
> principles and never read the fixture corpus.

## Context

[Plan 14](14-reposition-as-correctness-library.md) proposed repositioning GeoCase as a
correctness library and gated itself on a one-day falsification experiment with a decision
rule fixed in advance. The gate ran on 2026-08-09 and fired: ten fresh coding agents, given
neutral prompts with no hint that edge cases existed, produced **9 of 10 operations fully
correct** — including the Svalbard UTM exception, the NoData sentinel, the TMS row flip, the
donut label point, Voronoi cell ordering, and dateline clustering, length and interpolation.
The library is redundant. Evidence:
`tests/benchmark/agent_baseline/RESULTS.md`.

The one operation that failed is the reason this plan exists. `buffer_m` across the
antimeridian failed in **2 of 2 independent blind trials**, and failed *silently*: both agents
returned a valid-looking polygon that reports a point 211 km away as lying inside a 50 km
buffer. Both agents verified their own work, and both chose a geodesic radial check
(`Geod.inv` from centre to boundary vertices) that is **mathematically invariant under the
defect they had introduced**. Their verification could not see the bug by construction.

That is the finding, and it is a finding about *measurement*, not about geospatial. The
artifact that produced it — neutral prompt → generated module → first-principles oracle →
`PASS`/`SILENT`/`LOUD`/`MISSING` classification — is the only thing the experiment produced
positive evidence for. Plan 14 already anticipated this, listing the harness as a
"first-class deliverable… realistically the only marketing channel this project has".

**This plan promotes the instrument to the product.** GeoCase becomes a reproducible
benchmark measuring whether LLM coding agents write geospatial code that silently lies,
across free and paid models, on two execution tracks, publishing a leaderboard.

**Why this pivot is legitimate where a fourth reframing of the library would not be.** Plan
14's risk section says plainly: *"If Step 0 fails, stop — do not look for a fourth place to
put the value."* That injunction targets relocating the *library's* value. This plan does the
opposite: it abandons the library thesis entirely and keeps only what the experiment
measured. The distinguishing test is falsifiability under improvement — if next year's models
score 10/10, a correctness library becomes more pointless, while the benchmark simply
publishes another data point. It measures the trend instead of betting against it.

**Headline metric, everywhere: the silent-failure rate.** Not pass rate. A loud failure is one
the model's own test run would catch; a silent one is a plausible wrong answer that survives
verification. Benchmarks that grade against test suites structurally cannot see this class,
which is the gap this project occupies.

### Intended outcome

- ~20 tasks, each a neutral prompt plus a first-principles oracle, ~10 ported from Step 0 and
  ~10 derived from the Group A trap survey in `~/projects/GeoCase_Studies`, classified in
  [Plan 14](14-reposition-as-correctness-library.md).
- Two tracks: **bare** (single-shot completion, runs on every model) and **agentic**
  (sandboxed self-verify loop, matching the Step 0 condition).
- An automated OpenRouter runner covering free and paid models, plus a documented manual
  protocol for coding-agent CLIs that have no API.
- A leaderboard published to GitHub Pages, regenerated from committed run records.

---

## Decisions

Four were settled before drafting and the plan is designed within them.

| Decision | Choice | Why |
|---|---|---|
| Model access | OpenRouter runner **plus** a manual coding-agent-CLI protocol | One key reaches GPT/Gemini/DeepSeek/Qwen/Llama and the free tier uniformly; Claude Code, Cursor and Codex CLI have no equivalent API and must be driven by hand |
| Execution conditions | Two tracks: **bare** and **agentic** | Bare runs on every model and is maximally comparable; agentic reproduces the Step 0 condition, which is where the `buffer_m` finding lives |
| Repo pivot | Full, in **two stages** | Stage 1 stands the benchmark up as the product; Stage 2 archives the catalog machinery only once it does |
| Leaderboard | GitHub Pages via the existing mkdocs + material setup | Already a CI job; generated pages with a `--check` freshness gate follow the repo's established convention |

Three further decisions are fixed here:

- **Keep the distribution name `geocase`.** It is published, GIS-adjacent, and the benchmark
  is still built from geospatial cases.
- **Version `2.0.0.dev0` during Stage 1, `2.0.0` at the end of Stage 2.** Stage 2 removes the
  public API, so the pivot is a major.
- **Benchmark code lives at `src/geocase/benchmark/`,** installable via a `bench` extra, so the
  tasks, graders and runner ship rather than living under `tests/`.

### Verified ground truth

Two claims inherited from earlier drafts are wrong and the plan does not rely on them:

- The suite collects **1,179 tests**, not 727. (`python -m pytest tests --co -q`.)
- **There is no GitHub Pages deploy workflow.** `ci.yml`'s `docs` job runs
  `mkdocs build --strict` and discards the output; the `pages` string in that file is an
  unrelated catalog-page freshness gate at `ci.yml:151-155`. A stale `site/` directory sits
  in the repo root. Phase 6 must create the deploy workflow, not modify one.

---

## Minimum viable one-off

If the intent is a single published finding rather than a maintained benchmark, execute this
cut and stop. It is a **prefix** of the full plan, not a fork: everything built here is used
unchanged by the later phases, so expanding afterwards means resuming at Phase 2, not
reworking.

**In scope:**

- Phase 1 in full — the task packages, templated prompts, registry and `grade` CLI. This is
  the part that must not be cheapened: the per-task layout and grading contracts are exactly
  what every later phase builds on.
- Phase 3 in full, **including `test_oracles.py`.** The known-good/known-trapped self-tests
  are non-negotiable in every version of this project (trap 1) — without them the headline
  numbers are not defensible.
- A stripped Phase 4: `openrouter.py`, `bare.py`, `extract.py`, `sandbox.py` and a minimal
  orchestrator. Budget abort and `--dry-run` stay (they protect money); the mocked-transport
  test suite may be replaced by `--dry-run` plus a manual spot-check of two graded runs per
  model. The agentic track can be deferred or run manually per the Phase 5 protocol at k=1.
- One round of runs across the chosen models, and a findings write-up in
  `docs/benchmark/findings/` in the style of the existing `RESULTS.md` — dated, with the
  single-family and small-n caveats stated.

**Out of scope until expansion:** the Phase 2 results schema and pin test (keep the raw run
directories committed so they can be migrated later), the Phase 6 leaderboard and Pages
deploy, the Phase 7 repositioning and version bump, Phase 8, and all of Stage 2. The catalog
stays untouched.

**What the one-off deliberately gives up:** reproducibility guarantees for third parties, a
comparable second run, and the trend-measurement claim. The output is a *report*
("N models, silent-failure rate X on these tasks, on this date"), not a *benchmark*. That is
an honest deliverable, but the repo should not be repositioned around it — README and
`pyproject.toml` framing changes wait for the full plan.

**Expansion path:** Phase 2 migrates the committed one-off runs into the results store
exactly as it migrates the Step 0 artifacts today; Phases 4–6 then proceed as written. The
one thing that cannot be recovered after the fact is a prompt edited between the one-off and
the expansion — hash the prompts into the findings write-up at run time so the later
`prompt_sha256` field can be backfilled truthfully.

---

## Stage 1 — the benchmark becomes the product

### Phase 0 — Plan doc and repositioning decisions

**Files:** create this document; modify [`index.md`](../index.md) (add plan 15; mark plan 14's
salvage path as executed by it), [`14-reposition-as-correctness-library.md`](14-reposition-as-correctness-library.md)
(one status line pointing here), `mkdocs.yml` (nav entry).

**Verify:** `mkdocs build --strict`.

### Phase 1 — Task registry refactor

Split the 407-line monolith `tests/benchmark/agent_baseline/grade.py` into
per-task packages. The oracle logic ports **verbatim** — this phase changes no expected value,
and the pin test proves it.

Create under `src/geocase/benchmark/`:

- `taxonomy.py` — `Status` (`PASS`/`SILENT`/`LOUD`/`MISSING`), `CheckKind` (`control`/`edge`),
  pydantic `CheckResult` and `TrialOutcome`, and the controlled trap-category vocabulary:
  `antimeridian`, `axis-order`, `units-degrees`, `crs-conformance`, `nodata`,
  `topology-repair`, `canonical-equality`, `predicate-semantics`, `ordering`, `y-flip`,
  `zone-exceptions`, `collinearity`, `discretization`. Semantics come straight from
  `record()`/`run_check()` at `grade.py:39-62`.
- `registry.py` — discovers `tasks/*/task.yaml`, validates against a pydantic `TaskMeta`,
  exposes `all_tasks()`. Replaces the `GRADERS` dict at `grade.py:346-357`.
- `prompts.py` — `render_prompt(task, *, workdir, python)` over `{workdir}`, `{python}`,
  `{module_path}`, `{scratch_dir}` placeholders. **This fixes a real portability defect:** the
  committed prompts hard-code absolute scratchpad paths from the original session
  (`prompts/02_buffer_m.md:1`), so they cannot be re-run anywhere else as they stand.
- `grading.py` — module loading (from `load()`, `grade.py:45-52`), `grade_module()`, and
  `grade_in_subprocess()` for untrusted output. Model-generated code is **never** imported
  into the runner's own process.
- `tasks/<name>/{task.yaml, prompt.md, grader.py}` × 10, ported from the existing graders.
  Shared helpers (`GEOD`, `rel_ok`, `_make_raster`, `_pixel_lonlat`, `_xyz_tile_bounds`) move
  to `_oracle_utils.py`.
- `cli.py` / `__main__.py` — `python -m geocase.benchmark grade --generated DIR --json OUT`
  reproduces today's CLI (`grade.py:360-403`). The command is agnostic to who wrote the
  modules: any directory whose files match the task contracts (module name, function
  signature, CRS conventions from `task.yaml`) grades identically, whether the author was a
  model or a human. That property is load-bearing twice over — it is what lets Phase 3's
  oracle self-tests grade hand-written known-good and known-trapped implementations, and it
  is what makes the self-audit use in Phase 6 free.

`task.yaml`, schema v1:

```yaml
schema_version: 1
name: buffer_m
title: Geodesic buffer in metres
function: buffer_m
signature: "buffer_m(geom, distance_m) -> geometry (EPSG:4326 in and out)"
module: gen_buffer_m.py
handbook_id: null            # e.g. VEC-0012, or null where the bank has no counterpart
trap_category: antimeridian
packages: [shapely, pyproj]
origin: step0                # step0 | plan15
checks:
  - {name: 1km_at_lat50,          kind: control}
  - {name: 50km_across_dateline,  kind: edge}
```

Handbook ids for the ported ten, from Plan 14's Group A table: `area_m2`→FND-0027,
`length_m`→FND-0010, `cluster_points_m`→SQL-0042, `voronoi_cells`→ANA-0037,
`tile_bounds`→ALG-0022, `label_point`→VEC-0007, `position_at`→TRJ-0036. `buffer_m`,
`utm_epsg_for` and `sample_at` are `null` pending **U1**.

**Make the handbook citation machine-checkable.** This is Plan 14's trap 8 — cited ids are
prose until something checks them, which is the same defect class that produced Plan 13.
`tests/benchmark/test_registry.py` asserts every `task.yaml` validates; that declared `checks`
exactly match the names and kinds the grader emits when run against the committed Step 0
modules; that `handbook_id` matches `^[A-Z]{3}-\d{4}$` or is null; and — when
`GEOCASE_STUDIES_PATH` is set, as it is on the author's machine — that each id resolves to a
question file's frontmatter `id`. That last check skips when the variable is unset, so CI
stays green without the private repo.

**Verify:**

```bash
python -m pytest tests/benchmark -q
python -m geocase.benchmark grade --generated tests/benchmark/agent_baseline/generated \
  --json /dev/stdout          # statuses identical to the committed results.json
ruff format --check src tests && mypy src
```

### Phase 2 — Results store, and migrating the 2026-08-09 run

Create `src/geocase/benchmark/results.py` (pydantic `RunRecord`, `load_all_runs()`) and a
`results/runs/<run_id>/` tree. Schema v2, one `run.json` per (model, track):

```json
{
  "schema_version": 2,
  "run_id": "2026-08-09_claude-fable-5_agentic-manual",
  "date": "2026-08-09",
  "model": {"id": "anthropic/claude-fable-5", "label": "Claude Code (Fable 5)", "provider": "manual-cli"},
  "track": "agentic-manual",
  "protocol": "claude-code",
  "runner": {"name": "geocase-benchmark", "version": "2.0.0.dev0", "commit": "<sha>"},
  "config": {"trials": 1, "temperature": null, "max_turns": null, "variant_seed": null,
             "sandbox_requirements_sha256": "…", "prompt_sha256": {"buffer_m": "…"}},
  "cost_usd": null,
  "tasks": {
    "buffer_m": {"trials": [
      {"trial": 1, "module": "generated/trial1/gen_buffer_m.py", "module_sha256": "…",
       "outcome": "SILENT",
       "checks": [{"check": "1km_at_lat50", "kind": "control", "status": "PASS", "detail": "…"},
                  {"check": "50km_across_dateline", "kind": "edge", "status": "SILENT", "detail": "…"}],
       "turns": null, "usage": null}
    ]}
  }
}
```

`track` ∈ `bare` | `agentic` | `agentic-manual`. `protocol` records how the loop was driven:
`openrouter-chat`, `openrouter-tools`, `text-loop`, `claude-code`, `cursor`, `codex-cli`.

`scripts/migrate_step0_results.py` (one-shot) converts the Step 0 artifacts into the first
entry, `2026-08-09_claude-fable-5_agentic-manual`: the ten modules as trial 1,
`gen_buffer_m_trial2.py` as a partial trial 2, and the verbatim original prompts retained for
provenance.

The pin test generalises. `tests/benchmark/test_results_pin.py` parametrises over every
`results/runs/*/run.json`, re-grades each committed module and asserts statuses match — the
same reproducibility contract as `tests/benchmark/agent_baseline/test_agent_baseline.py`, which
notes that drift *in either direction* means the artifacts or oracles changed deliberately.
CI only ever executes committed, human-reviewed modules, which is the trust model already in
force.

Delete `tests/benchmark/agent_baseline/` once migrated; the `RESULTS.md` narrative becomes
`docs/benchmark/findings/2026-08-09-claude-fable-5.md`.

**Verify:** the pin reproduces nine `CORRECT` and `buffer_m` `SILENT` twice;
`git grep -l agent_baseline` returns nothing.

### Phase 3 — Ten new tasks from the handbook's Group A

Target ~20 tasks. Each is `tasks/<name>/{task.yaml, prompt.md, grader.py}` plus a registry
entry. Prompts follow the established neutral template — exact signature, tightly pinned
contract, "verify that your code actually runs before finishing", reply `DONE`, and **no hint
that a trap exists** (Plan 14, trap 6). Oracles are computed from first principles in the
grader (Plan 14, trap 7); the handbook's verified `q*.py` solutions are a design cross-check
run locally, never imported.

| Task | Handbook | Edge check — the trap, which must present as SILENT |
|---|---|---|
| `tag_points` | VEC-0012 | Point on a shared edge: `within` silently drops it, an `intersects` join silently duplicates the row |
| `fix_geometry` | VEC-0014 | Bowtie: result must be valid *and* keep both lobes; `buffer(0)` quietly deletes one |
| `dedupe_geoms` | VEC-0013 | Same ring with a rotated start vertex and reversed orientation must dedupe; WKB hashing misses it |
| `to_rfc7946` | VEC-0008 | EPSG:3857 input must be reprojected to lon/lat; no `crs` member; right-hand-rule rings |
| `project_line` | VEC-0029 | Densify *before* reprojection (oracle uses `Geod.npts`); densifying after puts the midpoint kilometres off |
| `wkt_from_latlon` | VEC-0002 | Input is `lat, lon` per API convention, WKT is `x y`; swapped axes parse fine and look plausible |
| `segment_intersection` | ALG-0028 | Collinear overlapping segments must return the overlap; determinant-only solvers return `None` |
| `geohash_neighbors` | ALG-0021 | Cells touching the equator or prime meridian share no prefix; oracle encodes offset points from first principles |
| `split_antimeridian` | FND-0047 | Two parts, geodesic area preserved, no part spanning more than 300° of longitude |
| `zonal_mean` | RAS-0024 | NoData sentinel plus partial edge pixels; oracle loops pixel centres explicitly |

**Design rule carried from Step 0:** each prompt pins the contract tightly enough that
"correct" is decidable — `tag_points` states that every point appears exactly once,
`zonal_mean` states the pixel-centre rule, `segment_intersection` states that an overlap is
returned as a segment. The trap must live in the implementation, never in spec ambiguity.
Plan 14's Step 0 limitations section makes the same point: a vaguer spec would produce more
failures, but a vaguer spec is a requirements defect, not a finding.

**The oracle needs its own regression net.** A wrong oracle silently mislabels every model —
the failure mode this project exists to name, turned on itself. `tests/benchmark/test_oracles.py`
grades, per task, a known-good implementation written fresh in the test (all `PASS`) and a
known-trapped one — `buffer(0)`, WKB-hash dedupe, prefix-only geohash — which must come back
`SILENT` on the edge check specifically.

> **USER ACTION U1.** Review each new grader against the corresponding handbook reference
> solution and its `## Probing` section. Optionally author new GeoCase_Studies questions for
> the three traps the bank does not yet cover — geodesic/antimeridian buffering, UTM zone
> exceptions, and raster point sampling with NoData — so that every task carries a non-null
> `handbook_id`.

### Phase 4 — The OpenRouter runner

Create `src/geocase/benchmark/runner/`:

- `openrouter.py` — httpx client. Auth from `OPENROUTER_API_KEY` **only**; refuse to start if
  unset, never log it, never commit it. `usage: {"include": true}` for live cost accounting.
  Exponential backoff with jitter on 429 and 5xx, capped at ~5 attempts.
- `bare.py` — Track A. One completion; the prompt asks for exactly one fenced python block
  rather than a file. Tolerant extraction in `extract.py` (fence variants, missing language
  tag); an unparseable reply records `MISSING` with `detail: no code block`.
- `agentic.py` — Track B. Tool-calling loop with `run_python(code)` (sandboxed) and
  `submit_module(source)`. Turn cap 12, per-task token cap. **Fallback protocol** for models
  whose tool calling is absent or unreliable: `text-loop`, where the model emits
  ` ```python RUN ` blocks that the runner executes and feeds back, and a final
  ` ```python SUBMIT ` block. Which protocol ran is recorded per run so tracks are never
  silently mixed.
- `sandbox.py` — one venv per run from `configs/sandbox-requirements.txt`, pinned to the Step 0
  environment (shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, scikit-learn). Fresh temp workdir
  per task; `subprocess.run` with a 60 s timeout; environment scrubbed of `*_KEY`/`*_TOKEN`.
  This is **soft** sandboxing and the methodology page must say so, alongside a
  `docker run --network none` recipe for stronger isolation.
- `orchestrator.py` —
  `python -m geocase.benchmark run --config configs/models.yaml --track bare|agentic --trials 3 --out results/runs/`.
  Incremental per-trial state with `--resume` so a crash does not re-spend. Grades through
  `grade_in_subprocess`. `--dry-run` prints call count and a cost ceiling without spending.

`configs/models.yaml` carries defaults (trials 3, temperature 0.2, `max_turns` 12,
`exec_timeout_s` 60), a `budget.max_usd_total` with hard abort driven by OpenRouter's returned
`usage.cost`, and a model list of `{id, label, tracks, supports_tools}` seeded with free
entries (DeepSeek V3.1, Qwen3 Coder, Llama 4 Maverick) and paid ones (GPT-5 mini, Gemini 2.5
Flash), for the user to extend.

`pyproject.toml` gains a `bench` extra (`httpx`, `geocase[vector,raster]`, `scikit-learn` —
the last because committed generated modules may import it during re-grading), folded into
`dev`.

**Verify:** unit tests against a mocked transport (`tests/benchmark/test_runner.py`) covering
code-block extraction, retry, budget abort, turn cap and text-loop fallback; then one live
free-model smoke run locally. The runner never executes in CI.

> **USER ACTION U2.** Create an OpenRouter key and export `OPENROUTER_API_KEY` locally; choose
> the model list and set `budget.max_usd_total`.
>
> **USER ACTION U3.** Run the shakedown in order — `--dry-run`, then free models bare, free
> models agentic, then paid. Spot-check two generated modules and their gradings per model
> before committing the run directories.

### Phase 5 — The manual coding-agent protocol

For the agents that have no API and that only the author can drive. `runner/manual.py` plus
`docs/benchmark/manual-protocol.md`:

1. `python -m geocase.benchmark manual prepare --out DIR` builds the workdir — sandbox venv,
   `generated/`, per-task scratch dirs — and renders the prompts with **that directory's**
   absolute paths. This is the payoff from Phase 1's templating: the same prompts, new paths,
   reproducing the Step 0 condition exactly.
2. Per task: a **fresh** agent session, cwd set to the workdir, no repo access and no other
   context, prompt pasted verbatim, run to `DONE`, session closed. One task per session, order
   shuffled.
3. `python -m geocase.benchmark manual ingest --dir DIR --model-id … --protocol claude-code --trial N`
   grades in the sandbox and writes or extends the run directory.

**Verify:** a prepare → ingest round trip against a scripted fake agent that writes correct
modules, producing a `run.json` that `load_all_runs()` accepts.

> **USER ACTION U4.** Run the manual track: Claude Code at k=3 (superseding the migrated k=1
> Step 0 entry, whose n=1 status is the first limitation `RESULTS.md` lists), then Cursor and
> Codex CLI. Roughly 20 tasks × 3 trials per agent.

### Phase 6 — Scoring, rating, and the leaderboard

`scoring.py` fixes the definitions:

- **Trial outcome:** `MISSING` if the module or function is absent; else `SILENT` if any check
  is silent; else `LOUD` if any check is loud; else `CORRECT`. This matches the aggregation
  precedence already in `grade.py:383-399`.
- **Task verdict** per model and track: majority across k trials, ties broken worst-first
  (`SILENT` > `LOUD` > `MISSING` > `CORRECT`). **Stability** is the mean fraction of trials
  agreeing with the verdict.
- **Model metrics:** `silent_rate` (headline), `correct_rate`, `loud_rate`, `missing_rate`, the
  pooled trial-level silent fraction, and an edge-check-only silent rate as a secondary lens.
- **Ranking:** ascending `silent_rate`, then descending `correct_rate`, then ascending
  `loud_rate`. No opaque composite number — the table shows the three rates and the rank.

`scripts/generate_leaderboard.py` follows the repo's generator-plus-`--check` convention and
writes `docs/_generated/benchmark/`: `leaderboard.md` (both tracks, run dates, a prompt-hash
column flagging runs made against outdated prompts), `models/<slug>--<track>.md` (per-task by
per-trial matrix, cost, tokens), and `tasks/<task>.md` (trap card from `task.yaml` plus which
models fail it silently).

`mkdocs.yml` gains a Benchmark section: `docs/benchmark/index.md` (methodology — tracks,
taxonomy, contamination policy, sandbox trust model), the manual protocol, the generated
leaderboard, and the findings write-up; generated detail pages go under the existing
`not_in_nav` convention.

The methodology page also gets a short **"Grade your own implementations"** section: write
modules matching the task contracts, run
`python -m geocase.benchmark grade --generated DIR --json OUT`, read the four-way statuses.
This is a supported side use of the grading CLI — useful as a smoke test of a team's own
geospatial utilities against the trap catalog — and the section states its boundary plainly:
coverage is exactly the ~20 benchmark tasks, and code with different signatures or contracts
is out of scope unless someone authors a new task package for it.

**Create `.github/workflows/docs-deploy.yml`** — `mkdocs build --strict`, then
`upload-pages-artifact` and `deploy-pages` on push to main. None exists today. Delete the
stale `site/` directory and gitignore it. Add `python scripts/generate_leaderboard.py --check`
to `ci.yml`'s docs job, matching the coverage-matrix freshness gates at `ci.yml:141-155`.

**Verify:** `python scripts/generate_leaderboard.py && mkdocs build --strict &&
python scripts/generate_leaderboard.py --check`; the leaderboard renders with the migrated
Fable 5 run as its first row.

> **USER ACTION U5.** Set the repository's Pages source to "GitHub Actions", and approve the
> public framing and title of the leaderboard before the first deploy.

### Phase 7 — Stage 1 repositioning

- `README.md`, full rewrite: what the benchmark measures, the four-way taxonomy, the headline
  finding (`buffer_m` antimeridian, 2/2 trials, invisible to the agents' own geodesic radial
  check), the leaderboard link, how to run both tracks, how to add a task, and how to grade
  your own implementations against the oracles. The catalog is
  demoted to a single history paragraph pending Stage 2.
- `pyproject.toml`: description becomes "A benchmark measuring silent failures in
  LLM-generated geospatial code"; keywords gain `llm`, `benchmark`, `evaluation`, `agents`;
  version `2.0.0.dev0`. The `pytest11` entry point and the `Framework :: Pytest` classifier
  stay until Stage 2.
- `docs/index.md` becomes benchmark-first.

**Verify:** the full local CI — `python -m pytest tests -q`, `ruff format --check src tests`,
`ruff check src tests`, `mypy src`, `mkdocs build --strict`, and the catalog `--check` scripts,
which stay green because the catalog is untouched until Stage 2.

### Phase 8 (optional) — Contamination hardening

The prompts are public on GitHub, so a model trained on this repository could memorise the
answers. Mitigations in order of cost:

1. Already in the schema after Phase 2: `prompt_sha256`, date-stamped runs and pinned model
   snapshot ids, so the leaderboard can flag any run postdating a prompt's publication.
2. `variants.py` — seeded parametric draws for the numeric tasks (buffer centre longitude near
   ±180, raster origin and sentinel, box coordinates, cluster latitudes, tile z/x/y). The
   graders already compute oracles from first principles, so they simply take the drawn
   parameters; prompts gain `{params}` slots and `variant_seed` is recorded. Held-out seeds
   chosen at run time mean the oracle shifts per run.
3. A stated policy in the methodology page: results for models released after task publication
   carry a contamination caveat unless run against a fresh variant seed.

---

## Stage 2 — Archive the catalog machinery

**Phase 9. Precondition: the leaderboard is live with at least three models across both
tracks** — that is, after U3 and U4. Nothing here starts before the benchmark stands on its
own.

**Delete** the public catalog surface: `src/geocase/pytest_plugin/` together with the
`pytest11` entry point, the marker declarations and the `Framework :: Pytest` classifier;
`src/geocase/api/`; the catalog `suites`, `selectors` and `manifests` public API; the one-line
assertion modules; `examples/`; `extended-manifests/`; the catalog-page and coverage-matrix
scripts. Their tests go in the same commit as the code they cover — expect the collected count
to fall from 1,179 to the benchmark suite plus retained internals.

**Keep, demoted to private:** `assertions/format_compliance.py` and `assertions/footprint.py`
per Plan 14's salvage path, plus `cases/`, the catalog loader core, `loaders/` and `data/`,
consolidated under `geocase._corpus/` — out of the docs and out of the strict mypy gate. The
corpus-feeding scripts survive only if a benchmark fixture actually uses them; since the
graders build their fixtures inline, the likely answer is that they do not. This is a decision
point at execution time, not a foregone conclusion.

**CI:** drop the GDAL-container catalog job, or reduce it to a `_corpus` checksum freshness
check if `_corpus` survives. The tests and docs jobs remain.

**Docs:** catalog user guides move to `docs/archive/` with tombstone notes; `philosophy.md` is
rewritten for the benchmark; `CHANGELOG.md` gains the 2.0.0 breaking-change entry.

**Verify:** `python -m pytest tests -q`; `python -m build && python scripts/verify_dist.py`;
in a clean venv, `pip install dist/*.whl && python -c "import geocase.benchmark"`; and
`pytest --co -q` in a scratch project to confirm the plugin no longer auto-registers.

> **USER ACTION U6.** Approve the deletion scope — particularly whether `_corpus` survives at
> all — and settle the PyPI strategy: leave `1.0.0rc1` published with a 2.0 breaking-change
> notice, or yank it. Decide whether the conda `recipe/` is abandoned.

---

## Traps

1. **The oracle is now the thing that can lie.** A wrong oracle mislabels every model, and it
   would be the exact failure this project is named after. Phase 3's known-good and
   known-trapped self-tests are not optional, and U1's review is the second gate.
2. **Never grade against the fixture corpus.** Plan 14's trap 7 stands unchanged and is now
   permanent policy rather than a Step 0 precaution: oracles are computed from `pyproj.Geod`
   and first principles. This is what makes Plan 13 optional rather than blocking.
3. **A leaked hint invalidates a run.** Plan 14's trap 6, applied continuously. Prompts must
   never name the trap, and `prompt_sha256` per run makes any edit auditable after the fact.
4. **Spec ambiguity is not a finding.** If a task fails because the contract was vague, the
   benchmark has measured its own prompt. Every prompt pins the decidable contract.
5. **Model-generated code is untrusted input, by design.** It only ever runs in a subprocess,
   in a dedicated venv, under timeout, with a scrubbed environment. CI executes only committed,
   reviewed modules.
6. **Tracks must not blur.** A model that falls back to `text-loop` is not doing the same thing
   as one using native tool calls. `protocol` is recorded per run and surfaced in the
   leaderboard.
7. **The pin test compares statuses, not floats.** Sandbox requirements are pinned and hashed
   per run, so a dependency upgrade that changes shapely's buffer output is attributable rather
   than mysterious.
8. **Self-grading is a side door, not a second product.** Grading human-written modules is
   documented and supported because the CLI gets it for free, but expanding it — new
   signatures on request, adapters for existing codebases, a "correctness suite" framing —
   is Plan 14's rejected library thesis returning through the back. New coverage arrives
   only as new benchmark tasks, on the benchmark's terms.
9. **Single-family evidence is the standing weakness.** `RESULTS.md` lists it first: the only
   run so far is Claude, the same family that authored both GeoCase and the harness. Until U3
   and U4 land, every published number carries that caveat explicitly.

---

## Verification

```bash
# Phase 1 — the port changes nothing
python -m pytest tests/benchmark -q
python -m geocase.benchmark grade --generated results/runs/2026-08-09_claude-fable-5_agentic-manual/generated/trial1 --json /dev/stdout

# Phase 2 — every committed run re-grades to its recorded statuses
python -m pytest tests/benchmark/test_results_pin.py -q

# Phase 3 — oracles catch a known-trapped implementation, pass a known-good one
python -m pytest tests/benchmark/test_oracles.py -q
GEOCASE_STUDIES_PATH=~/projects/GeoCase_Studies python -m pytest tests/benchmark/test_registry.py -q

# Phase 4 — runner logic without spending anything
python -m pytest tests/benchmark/test_runner.py -q
python -m geocase.benchmark run --config configs/models.yaml --track bare --dry-run

# Phase 6 — the leaderboard is generated, current, and builds
python scripts/generate_leaderboard.py && python scripts/generate_leaderboard.py --check
mkdocs build --strict

# Phase 7 — the full gate
python -m pytest tests -q
ruff format --check src tests && ruff check src tests && mypy src

# Phase 9 — the surface actually shrank, and the plugin is gone
python -m build && python scripts/verify_dist.py
```

---

## User-action checkpoints

| # | Phase | What you do |
|---|---|---|
| U1 | 3 | Review the ten new oracles against the handbook; optionally author questions for the three uncovered traps |
| U2 | 4 | Provide `OPENROUTER_API_KEY`; choose the model list and budget |
| U3 | 4 | Run the automated shakedown, free then paid; spot-check; commit the runs |
| U4 | 5 | Run the manual sessions: Claude Code at k=3, Cursor, Codex CLI |
| U5 | 6 | Enable GitHub Pages via Actions; approve the public framing |
| U6 | 9 | Approve the Stage 2 deletions and the PyPI/conda strategy |

---

## Files

**New**

- `src/geocase/benchmark/{taxonomy,registry,prompts,grading,scoring,results,variants,cli}.py`
- `src/geocase/benchmark/tasks/<name>/{task.yaml,prompt.md,grader.py}` × ~20
- `src/geocase/benchmark/runner/{openrouter,bare,agentic,sandbox,orchestrator,manual,extract}.py`
- `configs/models.yaml`, `configs/sandbox-requirements.txt`
- `results/runs/**` — committed run records, schema v2
- `scripts/generate_leaderboard.py`, `scripts/migrate_step0_results.py`
- `docs/benchmark/{index,manual-protocol}.md`, `docs/benchmark/findings/`
- `.github/workflows/docs-deploy.yml`
- `tests/benchmark/test_{registry,oracles,runner,scoring,results_pin}.py`

**Moved**

- `tests/benchmark/agent_baseline/grade.py` → `src/geocase/benchmark/tasks/*/grader.py`
- `tests/benchmark/agent_baseline/{prompts,generated,results.json}` →
  `results/runs/2026-08-09_claude-fable-5_agentic-manual/` and the task packages
- `tests/benchmark/agent_baseline/RESULTS.md` → `docs/benchmark/findings/2026-08-09-claude-fable-5.md`
- Stage 2: `src/geocase/{cases,catalog,loaders,data}/` and the two kept assertion modules →
  `src/geocase/_corpus/`

**Modified**

- `pyproject.toml` — description, keywords, version, `bench` extra; Stage 2 removes the
  `pytest11` entry point and the pytest classifier
- `mkdocs.yml` — Benchmark nav section; Stage 2 archives the catalog guides
- `.github/workflows/ci.yml` — leaderboard freshness gate; Stage 2 removes the catalog job
- `README.md`, `docs/index.md`, `docs/plans/index.md`, `CHANGELOG.md`

**Deleted**

- `tests/benchmark/agent_baseline/` (Phase 2, after migration)
- `site/` (Phase 6)
- Stage 2: `src/geocase/pytest_plugin/`, `src/geocase/api/`, catalog suites/selectors/manifests,
  the one-line assertion modules, `examples/`, `extended-manifests/`, the catalog-page and
  coverage-matrix scripts, and their tests

**External — not modified, but load-bearing**

- `~/projects/GeoCase_Studies` — supplies the Group A trap survey behind the ten new tasks and
  the citation for each. Kept separate by design; the `GEOCASE_STUDIES_PATH` check in Phase 1
  is what stops the citations rotting silently (Plan 14, trap 8).

---

## Main risks, stated plainly

**1. The benchmark measures one model family.** This is the honest state today and the
strongest reason U3 and U4 come early. A leaderboard with one row is a finding about Claude,
not about coding agents.

**2. Contamination erodes the result over time.** Public prompts plus published answers is a
known decay path for every benchmark. Phase 8's parametric variants are the real defence;
hashing and date-stamping only make the decay visible.

**3. Cross-model tool-calling is inconsistent.** The agentic track is the one that produced the
finding worth publishing, and it is also the track most likely to break unevenly across
providers. The `text-loop` fallback keeps coverage, but a run where half the models fell back
is a weaker comparison and the leaderboard must show it.

**4. Twenty tasks is a small n.** Silent-failure rates over twenty tasks with k=3 are coarse. The
per-task matrix, not the headline rate, is where the real information sits — and a single
reproducible silent failure like `buffer_m` is worth more than a rate computed to two decimals.
