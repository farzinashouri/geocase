# Plan 29 — Real Geometry Previews and a Single Compare Page

> **Status: proposed 2026-08-28.**

## Context

Two complaints, one root cause.

**The schematics do not show the data.** [`scripts/catalog_svg.py`](../../scripts/catalog_svg.py) draws every diagram from *metadata only* — `_VECTOR_SHAPES` is a dict of seven hardcoded coordinate lists keyed by geometry type. Every `Polygon` case in the catalog therefore renders the identical quadrilateral. `dateline_crossing_polygon`, `self_intersecting_bowtie`, and `simple_valid_polygon` are pixel-for-pixel the same drawing.

That is not a bug in the sense of a mistake — the module's docstring states the constraint deliberately: the generator must stay dependency-free so `mkdocs build` works from a plain checkout, and the output must stay text so `--check` diffs stay readable.

But the constraint has an cost nobody priced. **The schematic is least informative exactly where the case is most interesting.** A catalog whose entire value proposition is "realistic geospatial edge cases" illustrates its dateline-crossing polygon with a generic blob that crosses nothing. The diagram actively conceals the feature the case exists to demonstrate.

**There is no all-cases page.** `_case_grid()` ([`generate_catalog_pages.py:175`](../../scripts/generate_catalog_pages.py#L175)) already renders thumbnail-card grids and works today — but it is only ever called from risk hubs and format hubs ([line 527](../../scripts/generate_catalog_pages.py#L527)), each showing one filtered slice. The catalog index is link tables. The grid machinery exists and has simply never been pointed at the full corpus.

### What I verified in this tree

- **103 of 104 vector cases load through the public API.** `geocase.load_case(id).load()` returns a GeoDataFrame with real coordinates for every format in the catalog — GeoJSON, Shapefile, GPKG, KML, CSV_WKT, WKT, WKB, SQLite, FlatGeobuf, GML, Parquet, Feather, Arrow, GeoArrow. `VectorCase.load()` ([`vector.py:48-121`](../../src/geocase/cases/vector.py#L48-L121)) already dispatches all of them.
- **Bare `geopandas.read_file()` reaches only 78 of 104.** The other 26 are WKB/WKT geometry blobs, CSV_WKT, and the Arrow-family formats. This matters: the preview generator must go through `VectorCase.load()`, not `read_file`, or a quarter of the catalog silently falls back to archetypes.
- **Exactly one case cannot load: `unclosed_ring_polygon`** raises `GEOSException: Points of LinearRing do not form a closed line`. That case is *supposed* to be malformed. The archetype fallback is therefore load-bearing, not decorative — and the set of cases needing it will grow as Plan 28 adds more deliberately-broken fixtures.
- **The dependency constraint is narrower than the docstring implies.** The `catalog` CI job already installs `-e .[raster,vector]` ([`ci.yml:137`](../../.github/workflows/ci.yml#L137)) — geopandas and shapely are present — and it is the only job that runs `generate_catalog_pages.py`. The `docs` job installs `.[docs]` and runs `mkdocs build --strict` over *committed markdown*; it never invokes the generator. **Adding geopandas to the generator requires no CI change and does not affect the docs build.**
- Rasters are a genuinely different problem: real pixels mean PNG/data-URI output, which forfeits the text-diff property that makes `--check` reviewable.

### Intended outcome

1. A vector case's diagram shows *that case's actual geometry*, at its real proportions, with the archetype retained as a labelled fallback.
2. One page renders every case in a filterable, sortable table so cases can be compared side by side.
3. The text-diffable `--check` property survives Phase 1 intact.

### Non-goals

- Raster pixel previews are **Phase 3**, deliberately last and independently droppable.
- No change to `case.yaml` schema, case ids, or any part of the v1.0 compatibility surface.
- No basemap, no reprojection to a display CRS beyond a normalizing fit-to-viewport transform.

---

## Phase 1 — Real vector geometry previews

### 1.1 Failing test: previews differ per case

Add to `tests/unit/test_catalog_diagrams.py`:

- `test_distinct_polygons_render_distinct_paths` — assert `case_thumbnail(simple_valid_polygon) != case_thumbnail(dateline_crossing_polygon)`. **This fails today**: both are the same hardcoded quadrilateral. This is the test that pins the whole plan.
- `test_preview_reflects_real_coordinate_extent` — load `simple_valid_polygon` (a square, bounds `10,50,11,51`) and assert its emitted path is closed and its aspect ratio matches a square within tolerance.

Watch both fail before writing any generator code.

### 1.2 Geometry → SVG path projection

New module `scripts/catalog_geometry.py`, kept separate from `catalog_svg.py` so the metadata-only drawing path stays intact and independently testable.

- `geometry_to_path(gdf, width, height) -> str | None` — take the GeoDataFrame's geometries, compute `total_bounds`, and fit to the existing 120×80 viewport preserving aspect ratio, centred, with a small margin.
- Emit SVG `<path>` `d` strings per geometry: points as `<circle>`, lines as `M/L`, polygons as `M/L…Z` with `fill-rule="evenodd"` so interior rings render as actual holes.
- **Round every coordinate to a fixed 2 decimals.** Non-negotiable: unrounded floats make `--check` diffs churn on platform FP noise, which would destroy the gate's signal.
- Degenerate extents (a single point, a zero-width bbox) get a fixed nominal span rather than dividing by zero.

### 1.3 Wire previews into the generator, with fallback

- `catalog_svg.case_thumbnail` / `case_diagram` gain an optional injected geometry provider. Default stays metadata-only, so `catalog_svg` remains importable and testable with no geospatial stack.
- `generate_catalog_pages.py` supplies a provider backed by `geocase.load_case(id).load()`, wrapped so **any** exception falls back to the archetype — `unclosed_ring_polygon` must not break the build, and neither must the next deliberately-broken case.
- Cache loads per case id; the generator touches each case several times across index, hub, and case pages.

### 1.4 Captions must stop claiming the wrong provenance

The current caption asserts "Shape is illustrative, not the fixture's coordinates" ([`catalog_svg.py:199`](../../scripts/catalog_svg.py#L199)) and the index carries a `!!! warning` saying schematics are never drawn from fixture bytes. Once previews are real those statements invert, and a docs page that lies about its own provenance is precisely the defect class Plan 28 exists to kill.

- Real previews: "Rendered from the case's actual geometry."
- Fallback previews: "Schematic only — this case's geometry could not be rendered." The distinction must be visible on the page, not silent.
- Update the index's warning block to describe both paths.
- Add `test_caption_matches_render_path` asserting the caption tracks which path was taken.

### 1.5 Regenerate and gate

Run `python scripts/generate_catalog_pages.py` (conda env — needs `osgeo`), inspect a sample of diffs by eye, and confirm `--check` is clean on a second run. Confirm `mkdocs build --strict` still passes.

---

## Phase 2 — The compare page

### 2.1 Failing test: the page exists and covers every case

- `test_compare_page_lists_every_case` — assert `docs/_generated/catalog/compare.md` exists and contains a row for all 135 case ids. Fails: no such file.
- `test_compare_page_links_resolve` — reuse the existing raw-HTML href checks from `test_catalog_diagrams.py`; these anchors bypass mkdocs link rewriting exactly as the card grid does, so they carry the same silent-breakage risk that shipped 187 broken links in Batch 5.

### 2.2 Render the table

`_render_compare_page()` in `generate_catalog_pages.py`, emitting raw HTML (not a Markdown table — cells carry inline SVG):

| Preview | Case | Category | Format | Geometry | CRS | Risk types |

Sorted by category then geometry type then id, so related shapes sit adjacent. Preview cell reuses `case_thumbnail`. Case cell links to the case page. Raster rows show the band-stack schematic; NetCDF rows, which have no drawable diagram, get an explicit em-dash rather than an empty cell.

### 2.3 Filtering and sorting

A small vanilla-JS file at `docs/javascripts/catalog-compare.js`, registered via `extra_javascript` in `mkdocs.yml`:

- Text box filtering on id/title/risk substring.
- Dropdown filters for category, format, geometry type, built from the rendered rows.
- Click-to-sort on column headers.
- A live "showing N of 135" count.

Constraints: no external library, and **the table must be fully readable with JS disabled** — filtering is progressive enhancement over a complete server-rendered table.

### 2.4 Nav and styling

- Add to `mkdocs.yml` nav under the catalog section as "Compare All Cases".
- Table styles into `docs/stylesheets/catalog.css` using the existing `--gc-*` custom properties so light/dark tracks the Material toggle. Add `overflow-x: auto` on the table wrapper — seven columns will not fit a phone.

---

## Phase 3 — Raster previews (deferrable)

Independent of Phases 1–2, and explicitly droppable without stranding them.

### 3.1 Decide the encoding first

Real pixels cannot be text. Two options, to be settled before any code:

- **Embedded PNG data-URI in the markdown.** Self-contained, but base64 blobs in a generated file make `--check` diffs unreviewable — the gate degrades to "some bytes changed".
- **PNG files under `docs/_generated/catalog/previews/` referenced by path.** Diffs stay readable (a binary file changed, by name), reviewable per case, and the existing `generate_checksums.py` pattern extends to cover them.

**Recommendation: separate PNG files.** It preserves the reviewability property that motivated the text-only constraint originally.

### 3.2 Failing test, then render

- Assert a preview exists for every raster case declaring `expected_shape`, and that a known-nodata case's preview marks nodata distinctly from valid pixels.
- Render via the existing dependency-free `geocase.raster` primitive where possible; grayscale ramp for single-band, RGB composite for 3+ band, nodata in a flagged colour that is not on the ramp.
- Upscale small rasters with nearest-neighbour — many payloads are 64px or smaller and must not be shown blurred.

### 3.3 Gate the artifacts

Extend the catalog CI job to regenerate previews and fail on drift, matching how the coverage matrices are gated.

---

## Verification

1. `pytest tests/unit/test_catalog_diagrams.py -q` — green, including the new distinctness tests.
2. `python scripts/generate_catalog_pages.py --check` — clean after regeneration.
3. `mkdocs build --strict` — no broken links.
4. `ruff format --check scripts tests && ruff check scripts tests` and `mypy src`.
5. **By eye:** `dateline_crossing_polygon`, `self_intersecting_bowtie`, and `simple_valid_polygon` must be visibly different from one another, and each must look like what its title says. This is the check that actually decides whether the plan worked — the automated tests can only prove the drawings differ, not that they are *right*.
6. Confirm `unclosed_ring_polygon` renders its fallback with the honest caption rather than breaking the build.

## Risks

- **Preview churn on regeneration.** Mitigated by fixed 2-decimal rounding in 1.2; if diffs still churn, the rounding is the first thing to tighten.
- **Generator runtime.** 103 case loads on every docs regeneration. Acceptable at this size; if it bites, cache keyed on the payload checksums that `generate_checksums.py` already maintains.
- **A preview could mislead more than an archetype.** A fit-to-viewport transform normalizes away real scale, so a continent-sized and a metre-sized polygon can render identically. The caption must not overclaim: it says the geometry is real, not that the scale is comparable across cases.
- **Phase 3 weakens the `--check` gate** whichever encoding wins. That is the main reason it is sequenced last and kept droppable.
