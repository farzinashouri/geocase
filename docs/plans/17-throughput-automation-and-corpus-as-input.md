# Plan 17 — Throughput, automation, and corpus-as-input

> **Status: proposed 2026-08-11.** Extends [Plan 15](15-geocase-as-benchmark.md) and
> [Plan 16](16-generalize-beyond-geospatial.md) rather than superseding either. Plan 15
> stands the benchmark up; Plan 16 generalises it beyond geospatial; this plan makes it
> *runnable* — the 2026-08-11 probe sweep landed 25 of 160 completions, and two committed
> runs record rate-limit damage as if it were model behaviour.
>
> Nothing here changes what the benchmark measures. Scoring stays deterministic assertion
> (CORRECT / SILENT / LOUD / MISSING); `named_trap` review stays manual (Plan 16 U7). No
> LLM-as-judge enters the scoring path.

## Context

The benchmark works. What is broken is everything around it: the runs cannot complete,
the results cannot be trusted, and the workflow is six scripts held together by the
operator's memory.

**Three verified problems, in priority order.**

**1. The runner cannot survive a free-tier 429.** `openrouter.py:70` sets
`max_retry_after = 10.0` as a *class attribute*. When OpenRouter answers
`Retry-After: 24`, `chat()` raises immediately (`openrouter.py:162-166`) — it never
sleeps. `contamination_probe.py` exposes `--task-budget` (which sets `max_total_seconds`)
but **no flag reaches `max_retry_after`**, so no invocation can fix this from the CLI.
The 2026-08-11 probe sweep landed **25 of 160** completions. The real limits: `:free`
variants get **20 RPM account-wide** and **50 requests/day** under $10 lifetime credit,
rising to **1000/day** at ≥$10 (openrouter.ai/docs/api-reference/limits).

**2. Rate-limit damage is being recorded as model results.**
`results/runs/2026-08-10_nvidia-nemotron-3-super-120b-a12b-free_bare` grades
`{CORRECT: 4, LOUD: 2, MISSING: 14}` — the 14 MISSING are `api_failure` metas, not
model behaviour. Read naively that is "20% correct"; on what actually landed it is 67%.
Neither is publishable, and nothing on disk says so. **No `run.json` exists for any bare
run** (`manual ingest` writes one; `run_bare_track` does not), so there is no run-level
record of cost, model label, or integrity anywhere.

**3. The corpus is unused and the reason is a rule nobody has read carefully.** 135 cases
(4.2MB, bundled in the wheel) sit unreferenced by the benchmark. Trap 2 says "never grade
against the fixture corpus" — it forbids corpus *expected values*. It says nothing about
corpus *input bytes*. Meanwhile `zonal_mean` and `sample_at` synthesize rasters into
`tempfile.mkdtemp()` that duplicate cases already on disk.

Plus a comparability gap: Claude's 9/10 was **agentic on 10 tasks**; gpt-oss-20b's 12/20
was **bare on 20 tasks**. Publishing those in one table would be the benchmark lying
about itself.

**Intended outcome.** A sweep that runs to completion unattended, results that carry their
own integrity flag, and the corpus earning its place as input fixtures without touching
trap 2.

**Decisions made:** $20 credit / `max_usd_total: 15.00`; corpus mechanism + 2 new tasks,
no migration of existing graders; bad runs flagged `publishable: false`, kept, re-run.

---

## Phase 1 — Throughput

### 1.1 Retry policy becomes instance state

`src/geocase/benchmark/runner/openrouter.py` — convert the five class-attribute knobs to a
frozen dataclass passed at construction. Keep class attributes as defaults so
`client.max_total_seconds = x` (`contamination_probe.py:106`) still works.

```python
@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    max_timeout_attempts: int = 2
    max_retry_after: float = 10.0
    backoff_base: float = 2.0
    max_backoff: float = 60.0
    max_backoff_long: float = 300.0      # used only when honoring a long ask
    max_total_seconds: float = 120.0
    honor_long_retry_after: bool = False # opt-in
```

