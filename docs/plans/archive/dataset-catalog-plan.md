# Dataset Catalog & Geographic Coverage — implementation plan

> **Archived — complete. Retained as an implementation log.** Shipped as [`docs/dataset-catalog.md`](../../dataset-catalog.md).
>
> The single active roadmap is [`docs/plans/development-plan.md`](../development-plan.md).

Status: **Approved, scheduled** — see [`execution-order.md`](execution-order.md).
> **This is a scoped implementation plan for one deliverable, not a roadmap.** The single
> roadmap is [`development-plan.md`](../development-plan.md); adding "what's next" content
> here would restart exactly the drift the July 2026 roadmap collapse ended. Active plans
> live in `docs/plans/`, superseded ones in [`archive/`](index.md).

**The deliverable is split across two batches**, not implemented in one pass:

- The four items under [Out of scope](#out-of-scope-findings-now-scheduled) are defects,
  two of them inside CI gates that are supposed to prevent this exact class of error.
  They move to **Batch 3**.
- The page itself waits for **Batch 5**, because §7 (Remote / non-bundled) describes the
  surface that Batch 4 rewrites.
- The per-case tables must be **generated and CI-gated**, not hand-maintained — see
  [Drift control](#drift-control-required).

## Context

GeoCase bundles 134 cases (103 vector, 30 raster, 1 NetCDF) but **no page anywhere enumerates them**. The two generated matrices (`docs/_generated/{vector,raster}-coverage-matrix.md`) are ✅/❌ axis rollups; `case-discovery.md` teaches filtering; `adding-a-case.md` teaches authoring. A contributor or user cannot currently answer "what data do we actually have, in what formats, and why those?"

The geographic dimension is entirely invisible today. Cases cluster in a handful of deliberately-chosen coordinate neighbourhoods — Copenhagen (12.5E, 55.7N) for the vector baselines, a fictional UTM 33N tile for most rasters, the poles, the equator, the antimeridian, Svalbard — and each cluster exists for a specific geodetic reason. That reasoning lives only in scattered `notes.md` files and archived plan docs.

Outcome: one hand-written page, `docs/dataset-catalog.md`, that gives the whole picture — what we have, why we chose those formats, and where on Earth we are exercising the CRS/geodesy paths.

**Important framing:** all bundled data is synthetic/curated (`source.name` is `geocase-curated` or `geocase-synthetic`; no case carries a real provenance URL or agency). Coordinates are *nominal* — chosen to put data in a geodetic condition, not to depict a real acquisition. The doc must say this up front so the map reads as "conditions tested", not "places imaged".

## Deliverable

**One new file: `docs/dataset-catalog.md`** + one nav line in `mkdocs.yml`.

### Structure

1. **Preamble** — scope, and the synthetic-data note as an `!!! note` admonition (the `admonition` extension is already enabled in `mkdocs.yml`).
2. **At a glance** — counts by category/format/tier; the 4.2 MB total; the bundled-vs-remote split.
3. **Why these formats** — a table: format → what it represents in the ecosystem → what failure mode it uniquely exposes. This is the "why we chose these" core. E.g. Shapefile → DBF 10-char truncation + code-page encoding; KML → forced WGS84 + string-only ExtendedData; Parquet/Arrow/Feather → columnar nullable-dtype downcast; SpatiaLite/GPKG → SQL container semantics; WKB/WKT/CSV_WKT → CRS-less serialization.
4. **Vector datasets**
   - The 66-case geometry × format baseline matrix (6 geometries × 12 format axes), with the known holes called out (Parquet only Polygon/MultiLineString; Feather only Point/MultiPoint; Arrow only Point; GeoArrow only LineString).
   - The 36 `special/` edge cases as one table per family: `crs` (11), `dateline` (6), `invalid` (6), `encoding` (5), `precision` (3), `empty` (2), `degenerate` (2), `holes` (1) — columns: id, geometry, CRS, location/bbox, what it exercises.
   - `geometrycollection_mixed_valid` (1).
5. **Raster datasets** — 30 GeoTIFFs in four groups: product families (17: optical/multispectral/COG/SAR/DEM/NDVI/landcover/mask), dtype family (5), nodata-alignment-CRS family (3), footprint edge cases (5). Columns: id, bands/dtype/shape, CRS, nodata, exercises.
6. **NetCDF** — `latlon_small` (1).
7. **Remote / non-bundled** — the 7 declared cases in `extended-manifests/` and their `bundled_analog` mapping; note the `replace_me` checksums mean they aren't fetchable yet (cross-link `remote-datasets.md`).
8. **Where in the world we test** — the geographic section:
   - Leading note restating that coordinates are nominal.
   - **ASCII world map** in a fenced block, ~72 cols, equirectangular, with lettered markers (A–H) at each cluster.
   - **Location table**: marker, region, lon/lat, CRS involved, case count, and *why that spot* — e.g. Svalbard because UTM zone 33X is a hand-carved exception a naive `floor((lon+180)/6)+1` gets wrong; ±179.x because it splits UTM 32601/32660 and breaks naive bbox; the poles because meridian convergence makes area/centroid degenerate; 0,0 because it is the geocoding-failure sentinel.
   - Clusters to plot: Copenhagen/Øresund (~12.5E 55.7N — 66 baselines + precision cluster), UTM 33N synthetic tile (~15E, two northing bands ~4.5e6 and ~5.6e6 — most rasters), Svalbard (~20E 78N), Czechia (~15E 50.6N — rasterize-match pair), North Pole, South Pole, Equator (0N, −30→30E and 10E), Antimeridian (±179–190), Null Island, Web Mercator baseline, and the encoding case's European city names (Zürich/Köln/Malmö/São Paulo — note São Paulo is the one southern-hemisphere attribute value).
   - **Coverage gaps** subsection, stated honestly: no southern-hemisphere UTM geometry, no southern-hemisphere raster, nothing in Asia/Africa/Australia/the Americas, no case near the 84N/80S UTM validity limits, no Norway zone-32V exception (only the Svalbard 33X one).

### Style constraints

- Match existing docs: `#` title, `##` sections, GFM tables, mkdocs-material admonitions, relative links (`case-discovery.md`, `contributing/testing-edge-cases.md`, `remote-datasets.md`, `_generated/vector-coverage-matrix.md`).
- Do **not** restate the ✅/❌ rollups from the generated matrices — link to them.
- Do **not** duplicate `adding-a-case.md` (authoring) or `case-discovery.md` (filtering API).

## Files

| File | Change |
|---|---|
| `docs/dataset-catalog.md` | **new** — the whole deliverable |
| `mkdocs.yml` | add `- Dataset Catalog: dataset-catalog.md` under **Reference** (nav is at lines 27–51) |

~~Note: `not_in_nav` needs widening to `/plans/*.md`.~~ **Superseded.** Widening the glob
would silently hide every future file under `docs/plans/`, which is the drift pattern the
roadmap collapse just retired. `not_in_nav` stays narrowly scoped to `/plans/archive/*.md`;
every active plan, including this one and `execution-order.md`, is listed in the nav under
**Plans**.

## Data sourcing

All figures come from the inventory already gathered — `src/geocase/metadata/case-index.yaml` (134 entries), the per-case `case.yaml` files under `src/geocase/data/core/`, and `extended-manifests/*.yaml`. Before writing, re-read `case-index.yaml` and spot-check the `special/crs`, `special/dateline`, and raster `case.yaml` files so every id, CRS, and bbox in the tables is verbatim-correct rather than recalled.

## Out of scope findings — now scheduled

Originally recorded as "flag, don't fix". All four were verified by measurement, and two
turned out to be defects **inside CI gates**, which makes them worse than ungated bugs:
they manufacture false confidence. They were therefore **not** deferred — they moved to
Batch 3 (Step 13, "quality gates you can trust"), where they belong thematically. Three
are fixed; the fourth is a nav entry that belongs with Batch 5's docs pass.

| Finding | Verified | Severity | Status |
|---|---|---|---|
| `scripts/generate_raster_coverage_matrix.py:49` globs `rglob("case.yaml")`, missing the five `footprint_edge_cases/case_*.yaml`. The published matrix says *"Total bundled raster cases scanned: **25**"* against an actual 30. | ✅ confirmed | **High** — the artifact is gated by `git diff --exit-code`, so CI actively enforces the wrong number. | ✅ Fixed in Batch 3. Glob is now `*.yaml` filtered to `category == "raster"`; matrix regenerated at 30. The generator also fails if its discovery disagrees with `case-index.yaml`. |
| `metadata/schemas/case.schema.yaml`'s `format` enum has **7** values; `FormatType` in `catalog/models.py` has **17**. Missing: `SQLite`, `WKB`, `WKT`, `GML`, `KML`, `CSV_WKT`, `Feather`, `Arrow`, `GeoArrow`, `FlatGeobuf`. | ✅ confirmed (the plan said 16; it is 17) | **High** — the schema cannot validate 10 of the formats actually in the catalog, including `SQLite`. | ✅ Fixed in Batch 3, along with the `assertions` block (6 of 16 `AssertionHints` fields). `TestCaseSchemaMatchesModels` now pins all 7 enums and both property sets to the models. |
| `raster/affine_transform_quirk/case.yaml` is an empty stub, silently skipped by `build_case_index.py`, in no index — yet the directory ships in the wheel. | ✅ confirmed | Medium — third instance of the empty-stub pattern after `cli/` and the storage modules. | ✅ Deleted in Batch 3; `validate_catalog.py` now fails on any `*.yaml` under `data/core` that is missing from the index. |
| `docs/_generated/raster-coverage-matrix.md` is CI-gated but absent from `mkdocs.yml` nav. | ✅ confirmed | Low — already tracked as part of Step 16. | ⬜ Batch 5, with the rest of the docs pass. |

## Drift control (required)

The enumeration tables must **not** be hand-maintained.

This repository's documentation has drifted before, and expensively: docs claimed "216
unit tests" against 715, "raster has 2 cases + 1 stub" against 30, and that manifest
parsing was stubbed when it had shipped. Correcting that is a large part of why the
roadmap was collapsed. A hand-written page enumerating 134 case ids with CRS values,
bounding boxes, dtypes, and nodata values would become the highest-drift-risk artifact in
the repository, and nothing would catch it going stale.

Verification step 2 below already describes the right mechanism — extract the ids from the
markdown and diff them against `case-index.yaml` — but as a one-time manual check. Make it
a script with a `--check` mode, wired into `ci/catalog-validation.yml` alongside the two
coverage-matrix gates.

Split the deliverable accordingly:

- **Generated** (`docs/_generated/`, CI-gated): the per-case tables — id, geometry, CRS,
  bbox/location, dtype, nodata, format.
- **Hand-written** (`docs/dataset-catalog.md`): the reasoning that cannot be generated —
  why these formats, the geodetic rationale per location cluster, the ASCII world map, and
  the honest coverage gaps. This narrative is the actual value of the page.

## Verification

1. `python scripts/validate_catalog.py` and `python scripts/build_case_index.py --check` — confirm the counts quoted in the doc still hold and nothing was disturbed.
2. Cross-check every id in the doc against `case-index.yaml`: extract ids from the markdown tables and diff against the index to prove no typos and no omissions.
3. `mkdocs build --strict` — catches broken internal links and the new nav entry.
4. `mkdocs serve` and eyeball `/dataset-catalog/`: tables render, the ASCII map is inside a fenced code block so it survives, admonitions render, and the page does not scroll horizontally in the material theme.
