# Plan 23 — What is missing from `passify` and `GeoCase_Studies`

> **Status: audited 2026-08-16.** A measurement, not a plan. Everything below was run or read
> in the two working trees on that date; no gap is inferred from a README.
>
> It **corrects [Plan 22](22-portfolio-direction.md)** on one material point. Plan 22 called the
> two repos "the content half and the serving half of one product." A closer reading of
> passify's own content contract shows that is true for about a seventh of the question bank
> and false for the rest. See [The disagreement](#the-disagreement).

## Method

| Repo | Command | Result |
|---|---|---|
| `GeoCase_Studies` | `pytest -p no:warnings` | **554 passed, 61 skipped** (skips are the PostGIS questions, no `DATABASE_URL`) |
| `passify` | `passify_venv/bin/python -m pytest -q` | **191 passed, 14 failed** |

Both trees are free of `TODO`, `FIXME` and `NotImplementedError` outside
`scripts/new_question.py`, which is a scaffolder and is supposed to emit them. Neither repo is
rotting. What is missing is missing by design, and in passify's case it is missing *on purpose
and in writing*.

## passify — one thing is missing, and it is the product

`docs/plans/geospatial-interview-repoint.md` carries a self-maintained status table, last
updated 2026-08-15 on branch `repoint`. Reproduced here because it is more honest than anything
an outside audit would produce:

| Phase | Status |
|---|---|
| 1 — Security & honesty pass | **done**, except credential rotation, which is manual and outside the repo |
| 2.1 Question types, 2.2 Schema, 2.4 SQL grading, 2.5 Wiring, 2.6 AI spend caps | **done** |
| **2.3 Curated exercise bank** | **todo — format, validator and seed script exist; zero questions written** |
| 3.1 Open bank / progress accounts | todo |
| 3.2 Deploy | todo |
| 3.3 Website integration | todo |
| 3.4 Open source | partial — CI added, repo not yet public |
| 3.5 Distribution | todo |
| 4 — Executable Python + imagery | todo, explicitly gated on Phase 3 being live |

**All 14 test failures are the same failure**: `no YAML files under content/questions`.
`content/questions/` and `content/datasets/` contain a `README.md` each and nothing else.

This is the good kind of missing. `tests/test_question_bank.py` is a **failing spec** — it
states the content contract precisely enough that an importer can be written against it without
a further design step:

```
content/questions/<topic>.yaml   — a YAML list of entries:

  text:            str                    # unique across the bank (DB UNIQUE constraint)
  type:            theory | sql | numeric
  difficulty:      easy | medium | hard
  topic:           str                    # must match Topic.name
  interview:       bool                   # required; strict minority of the bank
  ideal_answer:    str                    # required for theory
  expected_result: list[list] | {value, tolerance, unit}   # sql | numeric
  grading_spec:    dict                   # optional, sql only
  dataset_key:     str                    # required for sql; must resolve to a pinned fixture
```

Four of the fourteen failures are aggregate targets that are *supposed* to stay red while the
bank is drafted: 120–200 questions, all eight topics present, and **≥30% of the bank graded
deterministically** (`sql` or `numeric`) — the test's own words: *"a bank that is 95% prose is
the generic app with geospatial words in it."*

### passify's other real gaps

- **No frontend.** Eleven endpoints, all JSON. Nothing a person can use without `curl`.
- **No question browsing or history.** `POST /practice/sessions` and `POST /practice/answer`
  exist; there is no `GET` for questions, past sessions, or progress. Phase 3.1's per-question
  attempt counts — the instrumentation the Phase 4 decision depends on — do not exist yet.
- **Session question selection is not a selection.** `create_session` filters by topic and then
  takes `.limit(n)` with no ordering, no difficulty filter, and no exclusion of questions the
  user has already answered. Every session returns the same questions in the same order.
- **Zero sandbox fixtures.** `content/datasets/` is empty, so a `sql` question cannot resolve a
  `dataset_key`, so it cannot carry an `expected_result` generated the way the README requires
  (*"Never hand-write expected rows"*). Executable SQL grading is built and has nothing to run
  against.

## GeoCase_Studies — complete on its own terms, thin in three places

Nothing here is broken. 554 tests pass, the bank validates against its own schema, and
`make exam` / `make quiz` work today. The gaps are of size and distribution:

| Axis | Measured | Note |
|---|---|---|
| Bank size | **65 questions** | passify's contract targets 120–200 |
| Type mix | 55 `coding`, 6 `sql`, 1 each `concept` / `debug` / `design` / `data-reading` | 85% is code |
| Level mix | 12 junior, 37 mid, 15 senior, **1 staff** | mid-heavy; the staff tier is a single question |
| Topic depth | vector 13, fundamentals 11, algorithms 9, raster 7, spatial-sql 6 … **system-design 1, visualization 2, analysis 3, remote-sensing 3** | four topics are stubs |
| Benchmark-ready | 45 of 65 | healthy |
| Trap coverage | 21 traps declared, top ones `units-degrees` 8, `ordering` 5, `nodata` 4 | good spread |

The four thin topics matter more than the headline count: `system-design` has one question, and
`remote-sensing` — the domain closest to `geofacts` and to your actual EO experience — has three.

## The disagreement

This is the finding, and it is why [Plan 22](22-portfolio-direction.md)'s framing was too
optimistic.

The two repos do not agree about what a question *is*:

| | GeoCase_Studies | passify |
|---|---|---|
| Types | `coding`, `sql`, `concept`, `debug`, `design`, `data-reading` | `theory`, `sql`, `numeric` |
| Topics | 11 slugs — fundamentals, vector, raster, remote-sensing, spatial-sql, data-engineering, algorithms, analysis, trajectories, visualization, system-design | 8 slugs — postgis, crs, raster-eo, ogc, tiling-mvt, geometry-topology, spatial-indexing, geospatial-python |
| Seniority | `level` (junior…staff) **and** `difficulty` (1–3) | one `difficulty` (easy/medium/hard) |
| Grading of code | pytest against the reference solution, offline, 2.8s for the suite | **no such type exists** |

Neither topic vocabulary is a subset of the other. Neither type vocabulary is either. And the
decisive one: **passify's content contract has no `coding` type at all.** Its answer to
executable code is Phase 4 — per-submission containers, a job queue, object-storage imagery, run
quotas — which its own plan calls *"the one that can consume the whole project if attempted
early"* and gates behind a live deployment.

So of 65 questions, the number that can be imported under the existing contract is:

- 6 `sql` — but none carries an `expected_result` or a `dataset_key`, and no fixture exists for
  them to be generated against, so **0 are importable today**
- ~4 prose-ish (`concept`, `design`, `data-reading`, arguably `debug`) → `theory`
- 0 `numeric` — Studies has never authored one
- 55 `coding` — **no destination**

Studies' entire strength is the half passify has deferred. Meanwhile the ≥30%-deterministic gate
means a bank of imported prose would fail the contract even if the mapping were done.

## What is actually missing, separated by kind

**Missing content** (weeks, not days — and passify's plan says so: *"the long pole and the real
product"*):

1. 55–135 more questions to reach the 120–200 target.
2. A `numeric` question type in Studies — none exists, and `numeric` plus `sql` is the only way
   to reach the 30% deterministic floor without Phase 4.
3. `expected_result` + `dataset_key` on the 6 `sql` questions.
4. At least one pinned fixture in `content/datasets/` (Natural Earth is the README's own first
   candidate), and the reference queries run against it to generate expected rows.

**Missing code** (days):

5. The importer: `handbook.loader.load_bank()` → `content/questions/<topic>.yaml`.
6. A topic mapping table, or a decision to collapse one vocabulary into the other.
7. A level → difficulty mapping (4 values → 3).
8. `## Signals` fed into `grade_prose_ai`, which currently passes only `ideal_answer`.
9. Real session question selection — ordering, difficulty filter, exclusion of answered questions.
10. `GET` endpoints for questions, sessions and progress.

**Missing decisions** (nothing can be built until these are made):

11. **Whose taxonomy wins.** Eleven Studies topics or eight passify topics.
12. **What happens to the 55 coding questions.** Either passify gains a `python` type — with the
    full sandbox cost its own Phase 4 enumerates — or the coding half stays a CLI product and
    the web app ships prose/SQL/numeric only. These are different products.
13. **Which user is being served.** Studies-as-CLI already serves user #1 today. passify serves
    user #2, and needs Phase 3.2 (deploy) plus a frontend before anyone can touch it.

## Reading

The cheapest coherent thing is not the merge. It is to accept that these are **two products
sharing a domain**:

- `GeoCase_Studies` is a working CLI exam tool with 65 tested questions. It needs no passify.
- `passify` is a working, well-tested, security-hardened practice API with an empty bank. It
  needs ~120 questions of a shape Studies has largely not written, plus a deploy and a UI.

Plan 22's recommendation stands unchanged where it matters — sit a generated exam before
building anything — but the "importer, then Signals, then code grader" sequence it sketched is
premature. Decisions 11–13 come first, and item 12 is a fork in the road, not a task.