The branch at `openrouter.py:162-166` becomes: if the server's ask exceeds
`max_retry_after` **and** `honor_long_retry_after` is false, raise as today; otherwise
sleep `min(wait, max_backoff_long)`. `max_backoff = 60.0` must not clamp an honored
`Retry-After: 300` — that is why `max_backoff_long` is separate.

`honor_long_retry_after` stays **off by default**. A run that sleeps 24s × 5 × 26 is
indistinguishable from a hang. When on, log every long sleep with its wake time.

### 1.2 A real rate limiter

New `src/geocase/benchmark/runner/limiter.py`. The 20 RPM cap is **account-wide**, so
`--delay` between sequential calls paces nothing once models interleave.

```python
class RateLimiter:
    """Thread-safe token bucket. rpm=None disables (paid models)."""
    def __init__(self, rpm: float | None, *, burst: int | None = None): ...
    def acquire(self) -> float: ...          # blocks, returns seconds waited

class DailyQuota:
    """Per-day request cap persisted to disk, so a same-day re-run does not
    re-spend a quota already burnt."""
    def __init__(self, path: Path, limit: int | None): ...
    def take(self, n: int = 1) -> None: ...  # raises QuotaExhaustedError
```

`OpenRouterClient.chat` calls `acquire()` before **every** POST including retries — a
retry consumes RPM budget too, which the current code ignores.

Config block read by both the orchestrator and the probe script:

```yaml
limits:
  rpm: 18                              # under the 20 RPM :free cap
  requests_per_day: 950                # 1000/day at >=$10 lifetime credit
  quota_file: .geocase_quota.json      # gitignored, local operator state
retry:
  max_retry_after: 60
  honor_long_retry_after: true
  max_total_seconds: 180
```

`configs/models-free.yaml` gets `rpm: 18`. `configs/models.yaml` gets `rpm: null`.

### 1.3 Fix the phantom "wrote"

`scripts/contamination_probe.py:171` prints `wrote {path}` outside the write loop. When
every probe fails, nothing is written — verified: three models printed "wrote" on
2026-08-11 with no file on disk. A silent failure in the silent-failure benchmark's own
tooling; name it as such in the commit.

Print `NO probes landed — nothing written` to stderr and return non-zero. Regression test
in `tests/benchmark/test_probe_script.py`: a transport that always 429s must create no
file **and** exit non-zero.

### 1.4 Shared pacing flags

New `src/geocase/benchmark/runner/policy.py` with `add_pacing_args(ap)` and
`policy_from_args(args, config)`, used by both `orchestrator.main()` and
`contamination_probe.main()` so the two cannot drift:

```
--rpm FLOAT  --max-retry-after FLOAT  --honor-retry-after
--task-budget FLOAT  --max-usd FLOAT
```

### 1.5 Budget guardrails

`configs/models.yaml` already carries paid ids with prices — including
`anthropic/claude-{haiku-4.5,sonnet-5,opus-5}` at lines 71-79. No new config file needed;
set `budget.max_usd_total: 15.00` and add `max_usd_per_model` so one long-running
reasoning model cannot eat the budget before the cheap models are reached.

Extend `plan_run` to estimate spend, not just call count:

```python
@dataclass
class RunPlan:
    calls: int; models: list[str]; trials: int
    budget_ceiling_usd: float | None
    est_usd: float | None            # NEW
    est_by_model: dict[str, float]   # NEW
```

Refuse to start without `--yes` when `est_usd > 0.5 * budget_ceiling`. Note a real gap
worth a comment: `CostTracker.add` is called only on success
(`orchestrator.py:158`), so a failed-but-charged call goes untracked.

---

## Phase 2 — One entry point

### 2.1 `sweep`

New `src/geocase/benchmark/runner/sweep.py`, dispatched from `cli.py` beside the existing
`run`/`grade`/`manual` subcommands.

```
python -m geocase.benchmark sweep --config configs/models.yaml --domain geo \
  --stages probe,run,grade,report --trials 3 [--dry-run] [--yes]
```

