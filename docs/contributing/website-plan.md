# Public Website — implementation plan

Status: **Proposed, unscheduled** — no batch assigned; see [Ordering](#ordering-and-hard-constraints).

> **Why this lives in `contributing/` and not `docs/plans/`.** `docs/plans/` holds only the
> archive of superseded roadmaps; the single roadmap is
> [`development-plan.md`](development-plan.md). This is a scoped implementation plan for one
> deliverable, not a competing roadmap — the same reasoning that placed
> [`dataset-catalog-plan.md`](dataset-catalog-plan.md) here.

## Context

GeoCase publishes documentation through mkdocs-material at
`https://farzinashouri.github.io/geocase`. That covers *readers who already found the
project*. It does nothing for discovery, and it presents the catalog — the thing that
actually distinguishes GeoCase from a fixtures folder — as prose rather than as data.

The catalog is 134 cases carrying validated, structured metadata: `category`, `format`,
`geometry_type`, `crs`, `tags`, `risk_types`, `assertions`, `expected_capabilities`. That
metadata is already machine-readable and already CI-gated. It is currently rendered
nowhere except two ✅/❌ axis rollups.

**The core observation:** each case is a small, self-describing dataset. Rendered one page
per case, the catalog becomes ~134 indexable pages, each answering a specific long-tail
query ("test data for dateline crossing polygon GeoJSON", "GeoTIFF int16 nodata fixture").
Emitting `schema.org/Dataset` JSON-LD on those pages additionally makes them eligible for
**Google Dataset Search** — a discovery surface with essentially no competition from
testing libraries.

This is the same drift-control argument as the dataset catalog page: the per-case pages
must be **generated and CI-gated**, never hand-maintained.

## Architecture decisions

Taken during design discussion, recorded here so they are not relitigated.

| Decision | Choice | Rationale |
|---|---|---|
| Site structure | **Hybrid** — hand-written landing page + mkdocs-material for docs | Material has no marketing-page mode; a bespoke landing page is ~4–6h against ~100h for a fully custom site. Docs machinery (search, nav, TOC, highlighting) stays free. |
| Backend | **None** | Every surface is static. Search is client-side (lunr). Nothing needs a server. |
| Frontend build | **None** — no Node toolchain | Contributors are Python developers. Adding npm to a Python repo is a real maintenance cost with no matching benefit at this size. |
| Page generation | **Plain Python**, matching `scripts/generate_*_coverage_matrix.py` | Markdown output is line-oriented and shallow; f-strings read better than templates for it. |
| Templating | **Jinja2 deferred, not rejected** | Already installed (3.1.6, via mkdocs and mkdocs-material) so adoption is free later. Earns its place around the third custom HTML page, when header/footer duplication appears. Not before. |
| Domain | **Optional, deferred** | github.io works fully. A domain is orthogonal to every other choice here and can be added at any point. See [Deferred](#deferred). |

**Rejected:** Astro/Starlight and a fully custom site. Both were evaluated; both introduce
a Node toolchain to buy polish rather than reach, and neither changes what ranks.

## Deliverable

### A. Catalog generator — `scripts/generate_catalog_pages.py`

Reads every case through `geocase.catalog.registry.get_registry()` (validated
`CaseMetadata`, not raw YAML) and emits under `docs/_generated/catalog/`:

| Output | Count | Contents |
|---|---:|---|
| `index.md` | 1 | Counts by category; risk and format facet tables; full case listing |
| `cases/<case_id>.md` | 134 | Per-case page — summary table, copy-pasteable `pytest` snippet, `behavioral_goal`, risk types, assertion table, files, source/license, tags, related cases, JSON-LD |
| `risk/<slug>.md` | 36 | Hub page per risk type |
| `format/<slug>.md` | 16 | Hub page per format |
| **Total** | **187** | |

**Thin-content gate.** Of 110 distinct risk types, **74 apply to exactly one case**.
A hub page listing a single row is thin content that dilutes crawl budget, so hub pages
are generated only at `MIN_HUB_CASES = 2` (measured: 36 qualify). Single-case risk types
still appear on the case page and in the index — unlinked, not hidden.

**Related-case ranking.** Risk-type overlap is weighted 2×, tag overlap 1×, same-category
+1. A reader browsing one failure mode wants the other cases exercising it, not other
cases in the same format.

### B. Landing page

One hand-written `index.html`, served at the site root, with MkDocs output beneath it.
Sections: problem statement → the `pytest` snippet from the README → what the catalog
covers (counts, formats, risk families) → install → links into docs and catalog.

Styled against Material's existing CSS custom properties (`--md-primary-fg-color`,
`--md-typeset-color`, `--md-default-bg-color`) so the dark-mode toggle already in the
theme applies to the landing page for free — no second palette to maintain.

**Timeboxed.** The landing page has no objective "done" and is the one item here that can
absorb unbounded effort. Ship the first version.

### C. SEO surface

| Item | Where | Notes |
|---|---|---|
| `Dataset` JSON-LD | Per-case pages | The Google Dataset Search play. Fields map directly from existing metadata; `source.license`/`source.name` populate `license`/`creator`. |
| `SoftwareApplication` JSON-LD | Landing page | |
| Meta description | Front matter, all generated pages | Falls back `description` → `behavioral_goal` → `title`, truncated to 155 chars |
| Social cards | mkdocs-material `social` plugin | Community edition; needs Pillow + CairoSVG |
| `sitemap.xml` | Already generated by MkDocs | Submit to Google Search Console + Bing |
| `noindex` on archives | `docs/plans/archive/*` | Superseded planning docs are thin and duplicative; they are already `not_in_nav` but still built |

### D. Hosting

GitHub Pages or Cloudflare Pages. Both build from either remote, which matters because
this repo has a GitHub `repo_url` and GitLab CI.

## Files

| File | Change |
|---|---|
| `scripts/generate_catalog_pages.py` | **new** — the generator |
| `docs/_generated/catalog/**` | **new, committed** — 187 generated pages |
| `docs/index.html` (or Pages root) | **new** — landing page |
| `docs/stylesheets/landing.css` | **new** — landing page styles |
| `mkdocs.yml` | add `- Case Catalog: _generated/catalog/index.md` under **Reference**; extend `not_in_nav` with `/_generated/catalog/cases/*.md`, `/_generated/catalog/risk/*.md`, `/_generated/catalog/format/*.md`; add the `social` plugin |
| `ci/catalog-validation.yml` | add the `--check` gate |
| `pyproject.toml` | add Pillow + CairoSVG to the `docs` extra (social cards only) |

`not_in_nav` must be extended **per subdirectory**, not widened to `/_generated/*`.
Widening the glob would silently hide future generated files — the drift pattern the
roadmap collapse retired.

## Drift control (required)

The generator ships with `--check`, which rebuilds every page in memory and compares
against what is committed, reporting three failure classes: `missing`, `out of date`,
`stale`. It runs in `catalog_validation` alongside `build_case_index.py --check` and
`validate_catalog.py`.

Without this gate the pages silently desynchronize from the catalog on the first case
edit, and the site starts publishing assertions the code no longer makes. Per Batch 3's
rule — **prefer a gate over a promise**.

Note that `scripts/` is outside the ruff gate (CI lints `src` and `tests` only), so the
generator follows the tab-indented house style of the existing `scripts/` modules rather
than `ruff format` output.

## Prototype status

A working generator was written during the design discussion and is **untracked and
unmerged**. It ran clean over all 134 cases, produced 261 pages (pre-gating), and passed
its own `--check`. Three subsequent edits — hub gating, list-literal rendering, index
wiring — are written but **unverified**: the verification run failed on an unrelated
circular import (`catalog/roots.py` → `cases.base`) introduced in `src/` by concurrent
work during the session.

Treat the prototype as evidence the approach works, not as a reviewed deliverable. The
measured figures in this plan (134 cases, 110 risk types, 74 single-case, 16 formats)
come from that run and are the numbers to re-verify, not inherit.

## Ordering and hard constraints

| Constraint | Why |
|---|---|
| **Batch 5 before this plan** | Step 16 is the docs truth pass. Generating 134 public pages from metadata that has not been through it publishes any error 134 times. |
| Dataset catalog page before the site | `dataset-catalog-plan.md` establishes what the corpus *is*; this plan renders it. Reversed, the site's framing gets written twice. |
| Generator + `--check` gate before the landing page | The catalog is the reach; the landing page is the polish. If only one ships, it should be the catalog. |
| v1.0 released before promoting the site | Driving traffic to an alpha with no installable package wastes the first-impression budget. |
| Case-description rewrite before expecting rankings | See below. |

## The content cost this plan does not remove

Case descriptions are written for contributors. `sar_dualpol_small` reads *"Exercises
dual-polarisation radar band handling and ordering"* — accurate, and not what anyone
types into a search engine.

The generator will publish 134 pages regardless. Whether they rank depends on a
description pass that is domain expertise, not tooling: roughly 4–6 hours, and it cannot
be automated or delegated to the generator. **This is the single largest determinant of
whether the SEO argument in this plan pays off**, and it is worth scheduling explicitly
rather than assuming it happens.

## Deferred

- **Custom domain.** ~$12/yr, orthogonal to everything above. Costs on github.io: Search
  Console is limited to a URL-prefix property (no DNS control), the future recommendation
  API has no natural subdomain, and moving later needs redirects. None are blockers.
- **Faceted catalog filter UI.** Hand-rolled JS over a generated JSON index. Static hub
  pages are what gets crawled; interactive filtering is a convenience. ~4–6h.
- **Per-case preview thumbnails.** Generated from bundled data via rasterio/geopandas.
  Largest visual improvement to the case pages; needs a generation script and CI wiring.
- **Blog.** Problem-first articles ("why reprojection breaks at the antimeridian") are the
  strongest organic-traffic lever, and an ongoing commitment rather than a build task.
- **Jinja2 adoption.** At the third custom HTML page. Zero migration cost — already installed.
- **Recommendation service UI.** Depends on
  [`../design/case-recommendation-service.md`](../design/case-recommendation-service.md),
  which needs the only server component in the entire plan (FastAPI + Pydantic). Out of
  scope here.

## Open questions

1. **Landing page at the repo root or `docs/`?** Affects whether MkDocs serves `/` or
   `/docs/`, and therefore every canonical URL and the JSON-LD `url` field. Decide before
   the generator's `--site-url` default is committed, since changing it rewrites all 134
   pages.
2. **Is `_generated/catalog/` the right path?** It is honest about provenance but produces
   long URLs (`/_generated/catalog/cases/<id>/`). A top-level `/catalog/` reads better and
   ranks marginally better. Cost is one more directory outside the `_generated` convention.
3. **Commit the 187 pages, or generate at build time?** Committing matches
   `_generated/*-coverage-matrix.md` precedent and makes `--check` meaningful; it also puts
   187 files into every diff that touches a case.
