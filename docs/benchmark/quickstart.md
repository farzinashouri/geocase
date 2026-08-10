# Benchmark Quick Start

The GeoCase benchmark measures whether LLM coding agents write geospatial code
that **silently lies** — code that returns a plausible wrong answer without
raising anything, so the model's own verification cannot see the bug.

Every task grades into one of four outcomes:

| Status | Meaning |
|---|---|
| `PASS` | The value is correct within tolerance. |
| `SILENT` | A plausible wrong value came back and nothing was raised. **This is the headline metric.** |
| `LOUD` | An exception was raised — the model's own test run would have caught it. |
| `MISSING` | The module or the function is absent. |

A trial's verdict is the worst status it produced: `MISSING`, then `SILENT`,
then `LOUD`, else `CORRECT`.

!!! note "Status of this page"
    This documents the Plan 15 *minimum viable one-off*: the task packages, the
    oracles, the grading CLI, and a bare-track OpenRouter runner. The results
    store, the leaderboard, and the automated agentic track are not built yet.
    See [Plan 15](../plans/15-geocase-as-benchmark.md) for the full design.

---

## Install

Inside this repository, an editable install with the `bench` extra:

```bash
pip install -e ".[dev]"
```

The `bench` extra adds `httpx` (the OpenRouter client) and `scikit-learn`
(some generated modules import it). Grading alone needs neither an API key nor
a network connection.

---

## The fastest thing you can do: grade your own code

The grading CLI does not care who wrote the module. Any directory whose files
match the task contracts grades identically — model-written or hand-written.
That makes it a quick way to check your own geospatial utilities against the
same traps.

Write a module named `gen_<task>.py` exporting a function named `<task>`:

```bash
mkdir /tmp/mycode
cat > /tmp/mycode/gen_wkt_from_latlon.py <<'EOF'
def wkt_from_latlon(lat, lon):
    return f"POINT ({lat} {lon})"
EOF
```

Then grade it:

```bash
python -m geocase.benchmark grade --generated /tmp/mycode --tasks wkt_from_latlon
```

```text
operation        check                        kind     status   detail
wkt_from_latlon  parses_as_point              control  PASS     parsed POINT (52.5 13.4)
wkt_from_latlon  axis_order                   edge     SILENT   got x=52.5, y=13.4; expected x=13.4 (lon), y=52.5 (lat)

per-operation: 0 fully correct, 1 with SILENT failures, 0 with only LOUD failures, of 1 graded
```

That is the whole point of the project in five lines. The WKT parses, the
control check passes, and the axes are swapped — a bug that produces valid
output, plots somewhere in the ocean off Somalia, and raises nothing.

Drop `--tasks` to grade every task at once; anything you have not written comes
back `MISSING`. Add `--json out.json` to get machine-readable records.

To see it on real evidence, grade the ten modules from the original experiment:

```bash
python -m geocase.benchmark grade \
  --generated tests/benchmark/agent_baseline/generated --tasks buffer_m
```

Nine of those ten operations were fully correct. `buffer_m` across the
antimeridian was not, and it failed silently in both independent trials.

---

## The twenty tasks

Ten ported from the original experiment (`origin: step0`) and ten derived from
the trap survey (`origin: plan15`).