Stages are **separately resumable and idempotent, driven by what is on disk** — no state
file. `probe` skips tasks already recorded (existing logic, `contamination_probe.py:118`);
`run` skips modules that exist and are not `api_failure` (`orchestrator.py:117-123`);
`grade` regrades any `trial*/` whose `graded.json` is missing or older than its newest
`.py`.

The `report` stage **refuses to run while any `named_trap` is null**, printing the count
and the `review_probes.py` command. That keeps U7/U8 manual while making the blocker
visible. `scripts/judge_probes.py` is **not** wired in — that would make LLM-as-judge the
path of least resistance in a benchmark whose entire premise is deterministic assertion.

### 2.2 `status`

The command whose absence let every problem above go unnoticed.

```
python -m geocase.benchmark status [--config C] [--domain geo]
```

Prints per model: probes landed/reviewed, per-trial completion, whether `graded.json` is
current, and a BLOCKERS section (unreviewed replies, stale gradings, runs with
`api_failure > 0`). **Exits non-zero when a blocker exists** so it works as a pre-commit
gate.

### 2.3 `run.json` for bare runs — highest-value change here

New `src/geocase/benchmark/runner/record.py`:

```python
def write_bare_record(run_dir: Path, *, model: dict, trials: int, date: str,
                      config: dict, outcomes_by_trial: dict[int, list[TrialOutcome]],
                      cost_usd: float | None) -> dict: ...
```

Reuse `manual._load_or_init_record`'s shape verbatim so one reporting path serves both
tracks. `track: "bare"`, `protocol: "openrouter-chat"`, plus:

```json
"integrity": {"tasks_attempted": 20, "api_failures": 14, "publishable": false}
```

`publishable: false` whenever `api_failures > 0`. This is what stops
"4 CORRECT / 14 MISSING" from ever being read as a model result.

Backfill records for the 5 existing runs; `super-120b` (14 failures) and `nano-30b`
(18 failures) get `publishable: false` and are re-run under Phase 1 pacing.

### 2.4 Commit gradings

`nano-30b` has no `graded.json` at all. Generate the missing one, then extend
`tests/benchmark/test_results_pin.py` to assert every committed `trial*/` has a
`graded.json` that regrades to its recorded statuses.

No Makefile — a fourth invocation path is a fifth source of drift.

---

## Phase 3 — Corpus as INPUT, never as ORACLE

### 3.1 The distinction, enforced mechanically

- A **fixture** is a file path handed to the model's function. It carries no expectation.
- An **oracle** is a value computed by `pyproj.Geod` / first principles in `grader.py`.
- The rule that separates them: **a grader may read a fixture's bytes; it may never read
  the fixture's `case.yaml`.** Every leak vector — `assertions`, `risk_types`,
  `params.crosses_dateline` — lives in that one file.

### 3.2 Mechanism

`task.yaml` gains an optional key (existing 20 geo `task.yaml` files stay untouched):

```yaml
fixtures:
  - name: poly
    case_id: classic_antimeridian_polygon
    file: geometry.geojson
    sha256: <pinned>
```

New `src/geocase/benchmark/fixtures.py`:

```python
def stage_fixtures(task: TaskMeta, dest: Path) -> dict[str, Path]:
    """Copy declared fixture FILES into dest, verifying sha256.
    Data bytes ONLY — never case.yaml, notes.md, checksums.sha256."""
```

Three enforcement points that turn trap 2 from a promise into a test:

1. `stage_fixtures` carries an explicit denylist (`case.yaml`, `notes.md`,
   `checksums.sha256`) and raises on any attempt to copy them.
2. `tests/benchmark/test_fixture_isolation.py` greps every `tasks/*/grader.py` for
   `case.yaml`, `assertions`, `risk_types`, `list_cases`, `get_case`, `load_case`,
   `geocase.catalog`, `geocase.cases` — fails on any hit.
3. `fixtures.py` is the **only** module under `benchmark/` permitted to import
   `geocase.catalog` (it needs `case_roots_by_id()`); the same test asserts that.

