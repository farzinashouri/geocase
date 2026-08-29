---
description: The single GeoCase roadmap — where the project stands, what is being built next, which user actions are blocking, and why each archived plan was archived.
---

# Roadmap

**The single roadmap.** Everything else in [`docs/plans/`](index.md) is a scoped plan for one
deliverable. If a scoped plan and this page disagree about what is next, this page wins — four
competing "what's next" documents is what forced the July 2026 roadmap collapse.

*Rewritten 2026-08-23. It previously described the road to v1.0, which shipped on 2026-08-02;
that document is preserved at
[`archive/10-v1-release-strategy.md`](archive/10-v1-release-strategy.md) and in the plans it
collapsed. Sequencing that used to live in `execution-order.md` is folded in below.*

## Where the project stands

| | |
|---|---|
| Version | `1.0.0rc2` in this repository; `1.0.0rc1` is published on [PyPI](https://pypi.org/project/geocase/). |
| Catalog | **135 cases** (vector, raster, NetCDF), 2.1 MB bundled, gated in CI. |
| Gates | `catalog`, `tests` (3.11 + 3.14), `lint`, `typecheck`, `docs` — all green. |
| Docs site | 188 generated pages with `schema.org/Dataset` JSON-LD. GitHub Pages deployment is configured; enable Pages in repository settings to serve it. |
| Users | Zero confirmed adopters. One prospective adopter (S2/Prithvi change detection) identified but not yet asked. |

Four external evaluations — one adopter, three rejectors — have now reported. Plans 22, 23 and
25 measured the result rather than argued it, and the finding is uncomfortable and consistent:

- **The four-gates, four-documents, zero-users pattern.** Every project in the portfolio has
  more CI gates and planning prose than it has users. GeoCase is the furthest along and still
  has none. ([Plan 22](22-portfolio-direction.md))
- **Packaging is not the bottleneck.** The library has been release-ready since Plan 11. The
  one hard blocker was dependency ordering — `geofacts` had to reach PyPI before GeoCase could
  install anywhere — and it **cleared 2026-08-24** with `geofacts 0.1.2` on PyPI. What remains
  is the GeoCase TestPyPI rehearsal itself. ([Plan 25](25-ship-geocase-as-a-package.md))
- **Discovery is the bottleneck.** The catalog is the differentiated asset, and GitHub Pages is
  now its chosen single public URL. Enable the deployment and make the catalog indexable before
  adding further promotional surfaces.
- **The defensible product is the scope guard, not the catalog.** 3 of 3 evaluations named the
  constants-with-scope-guards as the thing worth having; the catalog-as-product framing was
  rejected by [Plan 14](archive/14-reposition-as-correctness-library.md)'s own gate.
  ([Plan 20](20-restart-spec-first.md))

## Active sequence

[Plan 20](20-restart-spec-first.md) is the overarching frame — split the project, ship the
guard, gate the fixture work on interviews, demote the benchmark to an instrument.
[Plan 22](22-portfolio-direction.md) is the portfolio constraint on top of it: GeoCase competes
for attention with `GeoCase_Studies` and `passify`, which have a user who already exists.

Within that frame, in order:

1. **[Plan 25](25-ship-geocase-as-a-package.md) — ship the package.** Publish `geofacts` to
   PyPI first (hard dependency ordering), then rehearse GeoCase on TestPyPI as `1.0.0rc2`
   rather than spending the immutable `1.0.0`. Includes the README rewrite that leads with a
   concrete failing edge case — which is SEO work, not just persuasion work, because the README
   is the one indexable page GeoCase has.
2. **Publish the catalog on GitHub Pages.** The existing MkDocs site is the one canonical public
   home at `https://farzinashouri.github.io/geocase/`; enable GitHub Pages with GitHub Actions
   in repository settings. [Plan 24](24-catalog-site-on-owned-domain.md)'s Astro/Netlify route
   is superseded.
3. **[Plan 21](21-adoption-action-plan.md)'s remaining tracks** — the adoption funnel around
   the release, of which Track A (publish the spec package) is subsumed by Plan 25.
4. **[Plan 26](26-docs-truth-pass-and-seo-prep.md)** — **complete 2026-08-23, except its
   §3.4 `social` plugin**, which is blocked on `libcairo` and tracked in *Deferred work*.
5. **[Plan 27](27-close-plan-26-findings.md)** — closes what Plan 26 surfaced but did not
   predict. Its Phase 1.1 is the only item here with real leverage and is worth doing *before*
   Plan 24 deploys: the README now leads with four failure modes because Plan 24 pre-commits to
   measuring those four, and two of them have no case in the catalog. Ranking for a query the
   catalog cannot answer spends a first impression on a miss.

**Archived 2026-08-24, per [Plan 25](25-ship-geocase-as-a-package.md) §9:**
[Plan 17](archive/17-throughput-automation-and-corpus-as-input.md) (benchmark throughput) and
[Plan 18](archive/18-eo-product-fixtures.md) (EO product fixtures, absorbed by Plan 20) were
both off the critical path, and Plan 18's own gate had already refuted its premise. Keeping
them in the active set implied pending work that nothing is waiting on.
[Plan 23](archive/23-studies-passify-gap-audit.md) moved too — a completed audit, not a plan.
Archived does not mean wrong: Plan 17 in particular survives intact and can be revived if the
benchmark ever needs the throughput.

## Open user actions

Not automatable and not delegable. Each blocks the work named beside it.

| Id | Blocks | Action |
|---|---|---|
| — | [Plan 25](25-ship-geocase-as-a-package.md), step 6 | ~~**Publish `geofacts` to PyPI.**~~ **Done 2026-08-24** — shipped as `0.1.2`; GeoCase's floor is now `>=0.1.2`. Remaining user action: register GeoCase's own pending publishers on test.pypi.org/pypi.org so the `1.0.0rc2` rehearsal can upload. |
| U16 | [Plan 20](20-restart-spec-first.md) Phase 1 | Choose the PyPI name and create the repo. (Largely satisfied by the `geofacts` rename; confirm the name is claimable.) |
| U17 | [Plan 20](20-restart-spec-first.md) Phase 2, and all of Phase 3 bar the nodata carve-out | **Run the five fixture interviews.** 0 of 5 recorded. The whole gate is judgement about what people actually said. Instrument: [`docs/evidence/2026-fixture-interviews/`](../evidence/2026-fixture-interviews/TEMPLATE.md). |
| U18 | Nothing — but it is the cheapest signal available | Send the shipped guard to the S2/Prithvi adopter and ask directly whether it goes in. |
| U19 | [Plan 20](20-restart-spec-first.md) Phase 4 | Spend the $20; run the frontier bare track; spot-check two modules per model. |
| U20 | [Plan 20](20-restart-spec-first.md) Phase 4 | Review the 14 null `named_trap` records. |
| U21 | [Plan 20](20-restart-spec-first.md) Phase 5 | Approve the corpus deletion (~128 unreferenced cases) and the PyPI notice wording. |
| U7 | [Plan 16](archive/16-generalize-beyond-geospatial.md), archived | Run the contamination probe and review its `named_trap` output. Carried here because open items belong in the roadmap, not in an archived plan. |
| U9 | [Plan 16](archive/16-generalize-beyond-geospatial.md), archived | Run the `stdlib` bare track against a model. |
| U10 | [Plan 16](archive/16-generalize-beyond-geospatial.md), archived | The distribution rename that generalizing the benchmark beyond geospatial implies. |

## Deferred work

Named here so it is not lost, and not started:

- **Searcher-facing case descriptions for the remaining 114 cases** — now owned by
  [Plan 27](27-close-plan-26-findings.md) §3, which sizes it: 30 of the 114 exceed the 155-char
  cap and are silently truncated mid-clause in their `<meta name="description">`. Those 30 are a
  defect and are sequenced first; the other 84 are a preference and should be done
  opportunistically rather than as a batch.
- **Open Graph social cards.** `mkdocs.yml` declares an explicit `plugins:` block, but the
  `social` plugin is left out: it needs the native libcairo/libfreetype libraries, absent from
  both the development machine and the CI runner, so enabling it unverified would turn the
  `docs` gate red. Needs an apt step in the `docs` job plus `pillow`/`cairosvg` in the `docs`
  extra. Worth doing when the site is actually about to be served.
- **Remote dataset transport** — deferred from v1.0 to v1.1. Manifests parse and resolve; ids
  are discoverable; the data is not fetched.
- **Coverage gaps in the catalog** — rotated/skewed affine transforms, non-square pixels,
  southern-hemisphere UTM. Enumerated honestly in
  [`docs/dataset-catalog.md`](../dataset-catalog.md). Plan 26 §3.3 surfaced one more — **no
  case declares an `axis_order` or `crs_mismatch` risk type** — which became
  [Plan 27](27-close-plan-26-findings.md) §1.1. **`axis_order` is now closed** by
  [Plan 34](34-close-reviewed-catalog-gaps.md) §4.2: the six GML baselines already carried
  authority-order coordinates on disk and now declare and gate the property. **`crs_mismatch`
  remains owed** and should land before Plan 24 deploys, since the README leads with the term.
- **Gaps assessed and deliberately not closed by [Plan 34](34-close-reviewed-catalog-gaps.md)**,
  from an external expert's review of the catalog — its Phase 5 records each with reasons.
  Two are genuinely deferred rather than declined: **alpha-band-as-nodata**, which needs a v1.1
  break to extend the `NodataConvention` literal, and **curvilinear 2D coordinate grids**, which
  Plan 34's NetCDF generator has now unblocked and which is the natural next NetCDF case.
  **Mixed-timezone datetimes** stay with [Plan 28](28-validate-geocase.md) Phase 3.
- **`ambiguous_zero`'s enforcing check** — registered in [Plan 27](27-close-plan-26-findings.md)
  §1.3 and still owed there. Plan 34 added two rows to that table and did not touch this one.
- **mypy strictness** beyond `geocase.catalog.*` and `geocase.api.*`, ratcheting in v1.1.

## Decision log

One line per archived plan, and why. Full text and status banners in
[`archive/`](archive/index.md).

| Plan | Outcome |
|---|---|
| [Dataset Catalog Plan](archive/dataset-catalog-plan.md) | **Complete.** Shipped as [`docs/dataset-catalog.md`](../dataset-catalog.md) — what the catalog contains, why each format was chosen, the geodetic rationale for every coordinate cluster, and an honest list of gaps. |
| [Website Plan](archive/website-plan.md) | **Amended and superseded** by Plan 24, which reverses its rejection of Astro and its deferral of a domain. |
| [Execution Order](archive/execution-order.md) | **Complete.** Its Batches 1–5 shipped v1.0 "to the upload boundary"; the upload itself is Plan 25. Folded into this page rather than left as a second stale sequencing document. |
| [11 — Distribution (PyPI & conda)](archive/11-distribution-pypi-and-conda.md) | **Superseded** by Plan 25, which executes the same upload with a TestPyPI rehearsal and correct dependency ordering. |
| [12 — Docs Site Publication](archive/12-docs-site-publication.md) | **Reversed** by Plan 24. GitHub Pages is now explicitly ruled out for canonical-URL reasons, not cost reasons. |
| [13 — Cross-Format Canonical Convergence](archive/13-cross-format-canonical-convergence.md) | **Implemented 2026-08-09.** All 60 `*_baseline` fixtures now hold the geometry their `canonical_source_case_id` claims; gated by `generate_vector_fixtures.py --check`. 53 of 60 had been wrong. |
| [14 — Reposition as a Correctness Library](archive/14-reposition-as-correctness-library.md) | **Rejected 2026-08-09** by its own pre-committed Step 0 gate. Ten blind agents got 9/10 operations correct; only `buffer_m` across the antimeridian failed, silently, 2/2. The library would have been redundant. Salvage path executed by Plan 15. |
| [15 — GeoCase as a Benchmark](archive/15-geocase-as-benchmark.md) | **Implemented 2026-08-10** (Phases 1, 3, stripped 4). Superseded as *strategy* by Plan 20, which demotes the benchmark from product to instrument. The instrument remains and is maintained. |
| [16 — Generalize Beyond Geospatial](archive/16-generalize-beyond-geospatial.md) | **Phases 0–4 built 2026-08-10.** Halted where it stands by Plan 20. Its three open user actions are carried in the table above. |
| [19 — Spec Table as a Separate Package](archive/19-spec-table-separate-repo.md) | **Superseded** by Plan 20. The separate-distribution argument was right and carried forward into `geofacts`; the API shape was wrong — its public `SpecFact.value` is exactly the bare dereferenceable constant the one confirmed adopter calls make-or-break to prevent. |
| [01–10](archive/index.md) | The pre-v1.0 plans, collapsed into the roadmap in July 2026. Plans 04 and 08 hold real corpus history. |
