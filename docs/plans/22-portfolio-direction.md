# Plan 22 — Portfolio direction

> **Status: recorded 2026-08-16.** This is not a construction plan and it authorises no new
> building. It records where the five projects actually stand, what four rounds of external
> evidence say about them, and the one sequencing change that follows. It does not supersede
> [Plan 20](20-restart-spec-first.md) or [Plan 21](21-adoption-action-plan.md); Plan 21's
> Tracks A and B remain the open work inside this repo.
>
> The doc is deliberately aware of its own irony: its central finding is that this project
> writes plans in place of decisions. It is filed as a plan because that is where
> forward-looking documents live here, not because a twenty-second plan was needed.

## What triggered this

A fourth external evaluation, of the same Sentinel-2 / Prithvi codebase that
[Plan 20](20-restart-spec-first.md) classified as the **adopter**, re-run now that `geofacts`
exists as a shippable artifact rather than a design.

**Most of it is not new, and one part is stale.** Its headline finding — no offset or
harmonization handling in the loading path, go check the collection — is a question this
project already closed. Plan 20 records that check being run, coming back clean: every scene
was baseline ≥ 04.00, the offset was removed upstream, and Copernicus reprocessing erased the
pre/post-2022 split. The nodata finding is the same one that already carried 3/3 convergence.
On *is the problem real*, the fourth evaluation adds nothing.

**What is new is one sentence, and it matters.** Shown the built package, the adopter — the
strongest column in Plan 20's convergence table, the source of the "make-or-break" quote that
justified the entire scope-guard API — declined to take it as a dependency. Their reasons:

| Their objection | Weight |
|---|---|
| "Vendor it as a single file" | **Not a rejection.** That was already the design (Rejector C asked for it; `geofacts` ships a vendored single file). For a constants package, vendoring *is* adoption. |
| "Alpha, with a sunset date three months out" | **Self-inflicted and fixable.** The README announces the package's own death, and a prospective user cited it as a reason not to adopt. |
| "The value is in the audit, not the runtime" | **Correct, and unanswered.** The package's job completes on first contact. |

Design-stage enthusiasm and artifact-stage rejection are different measurements. The second is
worth more.

## Portfolio ground truth

Measured 2026-08-16, not assumed.

| Project | State | External users |
|---|---|---|
| **geocase** (this repo) | 130 `case.yaml`; the benchmark references 2 of them. ~13k LOC of `examples/`, `scripts/`, `tests/`, `benchmark/` around ~3.6k LOC of library. `1.0.0rc1` live on PyPI. | 0 |
| **geofacts** | v0.1.1, public on GitHub, published to **TestPyPI only** — `pypi.org` returns 404 for both `geofacts` and `geospatial-spec`. 42 tests, zero deps, ruff + mypy strict clean. | 0 |
| **benchmark** (in this repo) | ~4.6k LOC. 10 committed runs, all free/small models, all bare. 14 of 25 probe records still have `named_trap: null`, so no report exists. Frontier run blocked on $20. | 0 |
| **GeoCase_Studies** | 65 questions across 11 topics — 55 `coding`, 6 `sql`, 1 each of `concept`/`debug`/`design`/`data-reading`. ~420 tests, offline, ~5s. Exam and quiz generation working today. | 0 |
| **passify** | FastAPI + Postgres. Auth, sessions, question generation, three graders behind a dispatch table. Geospatial grading columns migrated 2026-08-14. No frontend. | 0 |

The common row is the last one.

## What four gates have said

| Gate | Date | Verdict | Response |
|---|---|---|---|
| [Plan 14](archive/14-reposition-as-correctness-library.md) Step 0 | 2026-08-09 | **Stop** — blind agents 9/10 correct; the function library is redundant | Plan 15 written |
| [Plan 18](18-eo-product-fixtures.md) Phase 0 | 2026-08-12 | **Premise false for frontier models** — −1000 is in their weights | Built on a narrowed claim |
| [Plan 20](20-restart-spec-first.md) Phase 2 | open | **Not run** — 0 of 5 interviews recorded | Plan 21 written to sequence running it |
| Fourth evaluation | 2026-08-16 | **Would not adopt as a dependency** | this document |

The instruments are good — pre-committed decision rules, oracle grading, witness tests that
machine-check every constant against a real granule. That is better epistemic hygiene than
most projects have. But a gate that is not acted on is documentation. Four gates, four
documents, zero users is the pattern this doc exists to name.

## geofacts — the use case, honestly bounded

Finish publishing it. Not because the market is large; because it is ~95% done, because
**geocase cannot be installed until it is on real PyPI**, and because it is the artifact to
point at if this becomes a write-up rather than a product.

What it is actually for, strongest first:

1. **The runtime guard.** Not the constant — the refusal. `assert_nodata_declared(...)` in a
   production loader turns a silent wrong number into a crash. A dict lookup cannot refuse.
   This is Rejector C's *"constants that only live in tests can't catch a bug in code that has
   no tests"*, and the fourth evaluation is the proof: a `== 0` nodata heuristic that does not
   fail, it quietly changes meaning across the cutover and smears fill through a bilinear
   resample.
