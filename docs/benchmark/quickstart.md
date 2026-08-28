# Benchmark Quick Start

The GeoCase benchmark measures whether LLM coding agents write code that
**silently lies** — code that returns a plausible wrong answer without raising
anything, so the model's own verification cannot see the bug. That is a claim
about *measurement*, not about geospatial: benchmarks that grade against test
suites structurally cannot see this class. Geospatial is the first and deepest
domain, not the boundary of the question.

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
    This documents the Plan 15 *minimum viable one-off* — the task packages,
    the oracles, the grading CLI, and a bare-track OpenRouter runner — plus the
    [Plan 16](https://github.com/farzinashouri/geocase/blob/main/docs/plans/archive/16-generalize-beyond-geospatial.md) domain mechanism. The
    results store, the leaderboard, and the automated agentic track are not
    built yet. The `stdlib` slate has a full harness but **no committed model
    run yet**, and its tasks remain provisional until the contamination probe
    (below) has been reviewed.

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

## Domains

A **domain** is a body of task content sharing one sandbox environment, one
prompt dependency sentence, and one closed trap vocabulary. The instrument
itself — grading, taxonomy, the runner — is domain-agnostic and always was;
only the task content is domain-specific.

| Domain | Tasks | Sandbox | Trap vocabulary |
|---|---|---|---|
| `geo` | 20 | `configs/sandbox-requirements.txt` (shapely, pyproj, rasterio, numpy, scikit-learn) | 13 categories |
| `stdlib` | 6 | `configs/sandbox-requirements-stdlib.txt` (empty — a bare venv) | 6 categories |

A trap category is valid only inside its own domain, so a geo task cannot
declare a numeric trap and vice versa. Most commands take `--domain`; where a
mixed selection would produce a blended number, it is refused outright rather
than printed (see *cross-domain rates are not comparable*, below).

### The selection rules for a new task

Beyond "pin the contract, never name the trap":

- **Reject canonical-pedagogy traps** unless the contamination probe shows
  models fall in anyway. A trap that is the subject of a named algorithm or a
  top Stack Overflow answer measures recall until proven otherwise.
- **Reject ambiguous contracts.** `percentile` is out — nearest-rank and linear
  interpolation are both defensible, so pinning one measures reading
  comprehension rather than correctness.
- **Concurrency is ruled out permanently.** A nondeterministic oracle cannot
  distinguish `SILENT` from noise, and the oracle is the one thing that must
  not lie.

---

## The twenty geo tasks

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

## The six stdlib tasks

`origin: plan16`, all `packages: []`. **Provisional**: each is subject to the
contamination probe below, and a task every probed model names unprompted
measures recall rather than the phenomenon.

| Task | Trap | The edge case |
|---|---|---|
| `dedupe_labels` | normalization | NFC vs NFD `"Ångström"` is one label; `casefold()` alone keeps two |
| `group_means` | null-propagation | An all-null group is `None`, not `0.0` — the `v or 0.0` idiom |
| `allocate_cents` | rounding-residue | `(1000, [1,1,1])` must sum to 1000; independent rounding gives 999 |
| `elapsed_hours` | dst-transition | Local midnight to midnight on 2026-11-01 in New York is 25 hours |
| `sample_variance` | cancellation | `[1e9+1 … 1e9+4]` has variance 1.667; the one-pass form returns `0.0` |
| `parse_delimited` | quoting | `'a,"b,c",d'` is 3 fields; `.split(",")` finds 4 |

`sample_variance` is the closest structural analogue to `buffer_m` anywhere in
numerics: cancellation returns exactly `0.0` for data with obvious spread, and
the natural self-check on small integers is *invariant under the defect* — the
same property that made the agents' geodesic radial check blind. It is also the
most likely to be memorised, which is precisely what the probe is for.

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
python -m geocase.benchmark run --config configs/models-free.yaml --domain geo --dry-run
```

```text
track=bare: 1 models x 1 trials x 20 tasks = 20 API calls; budget ceiling $0.00
```

`--domain` is required once more than one domain exists: a run spanning
domains could only be reported as a blended rate, which is refused. `--tasks`
narrows further and intersects with `--domain`; a filter matching nothing exits
non-zero rather than reporting "0 of 0".

Then run it:

```bash
python -m geocase.benchmark run --config configs/models-free.yaml --domain geo --out results/runs
```

Results land in `results/runs/<date>_<model>_bare/generated/trial1/` — or
`..._bare_<domain>/` for any domain other than `geo`, which keeps its
historical path so the committed runs stay where they are. Each holds: the raw
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
per-task scratch directories, and renders that domain's prompts with *that
directory's* absolute paths:

```bash
python -m geocase.benchmark manual prepare --out ~/agentlab --domain geo --seed 42
```

`--domain` is required and has no default. A workdir holds exactly one venv and
records exactly one `sandbox_requirements_sha256`, so a mixed-domain workdir
would stamp every task with a hash describing an environment wrong for half of
them. For the `stdlib` domain the venv builds in about a second, since its
requirements file installs nothing — which is what makes the prompt's "standard
library only" sentence structurally true rather than merely stated.

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

**Cross-domain rates are not comparable.** Task difficulty is set by the task
author, not by the domain: six hand-picked tasks with hand-picked traps are not
a random sample of anything. A lower silent rate on `stdlib` than on `geo`
would **not** mean "geo is uniquely hard." The per-task matrix is the
information; a blended headline number across domains is noise dressed as a
finding, so the tooling refuses to print one. What a second domain licenses is
narrower and defensible: *the instrument detects silent failures outside
geospatial code.* Say that and no more.

**Contamination is measured, not assumed.** See the next section — and note
that it bites the non-geo domains harder, because their traps are canonical
pedagogy independent of anything this repo publishes.

**Single-family evidence is the standing weakness.** The only complete run so
far is one Claude model, the same family that authored both GeoCase and this
harness. Until several models across both tracks have run, every number carries
that caveat.

---

## Contamination

Contamination inflates pass rates; it does not fabricate silent failures. A
model that has memorised Welford's algorithm and writes it scores `CORRECT`,
and arguably a fair one — knowing the standard algorithm *is* competence.
Memorisation cannot produce a *false* `SILENT`.

The failure mode is subtler: a **measurement-uninformative** result. A domain
scores a near-zero silent rate and nobody can tell whether models are genuinely
good at it or have simply memorised these particular war stories.

`buffer_m` is not in that class, and the agents failed it anyway while actively
self-verifying. The non-geo traps are: "the naive one-pass variance formula
suffers catastrophic cancellation" is in Knuth, and "don't split CSV on commas"
is among the most-repeated advice on Stack Overflow. So it is measured
per-task and per-model rather than caveated in prose:

```bash
python scripts/contamination_probe.py --config configs/models-free.yaml --dry-run
python scripts/contamination_probe.py --config configs/models-free.yaml
```

Each task may carry a `probe.md` — an open question about its contract ("what
are the common pitfalls when implementing X?") with no mention of any edge
case, asked in a session entirely separate from any benchmark run. Replies land
in `results/probes/<date>_<model>.json` with `named_trap` left `null`.

**`named_trap` is set by hand.** String matching cannot do this job: a model can
describe the antimeridian problem without ever using the word. This is the same
discipline as reviewing a new oracle, and it must not be automated.

The probe runs against the geo tasks too, `buffer_m` included, because the
strongest available result is the one where a model **names the trap and falls
into it anyway** while self-verifying. Knowing-but-not-applying is a far more
interesting claim than not-knowing, and it is the claim most resistant to the
objection that the benchmark just tests obscure knowledge.

!!! warning "Parametric variants do not fix this"
    Randomising the offset in `[1e9 + k]` changes nothing — the model either
    reaches for a two-pass or Welford form or it does not, and the specific
    constant is irrelevant. Parametric variants defend against *prompt*
    memorisation, not *concept* memorisation. They are not the mitigation here,
    and nothing on this page should be read as claiming they are.

---

## Verifying the harness itself

```bash
python -m pytest tests/benchmark -q
```

This covers the oracle self-tests, the registry contracts (every `task.yaml`
validates, and declared checks exactly match what each grader emits), the
prompt-hash gate (every committed run's recorded `prompt_sha256` still
reproduces from today's code, so a prompt edit can never happen silently), and
the port pin — which re-grades the committed modules from the original experiment
and asserts the statuses still match, including the `buffer_m` silent failure.
Drift in either direction means the artifacts or the oracles changed, and the
published numbers must be regenerated deliberately.

---

## Adding a task

1. Create `src/geocase/benchmark/tasks/<name>/`.
2. Write `task.yaml` — `schema_version: 1`, the signature, a `trap_category`
   from your domain's vocabulary in `taxonomy.py`, and the declared `checks`
   with their `control`/`edge` kinds. Add `domain:` for anything outside `geo`,
   which is the default. Unknown keys are rejected rather than ignored.
3. Write `prompt.md` using the `{workdir}`, `{python}`, `{module_path}` and
   `{scratch_dir}` placeholders. Pin the contract; never mention the trap.
4. Write `grader.py` exporting `build_checks(f)`, returning
   `(name, kind, callable)` triples. Each callable returns `(ok, detail)`;
   raising is `LOUD`, returning `False` is `SILENT`.
5. Write `probe.md` — the open contamination question. Required outside `geo`.
6. Add a known-good and a known-trapped implementation to
   `tests/benchmark/test_oracles.py`. This is mandatory — an oracle with no
   regression net is not defensible.

The registry test enforces that declared checks match emitted ones, so a
`task.yaml` that drifts from its grader fails CI.

## Adding a domain

Two domains prove the abstraction; a third mostly proves premature
generalisation. The gate is fixed in advance:

> A new domain is added only when every existing domain has ≥3 models × k=3 on
> the bare track, and the newest domain has produced at least one silent failure
> reproducible across trials **on a task the contamination probe did not flag**.

Candidates, in rough order of trap density: money/`Decimal`, text encoding
beyond normalisation, SQL semantics beyond `NULL`, serialisation round-trips,
floating-point accumulation.

Mechanically a domain is one entry in `DOMAINS` (`domains.py`) naming its
requirements file, its prompt dependency sentence, and its trap vocabulary
(`taxonomy.py`), plus a `configs/sandbox-requirements-<name>.txt`.
