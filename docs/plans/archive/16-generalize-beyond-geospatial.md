# Plan 16 — Generalize the benchmark beyond geospatial

> **Archived — Phases 0–4 built 2026-08-10. Retained as an implementation log.** Three user actions were still open when this was archived (U7 the probe run, U9 the `stdlib` bare run, U10 the distribution rename); they are carried in the roadmap's **Open user actions** table at [`development-plan.md`](../development-plan.md), which is where open items live.
>
> The single active roadmap is [`docs/plans/development-plan.md`](../development-plan.md).

> **Status: Phases 0–4 implemented 2026-08-10** — the domain mechanism, the probe tooling,
> the six-task `stdlib` slate with oracle pairs, the run-path filters and the docs are built
> and green. What is *not* done is everything requiring a model or a human: the probe run and
> its `named_trap` review (U7), the oracle review (U8), the `stdlib` bare run (U9) and the
> repositioning/rename decision (U10). Consequently the `stdlib` slate is **provisional** —
> Phase 0 was built but has not yet been *run*, so no task has been cleared or cut on
> evidence, and the top-level README/`pyproject` framing is deliberately untouched pending
> both U10 and Phase 3 results.
>
> Extends [Plan 15](15-geocase-as-benchmark.md) rather than superseding
> it. Plan 15 stands the benchmark up as the product; this plan makes it a benchmark about
> *coding* rather than about *geospatial coding*, with GIS as the first and deepest domain.
> Nothing here starts before Plan 15's Phase 1 task packages and oracle self-tests exist —
> they do.

## Context

The benchmark measures one thing: the **silent-failure rate** of LLM-generated code — code
that returns a plausible wrong answer without raising, so the model's own verification cannot
see the bug. Plan 15 states the thesis directly ([line 30](15-geocase-as-benchmark.md)):

> That is the finding, and it is a finding about *measurement*, not about geospatial.

Today the repo cannot support that sentence. All 20 tasks are geospatial, so the claim that
"benchmarks that grade against test suites structurally cannot see this class" is asserted
about coding in general but evidenced only in GIS.

The instrument is already domain-agnostic. `taxonomy.py`, `grading.py`, `registry.py`,
`prompts.py`, `cli.py` and all of `runner/` — roughly 1,100 lines — contain **zero**
geospatial imports, and 4 of the 20 graders (`segment_intersection`, `utm_epsg_for`,
`cluster_points_m`, `position_at`) are already stdlib-only. Only the task *content* is geo.

There is live signal worth generalizing: two committed bare runs show a ~20–25% silent rate
(`gpt-oss-20b`: 12 CORRECT / 5 SILENT / 3 LOUD, and 11 / 4 / 4 / 1 MISSING).

**Intended outcome.** GeoCase becomes a general silent-failure benchmark. This plan builds
the domain mechanism, ships a validated second domain, and fixes in advance the rule for
adding domain 3+ — while protecting the only assets the project has: a reproducible finding
and an oracle nobody has caught lying.

### The two risks this plan is designed around

**1. Breadth without evidence.** The project's credibility rests on `buffer_m` — silent in
2/2 blind trials, invisible to the agents' own geodesic radial check. Six domains × 20 shallow
tasks with one model family would be **less** credible than 20 geo tasks with 8 models. So:
mechanism first, two domains proven properly, domain 3+ behind a pre-committed gate (Phase 5).

**2. Contamination — and it bites the new domains harder than the old ones.** Plan 15's
Phase 8 frames contamination as *this repo's prompts leaking into training data*, mitigated by
`prompt_sha256`, date-stamping and parametric variants. Non-geo traps have a different and
worse problem: **the traps themselves are canonical pedagogy**, independent of anything this
repo publishes. "The naive one-pass variance formula suffers catastrophic cancellation" is in
Knuth and is the motivating example for Welford's algorithm; "don't split CSV on commas" is
among the most-repeated advice on Stack Overflow. `buffer_m` is not in that class — and the
models failed it anyway, while actively self-verifying. Phase 0 measures this instead of
guessing at it.