2. **The witness mechanism.** Constants machine-checked in CI against a vendored real
   `MTD_MSIL2A.xml` at baseline 04.00 and an S1 GRD annotation. Rejector B called this the only
   genuinely novel property in the project. It generalizes beyond ESA.
3. **The constants table.** Weakest, already downgraded by Plan 20. Lead with nodata, not with
   the offset.

The user is someone writing or auditing EO loading code *before* the nodata and baseline
decisions are made. The value is front-loaded into first contact. That is a real use case and
a small one.

### Blockers, both mechanical

- **TestPyPI is not PyPI.** `pip install geofacts` against the default index fails today.
- **The rename never propagated.** `pyproject.toml` still requires `geospatial-spec>=0.1.0`,
  and `src/geocase/raster/presets/sentinel1.py` and
  `src/geocase/raster/presets/sentinel2.py` still import
  `geospatial_spec`, which the 0.1.1 wheel no longer ships. Importing
  `geocase.raster.presets` on `spec_gaurd` raises `ModuleNotFoundError` right now.

## The finding: two repos are one product

> **Corrected 2026-08-16 by [Plan 23](23-studies-passify-gap-audit.md).** The section below was
> written from the two schemas. Running both test suites shows the framing holds for about a
> seventh of the bank and fails for the rest: passify's content contract has no `coding` type,
> and 55 of Studies' 65 questions are `coding`. The gap table further down understates the work.
> Read Plan 23 before acting on it.

`GeoCase_Studies` and `passify` are not two projects. They are the content half and the
serving half of a geospatial technical-interview platform, built four months apart without
being connected:

- **GeoCase_Studies** — the question bank, every coding answer runnable and pytest-covered,
  each question carrying `Probing`, `Follow-ups` and `Signals` (green/red) sections.
- **passify** — auth, sessions, persistence, and a grader dispatch table whose own docstring
  names the missing fourth entry: *"executable Python against real imagery."*
- **benchmark** — oracle grading over free-text answers, already solved.
- **geofacts** — machine-checked ground truth to grade against.

Unlike everything else in the portfolio, this one has a user who already exists and needs no
interview to find: **the author, currently preparing for geospatial interviews.** Every other
project needed five conversations to discover whether a user existed.

### The exam path already ships

```bash
make exam LEVEL=mid TOPIC=raster MINUTES=60
make quiz TOPIC=fundamentals LEVEL=junior
```

`handbook/exam.py` fills a *time budget* rather than a fixed count, spreads picks across topics
so a 60-minute raster exam is not six variations on `rasterio.mask`, and is deterministic per
seed. **For user #1 the gap is zero.** Everything below is for user #2.

### The gap to passify

The schemas line up almost exactly:

| GeoCase_Studies | passify `questions` | Work |
|---|---|---|
| `topic` (11 dirs) | `topic_id` FK | seed 11 rows |
| `level` (junior…staff) | `difficulty` (already `String`) | direct |
| `## Question` | `text` | direct |
| `## Solution` / `## Model answer` | `ideal_answer` | direct |
| `## Signals` (green/red) | — | **the win; nothing consumes it yet** |
| `type` (6 values) | `type` (3 graders) | mapping + one new grader |

Four gaps, sized:

1. **The importer** — ~half a day. `handbook.loader.load_bank()` → upsert rows.
2. **Signals into the AI grader** — ~20 lines, highest value per line in the plan. Every
   question already carries a hand-written rubric; `grade_prose_ai` currently passes only
   `ideal_answer`. This is the difference between a generic LLM judge and one that knows what
   the question tests.
3. **The code grader — the real work.** 55 of 65 questions are `coding`; the three existing
   graders cover about 9 of 65. So a prose-and-SQL-first MVP unlocks 14% of the bank. The
   grader should not be an LLM: each coding question already has a pytest file validating the
   reference solution, so grading is *run the submission against that file* — deterministic,
   free, correct. `GRADERS` is a dispatch table with the slot documented and empty.
4. **Sandboxing, and no frontend.** Running arbitrary user Python is the risk (`sql_sandbox.py`
   is the precedent). passify is API-only.

## Recommended sequence

| When | Action | Cost |
|---|---|---|
| Now | Sit a generated exam, closed-book, timed | 90 minutes, no code |
| Now, parallel | Promote `geofacts` TestPyPI → PyPI; fix the three stale `geospatial_spec` references | 1 day |
| Now, parallel | Plan 21 Track B — the five interviews | not delegable |
| Only if the exam is useful | Importer → Signals-into-grader → pytest-backed code grader | ~1 week |
| Not yet | Frontend, new questions, Plan 21 Tracks C and D | — |

The ordering principle: for the first time in this portfolio, build **after** using the thing
rather than before. Ninety minutes of sitting the exam settles more than another month of
construction — including whether 65 questions is enough, which for a product it probably is
not, and for one person's preparation plainly is.

## What this document does not authorise

New cases, new questions, a frontend, the README rewrite and docs site of
[Plan 21](21-adoption-action-plan.md) Tracks C and D (polish on a surface Plan 20 may delete),
[Plan 20](20-restart-spec-first.md) Phases 4–5, and any claim of adoption anywhere — including
on a résumé. Zero external users is the measured state of all five projects.
