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
| [Archived plans](archive/index.md) | Superseded | Plans 01–10, retained as an implementation log. |

## Rules for this folder

- **One roadmap.** Only [`development-plan.md`](development-plan.md) says "what's next".
  Everything else here is a scoped plan for a single deliverable. Four competing
  "what's next" documents is what forced the July 2026 collapse.
- **Supersede, don't delete.** When a plan is finished or replaced, move it to
  [`archive/`](archive/index.md) with a status banner, and record the outcome in the
  roadmap's Decision log.
- **Active plans are in the nav.** Only `archive/*` is excluded via `not_in_nav`.