---

## Verified ground truth

Checked against the working tree on 2026-08-10, not assumed:

- **All 51 committed `prompt_sha256` values reproduce exactly** from
  `bare_prompt(get_task(name))`. This makes a hash-stability regression test cheap and
  meaningful — it is the gate for Phase 1.
- **`TaskMeta` silently drops unknown YAML keys.** `model_config` is unset, so pydantic's
  default `extra="ignore"` applies; validating a `task.yaml` dict carrying `domain: "stdlib"`
  succeeds and the field vanishes. In a project about silent failure this is the wrong
  default, and it is fixed in Phase 1 regardless of the rest.
- **`run_bare_track(tasks=...)` exists but `orchestrator.main()` never passes it.** The `run`
  path has no task filter at all, so `--domain` means wiring a parameter through
  `plan_run` and `run_bare_track`, not adding a flag.
- **`str.format` in `bare.py:28` is not a bug.** Braces in the substituted paragraph are safe;
  only braces in the template itself would break. Switching to `.replace()` for consistency
  with `prompts.py` is optional cleanup.

---

## Phase 0 — Contamination probe

**This runs before any non-geo task is authored, and its results decide the slate.**

Contamination inflates pass rates; it does not fabricate silent failures. A model that has
memorised Welford's algorithm and writes it scores CORRECT, and arguably a fair CORRECT —
knowing the standard algorithm *is* competence. Memorisation cannot produce a *false* SILENT.

So the failure mode is not wrong numbers. It is a **measurement-uninformative** result: the
new domain scores a near-zero silent rate and nobody can tell whether models are genuinely
good at numerics or have simply memorised these particular war stories. That would waste the
phase and invite exactly the unearned comparative claim Phase 5 forbids.

**Note that parametric variants (Plan 15 Phase 8) do not fix this.** Randomising the offset in
`[1e9 + k]` changes nothing: the model either reaches for a two-pass or Welford form or it
does not, and the specific constant is irrelevant. Variants defend against *prompt*
memorisation, not *concept* memorisation. Phase 8 is not the mitigation here and the
methodology page must not imply that it is.

### The probe

For each candidate task, in a **separate session from any benchmark run**, ask the model an
open question — "what are the common pitfalls when implementing X?" — where X is the task's
one-line contract with no mention of any edge case. Record whether the model names the trap
unprompted.

- `scripts/contamination_probe.py`, reusing `runner/openrouter.py`. Writes
  `results/probes/<date>_<model-slug>.json`: `{task, probe_prompt_sha256, named_trap: bool,
  reply}`, with `named_trap` set by human review, not string matching — a model can describe
  the antimeridian problem without using the word.
- Probe prompts live at `src/geocase/benchmark/tasks/<name>/probe.md`, optional, hashed like
  any other prompt.

### What it buys

1. **Per-task, per-model contamination flags published alongside results**, rather than a
   prose caveat. A near-zero silent rate on a task 5/5 models can describe is a different
   fact from one on a task none can.
2. **Task selection decided empirically.** If a candidate is named by every model probed, it
   measures recall, not the phenomenon — cut it before spending a run.
3. **A stronger version of the existing headline finding.** Run the probe against the 20 geo
   tasks too, `buffer_m` included. If models can *describe* the antimeridian trap and still
   *fall into it* while self-verifying, knowing-but-not-applying is a substantially more
   interesting claim than not-knowing — and it is the claim most resistant to the objection
   that the benchmark just tests obscure knowledge.

**Verify:** probe the two models already in `results/runs/` across all 20 geo tasks plus the
Phase 2 candidates. Cheap: one short completion per task per model, no sandbox.

> **USER ACTION U7.** Review each probe reply and set `named_trap`. This is a judgement call
> and must not be automated — the same discipline as Plan 15's U1 oracle review.

