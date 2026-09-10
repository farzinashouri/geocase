# Plan 47 — Daily Content for SEO: A Publishing System, Not a Writing Commitment

> **Status: proposed 2026-09-10.**

## Context

The goal is a content strategy that puts something new on the GeoCase site every day, to grow
organic search traffic. The content does not have to be about geocase itself.

What the tree carries today (measured 2026-09-10):

- **Site:** `https://farzinashouri.github.io/geocase/`, MkDocs Material, `plugins: [search]`
  only, deployed by [`.github/workflows/pages.yml`](../../.github/workflows/pages.yml) on push
  to `main`. `mkdocs build --strict` is the gate.
- **Indexable assets already built:** 174 case pages, 59 risk-hub pages, 16 format-hub pages,
  and a compare page with two world maps, all under `docs/_generated/catalog/` with
  `schema.org/Dataset` JSON-LD and per-page `description:` front matter. Per-case `notes.md`
  prose (~12,176 words per [Plan 26](26-docs-truth-pass-and-seo-prep.md)) is rendered.
- **What is missing for SEO:** no blog/post surface at all; no Open Graph card image (the
  `social` plugin is blocked on native `libcairo`, [Plan 26](26-docs-truth-pass-and-seo-prep.md)
  §3.4); case descriptions still "written for contributors, not searchers" per the generator's
  own comment ([Plan 24](24-catalog-site-on-owned-domain.md) sized rewriting them at 4–6 hours
  and called it *"the single largest determinant of whether the SEO argument pays off"*); and no
  measurement loop — Plan 24's 90-day Search Console gate never started, because that plan was
  superseded when the project chose GitHub Pages over an owned domain.
- **Unpublished narrative material with real search value:**
  [`docs/validation.md`](../validation.md) is published; `docs/geocase_validate/` (draft
  upstream bug reports) is excluded from the site by decision. Three upstream issues are now
  public — odc-stac#288 (accepted within 12 hours), rio-tiler#993, titiler#1493 — per
  [Plan 43](43-upstream-filing-queue-and-repo-liveness.md), which embargoes broadcast until
  **filed plus two weeks** (day 14 from filing = **2026-09-20**).
- **A closed vocabulary that is also a keyword map:**
  [`src/geocase/catalog/risk_types.py`](../../src/geocase/catalog/risk_types.py) holds roughly
  111 `family/specific` terms across nine families (crs, extent, transform, nodata, dtype,
  precision, geometry, measurement, format). Each is a failure mode people search for when it
  bites them.
- **`benchmark/` is excluded from the site by decision** — the `mkdocs.yml` comment records it
  as "not mature enough to present as a product surface."

The honest constraint: one author cannot hand-write a quality post every day. "Daily" has to
come from a **system** — a small number of hand-written pieces per week, a larger number of
scaffolded short pieces whose substance comes from real bytes in the corpus, and scheduled
publishing so writing happens in batches while pages go live daily. Google's scaled-content
policy penalises templated pages with no unique substance; the defence built into this plan is
that every generated page carries at least one concrete number computed from a real file, which
the corpus already provides via `AssertionHints` ground truth
([Plan 40](40-round-3-packaging-truth-and-vocabulary.md)).

**Decided constraints (from the user):**
- Content need not be about geocase — roughly 60% of posts are about the underlying geospatial
  problem, mentioning geocase only as the case that reproduces it.
- Publishing cadence is daily, achieved through scheduling rather than daily authorship.

**Out of scope:** registering a domain (superseded, [Plan 24](24-catalog-site-on-owned-domain.md));
publishing anything from `docs/geocase_validate/`; publishing the benchmark subsystem before
[Plan 46](46-benchmark-depth-and-measurement.md)'s gate produces a number; adding an RSS
dependency before the 90-day measurement gate (§5) resolves.

---

## The strategy

### Principles

1. **Hub-and-spoke on the risk vocabulary.** The 59 risk-hub pages are the hubs. Every post
   links to at least one hub and at least one case page; hub pages link back to their posts
   (Phase 2). This is what turns ~300 pages into a topical cluster instead of ~300 orphans.
