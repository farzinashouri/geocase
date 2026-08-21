# Plans

This folder holds GeoCase's forward-looking documents: what is planned, and in what order.
Nothing here describes how the project works today — that lives in
[`docs/contributing/`](../contributing/workflow.md) and
[`docs/reference/`](../reference/codebase-summary.md).

| Plan | Status | What it covers |
|---|---|---|
| [Development Plan](development-plan.md) | **Active — the single roadmap** | Scope: what each step to v1.0 contains. |
| [Execution Order](execution-order.md) | Active | Order: batching, checkpoints, hard constraints. Scope disputes are settled by the roadmap. |
| [Dataset Catalog Plan](dataset-catalog-plan.md) | Approved, scheduled | The dataset catalog and geographic coverage deliverable. |
| [Website Plan](website-plan.md) | Proposed, unscheduled | The public website. |
| [Distribution — PyPI & conda](11-distribution-pypi-and-conda.md) | Proposed | Packaging and release to PyPI, then conda-forge. |
| [Docs Site Publication](12-docs-site-publication.md) | Proposed | Publishing the built docs to GitHub Pages, and the canonical-URL fix that goes with it. |
| [Cross-Format Canonical Convergence](13-cross-format-canonical-convergence.md) | Proposed | Corpus defect: `*_baseline` families do not hold the geometry they promise. Derive them from their declared canonical and gate it in CI. |
| [Reposition as a Correctness Library](14-reposition-as-correctness-library.md) | **Rejected — Step 0 gate fired (2026-08-09)** | Blind agents got 9/10 operations right; only `buffer_m` across the antimeridian failed, silently, in 2/2 trials. Per the pre-committed decision rule the library is redundant. Evidence: `tests/benchmark/agent_baseline/RESULTS.md`. Salvage path executed by [Plan 15](15-geocase-as-benchmark.md). |
| [GeoCase as a Benchmark](15-geocase-as-benchmark.md) | Proposed | Promotes Plan 14's Step 0 instrument to the product: a benchmark measuring silent failures in LLM-generated geospatial code across free and paid models, on a bare and an agentic track, with a leaderboard published to GitHub Pages. Full repo pivot in two stages. |
| [Generalize Beyond Geospatial](16-generalize-beyond-geospatial.md) | **Phases 0–4 built (2026-08-10)** | Extends Plan 15: makes the benchmark about *coding* rather than *geospatial coding*, with GIS as the first and deepest domain. Adds a per-task `domain`, a second task domain, and a contamination probe that measures whether models already know each trap. Mechanism, `stdlib` slate, oracles, run path and docs are in; the probe run (U7), the `stdlib` model run (U9) and the distribution rename (U10) are pending. |
| [Throughput, Automation & Corpus-as-Input](17-throughput-automation-and-corpus-as-input.md) | Proposed | Makes the benchmark runnable: fixes the free-tier 429 handling that capped the 2026-08-11 probe sweep at 25/160 completions, adds `sweep`/`status` commands and a `run.json` integrity flag so rate-limit damage stops reading as model results, and opens a corpus-as-*input* seam (2 new tasks) that leaves Plan 15's trap 2 intact. |
| [EO Product Fixtures](18-eo-product-fixtures.md) | Proposed, gated | Revisits Plan 14's "the input is the cheap part" premise, which was argued on vector only. For EO products (S2 L2A, S1 GRD) the fixture *is* the expensive part, and product specs are the one category Plan 14 conceded survives the agentic objection — *facts a model cannot have*. Proposes a `geocase.synth` generator with committed outputs as the corpus, gated on one benchmark task measuring whether models emit spec-accurate fixtures. Notes that the seven bundled product fixtures currently carry almost no product fidelity. |
| [Spec Table as a Separate Package](19-spec-table-separate-repo.md) | **Superseded by [Plan 20](20-restart-spec-first.md)** | Proposed a zero-dependency `geospatial-spec` package holding the constants table. The separate-distribution argument is correct and carried forward; the API shape is not — its public `SpecFact.value` is the bare dereferenceable constant the one confirmed adopter calls make-or-break to prevent, and its stated audience (AI agents writing tests) is contradicted by all three evaluations, which ask for a *runtime* guard. |
| [Restart, Spec-First](20-restart-spec-first.md) | **Proposed — overarching** | Acts on three independent external evaluations (one adopter, two rejectors). Splits the project: ship the constants **as scope-guard functions** in a new zero-dependency repo (3/3 evidence); gate the fixture generator on five interviews and rebuild it around a metadata-adversarial primitive with spec-accurate products as presets; demote the benchmark from product to instrument with three tasks left; delete the catalog-as-product surface Plan 14 rejected in 2026-08. Carries a pre-committed 90-day stop condition. |
| [Adoption Action Plan](21-adoption-action-plan.md) | Proposed | Sequences [Plan 20](20-restart-spec-first.md)'s open user actions against the measured release blockers. Release readiness is not the blocker; the funnel around it is. Five tracks, of which A (publish the spec package) is the critical path — geocase declares a runtime dependency that is not yet installable from PyPI. |
| [Portfolio Direction](22-portfolio-direction.md) | **Recorded 2026-08-16 — authorises no building** | Records where all five projects stand after a fourth external evaluation, names the four-gates-four-documents-zero-users pattern, bounds what `geofacts` is actually for, and identifies that `GeoCase_Studies` and `passify` are the content and serving halves of one product with a user who already exists. Sequencing only. |
| [Studies/passify Gap Audit](23-studies-passify-gap-audit.md) | **Measured 2026-08-16** | What is missing from the two sibling repos, run rather than read: passify is 191/14 green with all 14 failures being an empty question bank it has a machine-checkable spec for; GeoCase_Studies is 554-green but 65 questions against a 120–200 target. Corrects [Plan 22](22-portfolio-direction.md) — the two repos' type and topic vocabularies do not agree, and passify's contract has no `coding` type, so 0 of 65 questions import today. |
| [Catalog Site on an Owned Domain](24-catalog-site-on-owned-domain.md) | **Proposed 2026-08-17** | Publishes the catalog site that is already built and never deployed: 188 generated pages with `Dataset` JSON-LD, rendered as Astro on a domain you own. Amends [Website Plan](website-plan.md), reversing its Astro rejection and domain deferral. Renders the 12,176 words of `notes.md` prose no page currently shows, and carries a pre-committed 90-day Search Console gate. |
| [Archived plans](archive/index.md) | Superseded | Plans 01–10, retained as an implementation log. |

## Rules for this folder

- **One roadmap.** Only [`development-plan.md`](development-plan.md) says "what's next".
  Everything else here is a scoped plan for a single deliverable. Four competing
  "what's next" documents is what forced the July 2026 collapse.
- **Supersede, don't delete.** When a plan is finished or replaced, move it to
  [`archive/`](archive/index.md) with a status banner, and record the outcome in the
  roadmap's Decision log.
- **Active plans are in the nav.** Only `archive/*` is excluded via `not_in_nav`.