**Trap 3 is avoided by construction on both tracks.** Bare: the model receives only
`bare_prompt(task)` — fixtures are staged grader-side at grading time, so nothing about
the corpus reaches the model and **no prompt hash changes**. Agentic: `manual.prepare`
stages into `workdir/data`, where the agent sees a `.tif`, not a case directory. The
sandbox venv still does not install `geocase`.

### 3.3 Two new tasks

Chosen for trap quality, not corpus coverage:

1. **`geojson_bounds`** using `classic_antimeridian_polygon` — the polygon's longitudes
   jump +179 → −179, so a naive `bounds` returns a bbox spanning the whole planet,
   without error, looking plausible. The textbook silent failure, and the oracle is
   trivially first-principles (assert the returned bbox does not span 358° of longitude).
   Strongest new task available in the repo's reach.
2. **`shapefile_attrs`** using `shapefile_field_truncation` / `shapefile_encoding_legacy`
   — a genuinely new trap category (`encoding`) with no geodesy. DBF's 10-char field
   limit is normative, so the oracle is stated from the spec, not read from `case.yaml`.

Each needs `task.yaml`, `prompt.md`, `probe.md`, `grader.py`, and a GOOD/TRAPPED pair in
`test_oracles.py` (auto-enrolled via `NEW_TASKS = sorted(GOOD)`).

**Explicitly not doing:** migrating `sample_at`/`zonal_mean` to corpus rasters. Their
synthetic fixtures are 20 lines and the oracle knows the expected value *because it wrote
the raster*; swapping in corpus files means re-deriving that by reading them — more code,
same measurement, and it perturbs `graded.json` for committed runs. Also skipping
`polygon_is_valid` (shapely's `is_valid` is the settled canonical answer — measures
recall) and `null_island_point` / `out_of_bounds_coordinates` (too easy to state as a
contract; a model that fails is failing the spec, not the trap).

Task count goes 26 → 28, so cross-run comparison must be per-task on the intersection of
tasks present in both runs. `run_report.py` states the intersection explicitly.

### 3.4 How much of the corpus this actually uses — stated plainly

**2 of 135 cases.** The remaining ~133 stay unreferenced, exactly as today. That is the
honest yield, and the reason is structural rather than a lack of effort:

Every `case.yaml` carries **structural** assertions — `expected_epsg`, `expected_dtype`,
`expected_shape`, `expected_geometry_types`. **None carries an expected *computed*
result**: no expected area, no expected length, no expected buffer. The corpus answers
*"does your loader handle this file?"*; the benchmark asks *"does your function compute
the right number?"* Most of the 135 exist to break loaders, and the benchmark does not
test loaders.

The two selected are where a *loading* trap also yields a plausible wrong *number*. That
crossover is rare. Anyone extending this should expect to author oracles, not harvest
cases — the fixture is the cheap part.

Two paths are deliberately left open rather than taken here:

- **Sweep `special/` for more crossover candidates** (`dateline/` holds 6 cases, plus
  `invalid/`, `empty/`, `encoding/`). Possibly 5–8 further tasks. Each still needs its own
  first-principles oracle, `prompt.md`, `probe.md`, and GOOD/TRAPPED pair.
- **Extending `case.yaml` with computed expectations is rejected**, not deferred. Those
  values would have to be computed from `pyproj.Geod` anyway, and the moment a grader
  reads them from YAML the oracle's correctness depends on whatever wrote the YAML —
  Plan 15's trap 1, *"a wrong oracle would be the exact failure this project is named
  after."*

---

## Phase 4 — Close the comparability gap

`anthropic/claude-{haiku-4.5,sonnet-5,opus-5}` are already in `configs/models.yaml` on the
bare track. Run them on the same tasks, same single-completion protocol, k=3:

```bash
python -m geocase.benchmark sweep --config configs/models.yaml \
  --domain geo --trials 3 --stages run,grade --yes
```

