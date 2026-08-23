---
description: Index of GeoCase's active plans — one scoped document per deliverable, with the single roadmap that sequences them and an archive of superseded plans.
---

# Plans

This folder holds GeoCase's forward-looking documents: what is planned, and in what order.
Nothing here describes how the project works today — that lives in
[`docs/contributing/`](../contributing/workflow.md) and
[`docs/reference/`](../reference/codebase-summary.md).

| Plan | Status | What it covers |
|---|---|---|
| [Roadmap](development-plan.md) | **Active — the single roadmap** | Where the project stands, the active sequence, the open user actions blocking it, and a decision log covering every archived plan. |
| [Throughput, Automation & Corpus-as-Input](17-throughput-automation-and-corpus-as-input.md) | Proposed | Makes the benchmark runnable: fixes the free-tier 429 handling that capped the 2026-08-11 probe sweep at 25/160 completions, adds `sweep`/`status` commands and a `run.json` integrity flag so rate-limit damage stops reading as model results, and opens a corpus-as-*input* seam (2 new tasks). |
| [EO Product Fixtures](18-eo-product-fixtures.md) | Proposed, gated; absorbed by [Plan 20](20-restart-spec-first.md) | Revisits Plan 14's "the input is the cheap part" premise, which was argued on vector only. For EO products (S2 L2A, S1 GRD) the fixture *is* the expensive part. Proposed the generator that shipped as `geocase.raster` (then named `geocase.synth`), with committed outputs as the corpus. |
| [Restart, Spec-First](20-restart-spec-first.md) | **Proposed — overarching** | Acts on three independent external evaluations (one adopter, two rejectors). Splits the project: ship the constants **as scope-guard functions** in a new zero-dependency repo, `geofacts` (formerly `geospatial-spec`); gate the fixture generator on five interviews and rebuild it around a metadata-adversarial primitive with spec-accurate products as presets; demote the benchmark from product to instrument; delete the catalog-as-product surface Plan 14 rejected. Carries a pre-committed 90-day stop condition. |
| [Adoption Action Plan](21-adoption-action-plan.md) | Proposed; Track A subsumed by [Plan 25](25-ship-geocase-as-a-package.md) | Sequences [Plan 20](20-restart-spec-first.md)'s open user actions against the measured release blockers. Release readiness is not the blocker; the funnel around it is. Five tracks, of which A (publish `geofacts`, formerly `geospatial-spec`) is the critical path — geocase declares a runtime dependency that is not yet installable from PyPI. |
| [Portfolio Direction](22-portfolio-direction.md) | **Recorded 2026-08-16 — authorises no building** | Records where all five projects stand after a fourth external evaluation, names the four-gates-four-documents-zero-users pattern, bounds what `geofacts` is actually for, and identifies that `GeoCase_Studies` and `passify` are the content and serving halves of one product with a user who already exists. Sequencing only. |
| [Studies/passify Gap Audit](23-studies-passify-gap-audit.md) | **Measured 2026-08-16** | What is missing from the two sibling repos, run rather than read: passify is 191/14 green with all 14 failures being an empty question bank it has a machine-checkable spec for; GeoCase_Studies is 554-green but 65 questions against a 120–200 target. Corrects [Plan 22](22-portfolio-direction.md) — the two repos' type and topic vocabularies do not agree. |
| [Catalog Site on an Owned Domain](24-catalog-site-on-owned-domain.md) | **Proposed 2026-08-17 — blocked on the domain** | Publishes the catalog site that is already built and never deployed: 188 generated pages with `Dataset` JSON-LD, rendered as Astro on a domain you own. Amends [Website Plan](archive/website-plan.md), reversing its Astro rejection and domain deferral. Carries a pre-committed 90-day Search Console gate. |
| [Ship GeoCase as a Package](25-ship-geocase-as-a-package.md) | **Proposed 2026-08-23 — blocked on `geofacts` reaching PyPI** | Executes the upload the library has been ready for since Plan 11. Confirms [Plan 21](21-adoption-action-plan.md)'s track A by measurement: `geofacts` is a hard runtime dependency that resolves only from a sibling checkout, so it must reach PyPI first. Rehearses on TestPyPI as `1.0.0rc2` rather than spending the immutable `1.0.0`. Adds the two non-packaging steps with real adoption leverage: a README that leads with a failure, and validation against a real library's test suite. |
| [Docs Truth Pass & SEO Prep](26-docs-truth-pass-and-seo-prep.md) | **Implemented 2026-08-23** | Closed the gap between what the docs claimed and what the code does: a stale 134-case count that was an executable assertion in `recipe/meta.yaml`, install instructions for packages that do not resolve, and two completed renames (`geospatial-spec` → `geofacts`, `geocase.synth` → `geocase.raster`) never propagated into the case metadata that generates the published pages. Archived nine done/rejected/superseded plans and replaced the stale roadmap. Laid SEO groundwork **host-neutrally** — per [Plan 24](24-catalog-site-on-owned-domain.md) the canonical URL stays undecided — of which the load-bearing item was rendering the 119 `notes.md` files that no page showed. |
| [Archived plans](archive/index.md) | Superseded | Plans 01–19 and the pre-v1.0 sequencing documents, retained as an implementation log. |

## Rules for this folder

- **One roadmap.** Only [`development-plan.md`](development-plan.md) says "what's next".
  Everything else here is a scoped plan for a single deliverable. Four competing
  "what's next" documents is what forced the July 2026 collapse.
- **Supersede, don't delete.** When a plan is finished or replaced, move it to
  [`archive/`](archive/index.md) with a status banner, and record the outcome in the
  roadmap's Decision log.
- **Active plans are in the nav.** Only `archive/*` is excluded via `not_in_nav`.