2. **Not only geocase.** ~60% of posts address the *problem* (how GeoPackage stores datetimes,
   what `AREA_OR_POINT` means, why area in EPSG:4326 is meaningless) and mention geocase only as
   "the case that reproduces this." ~40% are geocase-facing (recipes, spotlights).
3. **Substance rule.** No published post under ~300 words of non-templated prose, and every
   scaffolded post carries at least one concrete number computed from the case's ground truth
   (`expected_mean_masked`, `nodata_pixel_count`, extent, vertex count). Templates supply
   structure, never the body.
4. **Batch-write, drip-publish.** Two writing sessions per week; posts are future-dated and go
   live one per day via a scheduled rebuild.
5. **Broadcast order follows Plans 39 and 43, not this plan.** A post narrating a library defect
   publishes only after the upstream issue is public *and* the Plan 43 embargo has passed.
   Nothing from `docs/geocase_validate/` is published by this plan.
6. **Measured with a pre-committed gate**, in the style of Plans 24 and 46: a 90-day Search
   Console number decides whether the cadence continues, halves, or stops.

### Assumptions (stated so the user can override)

- Writing budget ≈ **4 hours/week** (two 2-hour sessions). At 2 hours/week, drop pillar C to
  fortnightly and keep the rest.
- The Material `blog` plugin (bundled with `mkdocs-material>=9`, already pinned in
  `pyproject.toml`, no new dependency) is the post surface. An RSS feed needs
  `mkdocs-rss-plugin`, a new `[docs]` dependency — deferred to after the §5 gate.
- The benchmark stays unpublished until [Plan 46](46-benchmark-depth-and-measurement.md) Phase 1
  reports a number; an "does an LLM get the antimeridian right?" series is **queued, not
  scheduled** (§6, U33).

### The six pillars

| # | Pillar | Cadence | Source of substance | Hand-written share |
|---|---|---|---|---|
| A | **Failure mode of the week** — one `family/specific` term: what it is, a minimal reproduction in plain GDAL/shapely/rasterio, how to detect it, which case exercises it | 2/week (Mon, Thu) | `RISK_TYPES` description + the linked cases' `notes.md` + ground-truth numbers | ~50% (reproduction + detection paragraphs) |
| B | **Glossary / one-question pages** — "What is EPSG:32633?", "What does `AREA_OR_POINT` mean?", "GeoPackage requirement 15", "RFC 7946's antimeridian rule" | 2/week (Tue, Sat) | External specs, cited; one case as the worked example | ~70%, but short (300–500 words) |
| C | **Library behaviour explainers** — "How pyogrio handles `bbox=` on GPKG", "GDAL's `intelliround` and coordinates below 1e-13", "odc-stac's `crs=` and native resolution" | 1/week (Wed) | `known_divergences` records, `docs/validation.md`, public upstream threads only | 100% |
| D | **Recipes** — "Test your reprojection function against 174 cases in twelve lines", "Differential-test two readers with `geocase.differential`" | 1/week (Fri) | `docs/testing-your-function-with-geocase.md`, `examples/` | ~80% |
| E | **Case spotlight** — one case: what it looks like (existing SVG/PNG preview), where it is (extent/region), the one number that matters, which risks it declares | 1/week (Sun) | Fully scaffolded from `CaseMetadata` + `notes.md`; author adds one paragraph | ~20% |
| F | **Monthly: a bug story** — one filed-and-public finding, narrated as a two-library comparison | 1/month, replaces a pillar-A slot | Public issue thread + `known_divergences` | 100% |

Seven slots a week is a daily cadence. Hand-written load ≈ two pillar-A halves + two short-B
posts + one C + one D + one E paragraph ≈ 4 hours, matching the assumed budget.

### Keyword map (starting point; refined from Search Console after week 4)

Search volume cannot be measured from this repo. The free instruments are Search Console
impressions, Google autocomplete, "People also ask," and issue titles in the geopandas /
rasterio / shapely / GDAL trackers — real users phrasing real problems. Seed clusters, one per
risk family, each already backed by a hub page:

| Family | Query cluster (natural phrasing) | Hub page | Anchor cases |
|---|---|---|---|
| nodata | "rasterio nodata -9999 mean wrong", "numpy nan nodata geotiff", "landcover 0 nodata or class" | `nodata-ignored`, `nodata-nan-mishandled` | `geotiff_nodata_small` (48.08 vs −152.86), `dem_nan_nodata_small`, `landcover_ambiguous_zero_small` |
| extent | "polygon crosses dateline geopandas", "antimeridian bbox west greater than east", "geojson antimeridian split" | `extent-antimeridian`, `extent-polar` | `dateline_crossing_polygon`, `antimeridian_crossing_line`, `optical_dateline_small` (footprint reaching 180.22) |
| crs | "epsg 4326 axis order lat lon", "utm zone 33 vs 32 boundary", "geopandas area in degrees" | `crs-axis-order`, `crs-zone-selection`, `crs-units` | `utm_zone_33n_to_32n_pair`, `crs_mismatch_overlay_pair` (3,359 km off) |
| transform | "rasterio bottom up raster negative resolution", "rotated geotiff affine", "AREA_OR_POINT half pixel shift" | `transform-bottom-up`, `transform-rotated`, `transform-pixel-anchor` | `bottom_up_dem_small`, `rotated_two_islands`, `pixel_is_point_dem_small` |
| geometry | "shapely invalid polygon self intersection fix", "empty geometry vs null geopackage", "unclosed ring wkt" | `geometry-silent-invalid`, `geometry-null-empty-conflation` | `unclosed_ring_polygon`, `empty_geometry_gpkg`, `fractal_coastline_polygon` |
| precision | "geojson coordinates precision loss roundtrip", "gdal coordinate rounding 1e-14" | `precision-loss`, `precision-formatter-boundary` | `precision_loss_geojson_roundtrip` |
| format | "geopackage datetime timezone requirement", "shapefile field name 10 characters", "cog not tiled overviews missing" | `format-*` hubs | the scale trio ([Plan 28](28-validate-geocase.md) Phase 3), `format-not-tiled` cases |
| measurement | "calculate polygon area correct crs python", "geodesic vs planar distance" | `measurement-incorrect-area`, `measurement-distance-error` | UTM baselines |
| dtype/scaling | "int16 ndvi scale offset raster", "uint8 overflow raster arithmetic" | `dtype-*`, `scaling-ignored` | `ndvi_scaled_int16_small` (a 10,000× finding, [Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md)), `geotiff_int8_small` |

Each row is roughly a month of pillar A/B/E posts.

### First 14 days (concrete; starts the day the blog surface lands)

| Day | Pillar | Title (working) | Links |
|---|---|---|---|
| 1 | A | Why your raster mean is negative: NoData that is also a valid value | `nodata-ignored` → `geotiff_nodata_small` |
| 2 | B | What is EPSG:4326, and which way round are the coordinates? | `crs-axis-order` |
| 3 | C | pyogrio's `bbox=` on GeoPackage returns 2 rows where 3 exist (a public divergence record) | `empty_geometry_gpkg` known divergence |
| 4 | A | A polygon that crosses the dateline is not a bug — your bbox is | `extent-antimeridian` → `dateline_crossing_polygon` |
| 5 | D | Test your reprojection function against 174 cases in twelve lines of pytest | getting-started |
| 6 | B | What `AREA_OR_POINT` means and the half-pixel it moves | `transform-pixel-anchor` |
| 7 | E | Case spotlight: `rotated_two_islands` | compare page |
| 8 | A | Bottom-up rasters: when the y-resolution is positive | `transform-bottom-up` → `bottom_up_dem_small` |
| 9 | B | GeoPackage requirement 15: why datetimes must be UTC | `format-sqlite-driver-behavior` |
| 10 | C | GDAL writes 1e-14 as 0: the `intelliround` boundary ([Plan 44](44-gdal-as-target-and-the-numeric-axis.md) finding — publish only once filed and past its own embargo; otherwise swap in a `known_divergences` entry) | `precision-formatter-boundary` |
| 11 | A | Zero as NoData, zero as a land-cover class | `nodata/ambiguous_zero` → `landcover_ambiguous_zero_small` |
| 12 | D | Differential testing: read every case twice and let the readers disagree | `differential-testing.md` |
| 13 | B | UTM zone 33 or 32? What happens exactly on the boundary | `crs-zone-selection` → `utm_zone_33n_to_32n_pair` |
| 14 | E | Case spotlight: `optical_dateline_small` | — |