The agentic Claude baseline covers **10 of 20** geo tasks. Either re-run agentic over all
20 via `manual prepare --domain geo`, or state the 10-task scope every time 9/10 is
quoted. The report generator must refuse to place a bare row and an agentic row in one
table without a `track` column — reuse the existing `protocol` field.

---

## Cost

Basis: measured **221 prompt / 3164 completion tokens** per bare task (n=65). Probes ≈
150 in / 1200 out. Prices from `configs/models.yaml`. Benchmark = 26 tasks × 3 trials =
78 calls/model.

| Model | Bench (78 calls) | Probes (26) |
|---|---|---|
| `openai/gpt-oss-20b` (paid — pairs with the committed free run) | $0.03 | $0.004 |
| `deepseek/deepseek-v4-flash` | $0.07 | $0.01 |
| `qwen/qwen3-coder-next` | $0.20 | $0.03 |
| `anthropic/claude-haiku-4.5` | $1.25 | $0.16 |
| `google/gemini-3.6-flash` | $1.88 | $0.24 |
| `anthropic/claude-sonnet-5` | $2.51 | $0.32 |
| **Subtotal** | **$5.94** | **$0.77** |

**≈ $6.71, +5.5% credit fee ≈ $7.08.** `budget.max_usd_total: 15.00` leaves headroom for
retries and one re-run. `claude-opus-5` is +$7.06 and optional. The $20 purchase also
lifts the free tier from 50 → 1000 requests/day, which independently unblocks the free
roster.

---

## Verification

```bash
# Phase 1 — pacing, retries, the phantom-write regression
python -m pytest tests/benchmark/test_runner.py tests/benchmark/test_probe_script.py -q
python -m geocase.benchmark run --config configs/models.yaml --domain geo --dry-run
#   expect: call count AND est_usd, per model

# Phase 2 — status is the gate; sweep is resumable
python -m geocase.benchmark status --config configs/models.yaml --domain geo
python -m geocase.benchmark sweep --config configs/models-free.yaml \
  --domain geo --stages probe,run,grade --dry-run
python -m pytest tests/benchmark/test_results_pin.py -q

# Phase 3 — trap 2 enforced, not promised
python -m pytest tests/benchmark/test_fixture_isolation.py -q
grep -rn "geocase.catalog\|geocase.cases\|case.yaml" src/geocase/benchmark/ \
  --include='*.py' | grep -v 'benchmark/fixtures.py'    # expect: empty
python -m pytest tests/benchmark/test_oracles.py -q     # 28 GOOD/TRAPPED pairs

# Constraint: the 51 committed prompt hashes are untouched
python -m pytest tests/benchmark/test_prompt_hashes.py -q

# Full gate
python -m pytest tests -q && ruff format --check src tests && ruff check src tests \
  && mypy src && mkdocs build --strict
```

---

## User-action checkpoints

| # | Phase | What you do |
|---|---|---|
| U11 | 1 | Purchase $20 OpenRouter credit (also lifts free tier to 1000/day) |
| U12 | 2 | Review probe replies, set `named_trap` by hand — `report` stage blocks until none are null |
| U13 | 3 | Review the 2 new oracles against their GOOD/TRAPPED pairs, as U1 did for geo |
| U14 | 4 | Spot-check two generated modules + gradings per model before committing runs |

---

## Deliberately not doing

- **`honor_long_retry_after` by default** — a run that silently sleeps 24s × 5 × 26 is
  indistinguishable from a hang.
- **Wiring `judge_probes.py` into `sweep`** — makes LLM-as-judge the path of least
  resistance in a benchmark built on deterministic assertion.
- **Migrating `sample_at`/`zonal_mean`** — low value, real regression risk, perturbs
  committed gradings.
- **Publishing any rate from a run with `api_failure > 0`** — the `integrity.publishable`
  flag makes this non-negotiable.
- **Any blended rate across geo + stdlib, or across bare + agentic** — already refused for
  domains via `_run_dir_suffix`; extend the same refusal to tracks.
- **A Makefile.**