---

## Phase 1 — The domain mechanism (no new claims)

The smallest change that proves the mechanism end-to-end. One reviewable PR; no model calls.

**`src/geocase/benchmark/registry.py`**

- Add `domain: str = "geo"` to `TaskMeta`. **Defaulted, so all 20 existing `task.yaml` files
  stay untouched** — zero migration, zero re-grade. Do not backfill `domain: geo`; `task.yaml`
  is not hashed into run metadata, so leaving it implicit costs no auditability and saves 20
  empty diffs.
- Add `model_config = ConfigDict(extra="forbid")`.
- Replace the single-field `@field_validator("trap_category")` (`registry.py:38-43`) with an
  `@model_validator(mode="after")` — validating `trap_category` against the task's own domain
  needs cross-field access.

**`src/geocase/benchmark/taxonomy.py`** — a dict of frozensets, *not* namespaced strings:

```python
GEO_TRAP_CATEGORIES = frozenset({...the existing 13, unchanged...})
STDLIB_TRAP_CATEGORIES = frozenset({...})
TRAP_CATEGORIES_BY_DOMAIN = {"geo": GEO_TRAP_CATEGORIES, "stdlib": STDLIB_TRAP_CATEGORIES}
TRAP_CATEGORIES = GEO_TRAP_CATEGORIES   # back-compat alias
```

Why this beats namespacing (`geo:antimeridian`):

- `tests/benchmark/test_taxonomy.py:31` asserts exact set equality. With the alias it **passes
  unchanged and still means what it meant**. Namespacing rewrites all 13 strings inside the
  pin, which destroys its value — you could no longer distinguish a deliberate rename from
  accidental vocabulary drift in that diff.
- No churn across 20 `task.yaml` files.
- The closed-vocabulary guarantee gets *stronger*: a geo task cannot declare a numeric
  category, which one flat namespaced set could not prevent.

**`src/geocase/benchmark/domains.py`** (new — keeps `taxonomy.py` about statuses):

```python
@dataclass(frozen=True)
class Domain:
    name: str
    requirements: Path       # configs/sandbox-requirements[-<name>].txt
    package_blurb: str       # the exact sentence injected into prompts
    trap_categories: frozenset[str]

DOMAINS: dict[str, Domain] = {"geo": ..., "stdlib": ...}
```

**`src/geocase/benchmark/runner/bare.py`** — make the dependency line a slot:

```python
BARE_TEMPLATE = """You are writing one small self-contained Python module.

{paragraph}

Requirements:
- {deps}
- Importing the module must have no side effects.
- Reply with exactly one fenced ```python code block containing the complete module, and nothing else after it.
"""
```

`GEO_DEPS` must be the **byte-identical** existing sentence (`"You may use the standard
library plus any of: shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, scikit-learn."`).

**The gate — `tests/benchmark/test_prompt_hashes.py` (new).** Every `*.meta.json` under
`results/runs/*_bare/` must still hash-match `bare_prompt(get_task(...))`. All 51 match today.
This turns "we think we did not change the prompts" into a CI-enforced fact and retroactively
guards both committed runs against any future prompt edit. Roughly 15 lines, and it is the
reason the geo prompts can be left alone with confidence.

**`configs/sandbox-requirements-<domain>.txt`** per domain. For a stdlib domain the file is
comments only: `ensure_sandbox` runs `pip install -r` on it successfully and produces a bare
venv fast, which makes the "standard library only" claim structurally true rather than merely
stated.

**One task**, whichever Phase 0 clears with the lowest contamination. `test_oracles.py:293`
uses `NEW_TASKS = sorted(GOOD)`, so adding a `GOOD`/`TRAPPED` pair is the entire test-side
change — that auto-enrollment is the best-designed thing in the repo for this extension.

**`--domain` filter on `grade` only** (Phase 3 does `run`).

**Verify:**

```bash
python -m pytest tests/benchmark -q
python -m pytest tests/benchmark/test_prompt_hashes.py -q     # all 51 hashes still match
python -m pytest tests/benchmark/test_taxonomy.py -q          # geo pin unchanged
ruff format --check src tests && ruff check src tests && mypy src
```

---

## Phase 2 — The second domain's task slate

Candidates below were validated against the grader contract: controls PASS on both
implementations, edge PASSes on good, and the trapped version returns a **wrong value with no
exception**. All are `packages: []`, `handbook_id: null`, `origin: plan16`. Template:
`src/geocase/benchmark/tasks/segment_intersection/`.

**Every entry is provisional until Phase 0 clears it.** The contamination column is the
selection criterion, not a footnote.

| Task | Trap | Edge case | Trapped impl returns | A priori contamination risk |
|---|---|---|---|---|
| `dedupe_labels` | normalization | NFC vs NFD `"Ångström"` → 1 entry | 2 entries — `casefold()` without NFC | **Low** — trapped version already does the sophisticated thing |
| `group_means` | null-propagation | all-`None` group → `None` | `0.0` — the `v or 0.0` idiom | **Low–medium** |
| `allocate_cents` | rounding-residue | `(1000, [1,1,1])` must sum to 1000 | `[333,333,333]`, sums to 999 | **Medium** — a Fowler money-pattern classic |
| `elapsed_hours` | dst-transition | Nov 1 2026 midnight→midnight `America/New_York` → 25.0 | `24.0` — naive `fromisoformat` subtraction | **Medium–high** — every timezone blog post |
| `sample_variance` | cancellation | `[1e9+1 … 1e9+4]` → 1.667 | **`0.0`** — textbook one-pass form | **High** — motivating example for Welford |
| `parse_delimited` | quoting | `'a,"b,c",d'` → 3 fields | 4 fields — bare `.split(",")` | **High** — top Stack Overflow advice |

### The `sample_variance` tension, stated plainly

It is the closest structural analogue to `buffer_m` anywhere in numerics: catastrophic
cancellation returns exactly `0.0` for data with obvious spread, and the model's natural
self-check on small integers is **invariant under the defect** — the same property that made
the agents' geodesic radial check blind. That is precisely why it is attractive.

It is also the most likely to be memorised, and that is not a coincidence: the reason it is
such a clean example of cancellation is the reason it is in every textbook. Phase 0 settles
it empirically rather than by argument. If models name it unprompted and still write the
one-pass form, keep it — that is the knowing-but-not-applying finding, and it is the strongest
result available. If they name it and write Welford, cut it.

### Selection rules — stricter than Plan 15's

Plan 15's traps 3 and 4 stand. Three more, and they apply to every future domain:

- **Reject canonical-pedagogy traps unless Phase 0 shows models fall in anyway.** If the trap
  is the subject of a named algorithm or a top Stack Overflow answer, it measures recall until
  proven otherwise.
- **Reject ambiguous contracts.** `percentile` is out: nearest-rank and linear interpolation
  are *both defensible* (NumPy ships nine methods), so pinning one measures reading
  comprehension. `round_half_up` is out: pinning it requires the prompt to say "half-up,"
  which approaches naming the trap.
- **Concurrency is ruled out permanently, in writing.** Nondeterministic oracles cannot
  distinguish SILENT from noise, and per **trap 1** the oracle is the thing that must not lie.

Practical notes: write `dedupe_labels`' NFC/NFD literals as `\u` escapes in both grader and
oracle strings and assert the inputs differ in `len()`, so a normalising editor cannot
silently break the task. `group_means` must state the SQL-`AVG` rule explicitly (nulls
excluded from numerator *and* denominator; all-null group → `None`) — stating the contract is
not leaking the trap.

Each task needs `task.yaml`, `prompt.md`, `probe.md`, `grader.py`, and a `GOOD`/`TRAPPED` pair
in `test_oracles.py`.

---

## Phase 3 — The run path

- Shared `select_tasks(names=None, domain=None)` in `cli.py`, beside the existing filter at
  `cli.py:149-151`. `--domain` and `--tasks` intersect (AND).
- **`--domain` on `grade` defaults to `None` (all domains).** Grading everything and getting
  MISSING for absent modules is documented existing behaviour (`test_port_pin.py:37`).
- **Any filter selecting zero tasks exits non-zero.** Today `--tasks nonexistent` prints
  `0 of 0 graded` and exits 0 — a silent failure in the benchmark's own tooling. Fix for
  `--tasks` at the same time.
- Wire `--domain` through `orchestrator.main()` → `run_bare_track(tasks=...)` **and**
  `plan_run`, so `--dry-run`'s call count and cost ceiling stay truthful.
- **Partition output by domain**: keep `{date}_{slug}_bare` for geo (preserving existing paths
  and resume behaviour), use `{date}_{slug}_bare_{domain}` otherwise. **Never print a
  cross-domain aggregate** — a blended silent rate over hand-picked tasks from different
  domains is not a meaningful number.
- **`manual prepare --domain` is required; mixed-domain workdirs are refused.** It builds one
  venv and writes one `sandbox_requirements_sha256`; a mixed workdir would record a hash
  describing an environment wrong for half the tasks — the provenance lie **trap 7** exists to
  prevent. Defaulting to `geo` would be worse than requiring the flag. Follows the existing
  protocol-mixing refusal at `manual.py:232-236`.
- Without this, the first `manual prepare` after Phase 2 silently hands the operator 26
  sessions instead of 20 — `plan_run` and `manual.prepare` both iterate `all_tasks()` today.
- Give `packages` a real job: a CI test asserting `set(task.packages) ⊆ domain packages`. The
  *prompt* advertises the whole domain environment, never the per-task list — a prompt naming
  only `shapely` for `area_m2` would hint which library the oracle expects (**trap 3**).

**Run** the new domain against the same two models already in `results/runs/`. Same models,
different domain, is the only comparison that isolates the variable.

---

## Phase 4 — Repositioning

Only after Phase 3 has produced results. Deliberately after evidence, not before.

- `README.md`, `docs/index.md`, `pyproject.toml` description: a benchmark for silent failures
  in LLM-generated code, **with geospatial as the first and deepest domain**.
- **Renaming the distribution is a separate decision, not folded in here.** `geocase` is
  published on PyPI and conda-forge, and Plan 15 kept the name as a pragmatic call. A rename
  costs a new package, redirects, and breaks `pip install geocase`. Revisit once a third
  domain exists — the name is a symptom of the identity question, not its cause.
- Methodology page gains a **Domains** section (what a domain is; the selection rules) and a
  **Contamination** section carrying Phase 0's per-task flags and stating plainly that
  parametric variants address prompt memorisation, not concept memorisation.

---

## Phase 5 — The rule for domain 3+

Two domains prove the abstraction; a third mostly proves premature generalisation. The gate,
fixed in advance so it can fire against this plan the way Plan 14's fired against its own:

> A new domain is added only when every existing domain has ≥3 models × k=3 on the bare
> track, and the newest domain has produced at least one silent failure reproducible across
> trials **on a task Phase 0 did not flag as contaminated**.

Candidates, in rough order of trap density: money/Decimal, text encoding beyond normalisation,
SQL semantics beyond NULL, serialisation round-trips, floating-point accumulation.

### The claim this licenses — and the one it does not

If the second domain shows a lower silent rate than the ~20–25% geo baseline, that is **not**
"geo is uniquely hard." Six hand-picked tasks with hand-picked traps are not a random sample
of either domain; the difficulty knob belongs to the task author, not the domain. What this
licenses is narrower and defensible: *the instrument detects silent failures outside
geospatial code* — precisely the claim Plan 15 line 30 already makes and currently cannot
support. Say that and no more. **Trap 9** already flags single-family evidence as the standing
weakness; a second unearned claim would be a poor trade.

---

## Traps

Plan 15's nine stand unchanged. Three more:

10. **Canonical traps measure recall, not the phenomenon.** A textbook pitfall that every
    model can recite tests memorisation. Phase 0 is the gate, and the answer is per-model, not
    global.
11. **Parametric variants do not defend against concept memorisation.** Plan 15 Phase 8
    protects against prompt leakage only. Claiming otherwise on the methodology page would
    be the project's own failure mode — a plausible-looking mitigation that does not hold.
12. **Cross-domain rates are not comparable.** Task difficulty is set by the author. The
    per-task matrix is the information; a blended headline number across domains is noise
    dressed as a finding, and Phase 3 refuses to print one.

---

## Files

**New**

- `src/geocase/benchmark/domains.py`
- `src/geocase/benchmark/tasks/<name>/{task.yaml,prompt.md,probe.md,grader.py}` × ~6
- `configs/sandbox-requirements-<domain>.txt`
- `scripts/contamination_probe.py`; `results/probes/**`
- `tests/benchmark/test_prompt_hashes.py`

**Modified**

- `registry.py` (`domain` field, `extra="forbid"`, model_validator) · `taxonomy.py`
  (`TRAP_CATEGORIES_BY_DOMAIN` + alias) · `runner/bare.py` (`{deps}` slot) · `cli.py`
  (`select_tasks`, non-zero on empty) · `runner/orchestrator.py` (wire `--domain`,
  domain-suffixed run dirs) · `runner/manual.py` (require `--domain`, refuse mixed) ·
  `tests/benchmark/test_oracles.py` · `docs/benchmark/quickstart.md` · `docs/plans/index.md` ·
  `mkdocs.yml`

**Untouched, deliberately**

- The 20 geo `prompt.md` files — editing them changes `prompt_sha256` and burns the cheap
  audit trail for nothing
- The 20 geo `task.yaml` files · `configs/sandbox-requirements.txt` · `_oracle_utils.py` ·
  all 20 geo graders

---

## Verification

```bash
# Phase 0 — contamination flags exist before any task is authored
python scripts/contamination_probe.py --config configs/models-free.yaml --dry-run
python -m pytest tests/benchmark/test_probe_prompts.py -q

# Phase 1 — mechanism works, nothing drifted
python -m pytest tests/benchmark -q
python -m pytest tests/benchmark/test_prompt_hashes.py -q     # all 51 hashes still match
python -m pytest tests/benchmark/test_taxonomy.py -q          # geo pin unchanged

# Phase 2 — oracles catch trapped impls, pass good ones, across all domains
python -m pytest tests/benchmark/test_oracles.py -q

# Phase 3 — filters are truthful and refuse empty selections
python -m geocase.benchmark run --config configs/models-free.yaml --domain stdlib --dry-run
python -m geocase.benchmark grade --generated DIR --domain nosuchdomain   # exits non-zero
python -m geocase.benchmark manual prepare --out ~/lab                    # fails: --domain required

# Full gate
python -m pytest tests -q && ruff format --check src tests && ruff check src tests \
  && mypy src && mkdocs build --strict
```

Spot-check two generated modules and their gradings per model before committing any run
directory — the U3 discipline from Plan 15.

---

## User-action checkpoints

| # | Phase | What you do |
|---|---|---|
| U7 | 0 | Review every probe reply and set `named_trap` by hand; decide the slate from the results |
| U8 | 2 | Review each new oracle against its known-good and known-trapped pair, as U1 did for geo |
| U9 | 3 | Run the new domain against the two existing models; spot-check before committing |
| U10 | 4 | Approve the repositioning framing; defer or schedule the rename decision |