Day 15 onward is generated from the keyword map by the same rotation. **The first pillar-F post
(odc-stac#288, already accepted) is scheduled for the first Sunday after 2026-09-20**, the Plan
43 embargo date.

---

## Phase 1 — The publishing surface

Config plus one gate; roughly half a day.

### 1.1 Test first

New `tests/unit/test_site_config.py`: parse `mkdocs.yml` and assert (a) `blog` is present in
`plugins` with `blog_dir: posts`, `draft_if_future_date: true`, `post_url_format: "{slug}"`; and
(b) every markdown file reachable from `nav` plus every `docs/posts/**/*.md` carries a non-empty
`description:` in its front matter. Watch it fail on (a) first.

### 1.2 Build

- `mkdocs.yml`: add the Material `blog` plugin (`docs/posts/`, categories mapped to the nine
  risk families, `draft_if_future_date: true`, `archive: false` to avoid thin archive pages), and
  a nav entry **Articles** between *Validation Report* and *Catalog*.
- `docs/posts/index.md` with a `description:`.
- [`.github/workflows/pages.yml`](../../.github/workflows/pages.yml): add
  `schedule: - cron: "0 6 * * *"` so future-dated posts go live on their date without a manual
  push — `draft_if_future_date` is what makes the cron meaningful.
- `docs/overrides/main.html`: extend `{% block extrahead %}` with `og:title`, `og:description`
  (from `page.meta.description`), `og:type`, `og:url`, and one static `og:image`
  (`docs/assets/og-default.png`, committed by hand). This is the `libcairo`-free substitute for
  [Plan 26](26-docs-truth-pass-and-seo-prep.md) §3.4; per-page cards stay deferred.
- `mkdocs build --strict` green.

### 1.3 Docs

`docs/contributing/workflow.md`: a "Writing a post" subsection covering front-matter shape, the
substance rule, future-dating, and the embargo rule (linking
[Plan 43](43-upstream-filing-queue-and-repo-liveness.md) by GitHub URL, per this folder's
publishing rule).

## Phase 2 — Hubs link back to spokes

Generator change; roughly half a day.

### 2.1 Test first

Extend the existing catalog-page generator test: given a post in `docs/posts/` whose front
matter declares `risk_types: [nodata/ignored]` and `cases: [geotiff_nodata_small]`, the
generated `risk/nodata-ignored.md` and `cases/geotiff_nodata_small.md` each carry a **Read more**
section linking to it. Watch it fail.

### 2.2 Build

[`scripts/generate_catalog_pages.py`](../../scripts/generate_catalog_pages.py): read
`docs/posts/**/*.md` front matter (reuse the script's existing YAML front-matter parsing; add no
dependency), build a term-to-posts and case-to-posts index, and emit the section. Regenerate all
pages; `--check` green. `docs/adding-a-case.md` gains one line documenting the `cases:` key.

## Phase 3 — The scaffold

A generation script; roughly half a day.

### 3.1 Test first

New `tests/unit/test_scaffold_post.py`: `scripts/scaffold_post.py --pillar spotlight --case
geotiff_nodata_small --date 2026-10-05` writes
`docs/posts/2026-10-05-geotiff-nodata-small.md` with `description:` prefilled from
`CaseMetadata.description`, `risk_types:`/`cases:` front matter, the preview-image link, the
extent/region line, and the ground-truth numbers table (`expected_mean_masked`,
`expected_mean_naive`, `nodata_pixel_count` where present). `--pillar failure-mode --risk
nodata/ignored` prefills the `RISK_TYPES` description and the list of declaring cases from the
`risk_types()` reverse index ([Plan 40](40-round-3-packaging-truth-and-vocabulary.md)). Watch
both fail.

### 3.2 Build

A pure read of the registry via `geocase.catalog` (`get_registry`, `risk_types()`) — no `osgeo`
needed, so it runs in either environment. Output is a draft carrying `TODO:` markers where the
author must write; `test_site_config.py` gains a check that fails the build if any
`docs/posts/*.md` still contains `TODO:` and is not `draft: true`.

## Phase 4 — Case descriptions for searchers

Editorial work; the 4–6 hours [Plan 24](24-catalog-site-on-owned-domain.md) already sized, no
code.

Rewrite the `description:` of the ~40 cases in the keyword-map anchor column first, since they
receive the most inbound links, in the form *symptom → cause → what the file contains*. Each
edit is a corpus metadata change: regenerate pages, `--check` green. Confirm against
`CHANGELOG.md`'s stated convention before assuming an entry is or isn't required — descriptions
are not one of the pinned surfaces (CRS, dtype, nodata value, id, `risk_types`) that convention
names explicitly.

## Phase 5 — Measurement and the gate

### 5.1 Setup (user action, browser)

Verify the site in Search Console via the HTML-file method (no DNS control on `github.io`), and
submit `sitemap.xml`, which MkDocs already emits. Record the start date in this plan's header
once done.

### 5.2 Pre-committed 90-day rule

Assessed 90 days after 5.1's verification date:

| Result | Action |
|---|---|
| ≥ 60% of posts indexed **and** ≥ 3 risk families each with ≥ 100 impressions/28 days | Continue daily; add the RSS plugin; queue the benchmark series (§6, U33) |
| Indexed but impressions below that | Halve cadence to pillars A/B/E only (4/week); reassess after 90 more days |
| < 30% of posts indexed at day 90 | Stop the cadence; diagnose (crawl budget on a `github.io` subpath, thin-content flags) before writing more |

Record the actual numbers in this plan's status header, in the style of
[Plan 46](46-benchmark-depth-and-measurement.md)'s gate.

## Open user decisions (U33–U35)

- **U33** — publish a benchmark-results series once [Plan 46](46-benchmark-depth-and-measurement.md)
  Phase 1 reports a number? Excluded today by decision.
- **U34** — weekly writing budget: 4 hours assumed above; correct if wrong.
- **U35** — an owned domain was rejected when [Plan 24](24-catalog-site-on-owned-domain.md) was
  superseded. This plan does not reopen that question, but the §5.2 indexing number is the
  evidence that would.

---

## Verification

- `docs/plans/47-daily-content-strategy-for-seo.md` exists in this format; its row is in
  [`docs/plans/index.md`](index.md).
- `mkdocs build --strict` stays green after each phase.
- Nothing under `docs/geocase_validate/` is referenced or published by any phase.
- Phase 1: `test_site_config.py` passes; a future-dated draft post does not appear on the live
  site before its date, and does appear on/after it once the cron runs.
- Phase 2: a risk-hub page and a case page each show a linked post in their **Read more**
  section; `generate_catalog_pages.py --check` is green.
- Phase 3: `scaffold_post.py` output matches the fields specified in 3.1 and the build fails on a
  leftover `TODO:`.

## Critical files

- `docs/plans/47-daily-content-strategy-for-seo.md` (this file), `docs/plans/index.md` (row)
- Phase 1: `mkdocs.yml`, `.github/workflows/pages.yml`, `docs/overrides/main.html`, new
  `docs/posts/index.md`, new `tests/unit/test_site_config.py`,
  `docs/contributing/workflow.md`
- Phase 2: `scripts/generate_catalog_pages.py`, `docs/adding-a-case.md`
- Phase 3: new `scripts/scaffold_post.py`, new `tests/unit/test_scaffold_post.py`
- Reused: `src/geocase/catalog/risk_types.py` (`RISK_TYPES`),
  `geocase.catalog.registry.get_registry`, the `risk_types()` reverse index
  ([Plan 40](40-round-3-packaging-truth-and-vocabulary.md)),
  `docs/_generated/catalog/previews/`
