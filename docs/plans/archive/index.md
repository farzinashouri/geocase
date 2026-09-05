# Archived plans

These are superseded planning documents, retained as an **implementation log** rather
than as guidance. They record what was decided and why at the time, which is worth
keeping — plans 04 and 08 in particular contain real history.

**Do not treat anything here as current.** The single active roadmap is
[`docs/plans/development-plan.md`](../development-plan.md).
Plans 01–10 were collapsed into it in July 2026, because four competing "what's
next" documents using five different sequencing vocabularies had started producing
contradictory and mislabeled work. Plans 11–19 and the two named plans below were
archived on 2026-08-23 for the ordinary reasons — done, rejected, or superseded — each
with a status banner and a line in the roadmap's Decision log.

| Plan | Status | What it was |
|---|---|---|
| [01 — Actionable Next Steps](01-actionable-next-steps.md) | Superseded | Alpha-to-release checklist; items re-scoped by the v1.0 strategy. |
| [02 — Documentation Consolidation](02-documentation-consolidation.md) | Complete | The docs restructure that produced the current layout. |
| [03 — Consolidation Roadmap](03-consolidation-roadmap.md) | Superseded | First v1.0 scoping. Its Phase 4 open item is resolved in the Decision log. |
| [04 — Phase 2 Vector Edge Cases](04-phase-2-vector-edge-cases.md) | Complete | The vector edge-case corpus. |
| [05 — Format & Geometry Compliance Gate](05-format-geometry-compliance-gate.md) | Complete | Shipped as `tests/unit/test_format_compliance.py`. |
| [06 — Manifest Support](06-manifest-support.md) | Complete | Manifest models and parsing. Registry wiring is Step 14 of the roadmap. |
| [07 — Raster Coverage Plan](07-raster-coverage-plan.md) | Superseded | Raster strategy, executed by plan 08. |
| [08 — Raster Action Plan](08-raster-action-plan.md) | Complete | Raster fixtures, generators, and checksum tooling. |
| [09 — Storage, API/CLI, and v1.0 Release](09-storage-api-cli-and-v1-release-plan.md) | Withdrawn | Its storage and CLI workstreams were deferred and withdrawn. |
| [10 — v1.0 Release Strategy](10-v1-release-strategy.md) | Folded into the roadmap | The detailed rationale and measured evidence behind Steps 11–16. |
| [11 — Distribution (PyPI & conda)](11-distribution-pypi-and-conda.md) | Superseded | Packaging and release to PyPI, then conda-forge. Superseded by [Plan 25](../25-ship-geocase-as-a-package.md). |
| [12 — Docs Site Publication](12-docs-site-publication.md) | **Reversed** | Publishing the built docs to GitHub Pages. Reversed by [Plan 24](../24-catalog-site-on-owned-domain.md): Pages is now explicitly ruled out, because Dataset Search dedupes on the JSON-LD `url` and would likely credit `github.io` as canonical. |
| [13 — Cross-Format Canonical Convergence](13-cross-format-canonical-convergence.md) | Complete | Derived all 60 `*_baseline` fixtures from their declared canonical and gated it in CI. 53 of 60 had shipped the wrong geometry. |
| [15 — A Benchmark Built on the Catalog](15-geocase-as-benchmark.md) | Implemented as an addition | Proposes the benchmark subsystem as an **addition** built on the catalog, shipped beside the library behind a `bench` extra rather than in place of it. Built 2026-08-10. |
| [16 — Generalize Beyond Geospatial](16-generalize-beyond-geospatial.md) | Phases 0–4 built, halted | Made the benchmark about *coding* rather than *geospatial coding*. Halted; its open items U7/U9/U10 are carried in the [roadmap](../development-plan.md). |
| [17 — Throughput, Automation & Corpus-as-Input](17-throughput-automation-and-corpus-as-input.md) | Proposed, not started | Benchmark throughput: 429 handling, `sweep`/`status` commands, a `run.json` integrity flag, and a corpus-as-*input* seam. Survives intact but is off the critical path — the benchmark is an instrument rather than the product, so this became tooling for an instrument nobody is blocked on. |
| [18 — EO Product Fixtures](18-eo-product-fixtures.md) | Phases 0–1 implemented; **premise refuted** | Argued the fixture is the expensive part for EO products (S2 L2A, S1 GRD). Its own Phase 0 gate refuted the premise for frontier models 2026-08-12 — the −1000 BOA offset is in their weights. The generator it proposed did ship, as `geocase.raster` (then `geocase.synth`). |
| [19 — Spec Table as a Separate Package](19-spec-table-separate-repo.md) | Superseded | Proposed the zero-dependency constants package that became `geofacts`. The distribution argument carried forward; the API shape did not. |
| [23 — Studies/passify Gap Audit](23-studies-passify-gap-audit.md) | **Measured 2026-08-16 — a completed measurement** | What was missing from the two sibling repos, run rather than read: passify 191/14 green with all 14 failures an empty question bank; `GeoCase_Studies` 554-green but 65 questions against a 120–200 target. Archived because it is a finished audit, not open work — its correction to the earlier portfolio framing (the two repos' type and topic vocabularies disagree) is recorded in the audit itself. |
| [Dataset Catalog Plan](dataset-catalog-plan.md) | Complete | Shipped as [`docs/dataset-catalog.md`](../../dataset-catalog.md). |
| [Website Plan](website-plan.md) | Amended and superseded | The public website. [Plan 24](../24-catalog-site-on-owned-domain.md) reverses its Astro rejection and domain deferral. |
| [Execution Order](execution-order.md) | Complete | The v1.0 batching and checkpoint sequence. Batches 1–5 shipped "to the upload boundary"; folded into the roadmap so there is one sequencing document. |