| Task | Trap | The edge case |
|---|---|---|
| `area_m2` | antimeridian | Box crossing ±180 — planar treatment computes the 358°-wide complement |
| `buffer_m` | antimeridian | 50 km buffer at lon 179.9 — the known silent failure |
| `length_m` | units-degrees | 1° at lat 60 is 55.8 km, not 111.3 km |
| `position_at` | antimeridian | Ship track interpolated across the dateline |
| `cluster_points_m` | units-degrees | A metre threshold converted to degrees breaks at high latitude |
| `utm_epsg_for` | zone-exceptions | Svalbard 33X and SW Norway 32V defeat the `lon/6` formula |
| `sample_at` | nodata | The `-9999` sentinel must read as "no data", not as a value |
| `label_point` | predicate-semantics | A donut's centroid lies in its hole |
| `tile_bounds` | y-flip | TMS row order is inverted relative to XYZ |
| `voronoi_cells` | ordering | Cell *i* must belong to point *i* |
| `tag_points` | predicate-semantics | A point on a shared edge: `within` drops it, `intersects` duplicates it |
| `fix_geometry` | topology-repair | `buffer(0)` on a bowtie quietly deletes one lobe |
| `dedupe_geoms` | canonical-equality | Same ring, rotated start and reversed — WKB hashing misses it |
| `to_rfc7946` | crs-conformance | EPSG:3857 input must be reprojected; no `crs` member |
| `project_line` | discretization | Densify *before* reprojecting, or the midpoint lands hundreds of km off |
| `wkt_from_latlon` | axis-order | The API gives `lat, lon`; WKT is `x y` |
| `segment_intersection` | collinearity | Collinear overlap must return a segment, not `None` |
| `geohash_neighbors` | discretization | Cells across the equator share no prefix |
| `split_antimeridian` | antimeridian | Two parts, area preserved, neither spanning 358° |
| `zonal_mean` | nodata | Pixel-centre rule plus the sentinel excluded |

Inspect any of them:

```bash
python -c "
from geocase.benchmark.registry import get_task
t = get_task('zonal_mean')
print(t.signature)
print(t.prompt_template)
"
```

Each task is a directory under `src/geocase/benchmark/tasks/<name>/` holding
`task.yaml` (metadata and declared checks), `prompt.md` (the neutral prompt),
and `grader.py` (the oracle).

---

## Running models: the two tracks

### Bare track — automated, needs an OpenRouter key

One single-shot completion per task. No tools, no self-verification loop. It
runs on every model and is maximally comparable.

```bash
export OPENROUTER_API_KEY=sk-or-v1-...
```

Export it in your shell — never put a key in a config file in this repository.
The runner reads it from the environment only, refuses to start without it, and
never logs it.

Always plan the run first. `--dry-run` makes no network calls:

```bash
python -m geocase.benchmark run --config configs/models-free.yaml --dry-run
```

```text
track=bare: 1 models x 1 trials x 20 tasks = 20 API calls; budget ceiling $0.00
```

Then run it:

```bash
python -m geocase.benchmark run --config configs/models-free.yaml --out results/runs
```

Results land in `results/runs/<date>_<model>_bare/generated/trial1/`: the raw
reply, the extracted module, a `.meta.json` per task with cost and the prompt
hash, and `graded.json` with the verdicts.

**On money.** `configs/models-free.yaml` uses one free model with a
`max_usd_total` of `0.00`, so free calls proceed and the first fraction of a
cent aborts the run. `configs/models.yaml` carries the wider roster with a
`$10.00` ceiling. The ceiling is enforced against the cost OpenRouter reports,
and is your only backstop — set it to what you actually intend to risk.

**On rate limits.** Free models are throttled. A 429 is retried five times with
backoff; if the run still stops, re-run the identical command. `--resume` is on
by default and skips every task that already has a module, so nothing is
re-spent.

**On model ids.** The free tier churns, and a stale id returns 404 at call
time. Ids in the shipped configs were verified on 2026-08-09. Re-check before a
run:

```bash
python -c "
import httpx
free = [m['id'] for m in httpx.get('https://openrouter.ai/api/v1/models').json()['data']
        if m['id'].endswith(':free')]
print('\n'.join(sorted(free)))
"
```

### Agentic track — manual, needs no API key

This is the condition that produced the original finding, and the one worth
caring about: the agent gets a sandbox, runs its own code, verifies its own
work, and *still* ships a plausible wrong answer. It runs on a coding-agent CLI
you already have — Claude Code, Cursor, Codex — with no API key at all.

**1. Prepare the workdir.** This builds the sandbox venv, `generated/`, the
per-task scratch directories, and renders all twenty prompts with *that
directory's* absolute paths:

```bash
python -m geocase.benchmark manual prepare --out ~/agentlab --seed 42
```

It prints the shuffled session order to work through. Building the venv takes a
few minutes; add `--no-venv` to skip it, but then the agent cannot run its own
code — which defeats the point of this track, since self-verification is
exactly what the silent failures have to survive.

**2. Run one fresh agent session per task**, in the printed order. For each:

- open a **new** session with the working directory set to `~/agentlab`,
- give it no repository access and no other context,
- paste `~/agentlab/prompts/<task>.md` verbatim — nothing added, nothing removed,
- let it run to `DONE`, then close the session.

One task per session. The isolation is the experiment: an agent that can see
this repository, or that has been told a trap exists, is measuring nothing.

**3. Ingest and grade:**

```bash
python -m geocase.benchmark manual ingest --dir ~/agentlab \
  --model-id anthropic/claude-fable-5 --label "Claude Code (Fable 5)" \
  --protocol claude-code --trial 1 --out results/runs
```

```text
ingested trial 1 into results/runs/2026-08-09_anthropic-claude-fable-5_agentic-manual
  17 CORRECT, 2 SILENT, 1 LOUD, 0 MISSING of 20 — silent-failure rate 10%
```

This writes a schema v2 `run.json` holding every check result, the module
hashes, the prompt hashes carried over from `prepare`, and the pinned sandbox
requirements hash.

**For k=3**, repeat with a fresh workdir per round and `--trial 2`, `--trial 3`
against the same `--out`. Trials accumulate in one record, so a task's three
verdicts sit side by side — which is what separates a reproducible defect from
an unlucky sample. `--protocol` is fixed per run: mixing `claude-code` and
`cursor` results into one record is refused rather than silently blurred.

---

## Rules that keep the numbers honest

These are not style preferences; violating any one of them invalidates a run.

**The oracle is the thing that can lie.** A wrong oracle mislabels every model
— precisely the failure this project is named after, turned on itself. Every
oracle is computed from first principles (`pyproj.Geod`, the Web Mercator
formulas, geohash bit interleaving), never from the fixture corpus. And every
new task's oracle is itself regression-tested against a known-good
implementation (must grade `CORRECT`) and a deliberately trapped one (must
grade `SILENT` on the edge check):

```bash
python -m pytest tests/benchmark/test_oracles.py -q
```

**A leaked hint invalidates a run.** Prompts must never name the trap or hint
that an edge case exists. Every prompt is hashed per run so an edit is
auditable after the fact.

**Spec ambiguity is not a finding.** If a task fails because the contract was
vague, the benchmark has measured its own prompt. Each prompt pins the contract
tightly enough that "correct" is decidable — `zonal_mean` states the
pixel-centre rule, `segment_intersection` states that an overlap is returned as
a segment.

**Model-generated code is untrusted input.** It runs only in a subprocess, in a
dedicated venv, under timeout, with `*_KEY` and `*_TOKEN` scrubbed from the
environment. This is *soft* isolation — for stronger guarantees, run the
grading step inside `docker run --network none`.

**Single-family evidence is the standing weakness.** The only complete run so
far is one Claude model, the same family that authored both GeoCase and this
harness. Until several models across both tracks have run, every number carries
that caveat.

---

## Verifying the harness itself

```bash
python -m pytest tests/benchmark -q
```

This covers the oracle self-tests, the registry contracts (every `task.yaml`
validates, and declared checks exactly match what each grader emits), and the
port pin — which re-grades the committed modules from the original experiment
and asserts the statuses still match, including the `buffer_m` silent failure.
Drift in either direction means the artifacts or the oracles changed, and the
published numbers must be regenerated deliberately.

---

## Adding a task

1. Create `src/geocase/benchmark/tasks/<name>/`.
2. Write `task.yaml` — `schema_version: 1`, the signature, a `trap_category`
   from the controlled vocabulary in `taxonomy.py`, and the declared `checks`
   with their `control`/`edge` kinds.
3. Write `prompt.md` using the `{workdir}`, `{python}`, `{module_path}` and
   `{scratch_dir}` placeholders. Pin the contract; never mention the trap.
4. Write `grader.py` exporting `build_checks(f)`, returning
   `(name, kind, callable)` triples. Each callable returns `(ok, detail)`;
   raising is `LOUD`, returning `False` is `SILENT`.
5. Add a known-good and a known-trapped implementation to
   `tests/benchmark/test_oracles.py`. This is mandatory — an oracle with no
   regression net is not defensible.

The registry test enforces that declared checks match emitted ones, so a
`task.yaml` that drifts from its grader fails CI.
