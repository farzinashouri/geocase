# Plan 29 — Real Geometry Previews and a Single Compare Page

> **Status: implemented 2026-08-28** (all three phases).

## Context

Two complaints, one root cause.

**The schematics do not show the data.** [`scripts/catalog_svg.py`](https://github.com/farzinashouri/geocase/blob/main/scripts/catalog_svg.py) draws every diagram from *metadata only* — `_VECTOR_SHAPES` is a dict of seven hardcoded coordinate lists keyed by geometry type. Every `Polygon` case in the catalog therefore renders the identical quadrilateral. `dateline_crossing_polygon`, `self_intersecting_bowtie`, and `simple_valid_polygon` are pixel-for-pixel the same drawing.

That is not a bug in the sense of a mistake — the module's docstring states the constraint deliberately: the generator must stay dependency-free so `mkdocs build` works from a plain checkout, and the output must stay text so `--check` diffs stay readable.

But the constraint has an cost nobody priced. **The schematic is least informative exactly where the case is most interesting.** A catalog whose entire value proposition is "realistic geospatial edge cases" illustrates its dateline-crossing polygon with a generic blob that crosses nothing. The diagram actively conceals the feature the case exists to demonstrate.

**There is no all-cases page.** `_case_grid()` ([`generate_catalog_pages.py:175`](https://github.com/farzinashouri/geocase/blob/main/scripts/generate_catalog_pages.py#L175)) already renders thumbnail-card grids and works today — but it is only ever called from risk hubs and format hubs ([line 527](https://github.com/farzinashouri/geocase/blob/main/scripts/generate_catalog_pages.py#L527)), each showing one filtered slice. The catalog index is link tables. The grid machinery exists and has simply never been pointed at the full corpus.

### What I verified in this tree

- **103 of 104 vector cases load through the public API.** `geocase.load_case(id).load()` returns a GeoDataFrame with real coordinates for every format in the catalog — GeoJSON, Shapefile, GPKG, KML, CSV_WKT, WKT, WKB, SQLite, FlatGeobuf, GML, Parquet, Feather, Arrow, GeoArrow. `VectorCase.load()` ([`vector.py:48-121`](https://github.com/farzinashouri/geocase/blob/main/src/geocase/cases/vector.py#L48-L121)) already dispatches all of them.
- **Bare `geopandas.read_file()` reaches only 78 of 104.** The other 26 are WKB/WKT geometry blobs, CSV_WKT, and the Arrow-family formats. This matters: the preview generator must go through `VectorCase.load()`, not `read_file`, or a quarter of the catalog silently falls back to archetypes.
- **Exactly one case cannot load: `unclosed_ring_polygon`** raises `GEOSException: Points of LinearRing do not form a closed line`. That case is *supposed* to be malformed. The archetype fallback is therefore load-bearing, not decorative — and the set of cases needing it will grow as Plan 28 adds more deliberately-broken fixtures.
- **The dependency constraint is narrower than the docstring implies.** The `catalog` CI job already installs `-e .[raster,vector]` ([`ci.yml:137`](https://github.com/farzinashouri/geocase/blob/main/.github/workflows/ci.yml#L137)) — geopandas and shapely are present — and it is the only job that runs `generate_catalog_pages.py`. The `docs` job installs `.[docs]` and runs `mkdocs build --strict` over *committed markdown*; it never invokes the generator. **Adding geopandas to the generator requires no CI change and does not affect the docs build.**
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

## Phase 1 — Real vector geometry previews — **implemented 2026-08-28**

**What differed from the plan as written:**

- The case named `self_intersecting_bowtie` throughout this document **does not exist**. The
  catalog's bowtie is `self_intersecting_polygon`; the tests use that id.
- `geometry_to_path` became `catalog_geometry.geometry_shapes`, returning a *list of SVG
  elements* rather than one path string. Points must be `<circle>` and lines `<path>`, so a
  single `d` string could not carry a mixed GeometryCollection.
- The projection styling (fill, stroke, radius) is injected by `catalog_svg` as `*_attrs`
  strings. That keeps every colour in one module, so
  `test_schematics_use_theme_variables_not_hex` still covers the preview path.
- `unclosed_ring_polygon` behaves exactly as predicted: pyogrio emits a `Non closed ring`
  warning and then raises, the provider returns `None`, and the page falls back with the
  honest caption. The fallback is load-bearing, as 1.1 anticipated.
- **Pre-existing, fixed in passing:** this plan document's own `../../` source links broke
  `mkdocs build --strict` from the moment it was committed. They now point at GitHub.

### 1.1 Failing test: previews differ per case — done

Add to `tests/unit/test_catalog_diagrams.py`:

- `test_distinct_polygons_render_distinct_paths` — assert `case_thumbnail(simple_valid_polygon) != case_thumbnail(dateline_crossing_polygon)`. **This fails today**: both are the same hardcoded quadrilateral. This is the test that pins the whole plan.
- `test_preview_reflects_real_coordinate_extent` — load `simple_valid_polygon` (a square, bounds `10,50,11,51`) and assert its emitted path is closed and its aspect ratio matches a square within tolerance.

Watch both fail before writing any generator code.

### 1.2 Geometry → SVG path projection — done

New module `scripts/catalog_geometry.py`, kept separate from `catalog_svg.py` so the metadata-only drawing path stays intact and independently testable.

- `geometry_to_path(gdf, width, height) -> str | None` — take the GeoDataFrame's geometries, compute `total_bounds`, and fit to the existing 120×80 viewport preserving aspect ratio, centred, with a small margin.
- Emit SVG `<path>` `d` strings per geometry: points as `<circle>`, lines as `M/L`, polygons as `M/L…Z` with `fill-rule="evenodd"` so interior rings render as actual holes.
- **Round every coordinate to a fixed 2 decimals.** Non-negotiable: unrounded floats make `--check` diffs churn on platform FP noise, which would destroy the gate's signal.
- Degenerate extents (a single point, a zero-width bbox) get a fixed nominal span rather than dividing by zero.

### 1.3 Wire previews into the generator, with fallback — done

- `catalog_svg.case_thumbnail` / `case_diagram` gain an optional injected geometry provider. Default stays metadata-only, so `catalog_svg` remains importable and testable with no geospatial stack.
- `generate_catalog_pages.py` supplies a provider backed by `geocase.load_case(id).load()`, wrapped so **any** exception falls back to the archetype — `unclosed_ring_polygon` must not break the build, and neither must the next deliberately-broken case.
- Cache loads per case id; the generator touches each case several times across index, hub, and case pages.

### 1.4 Captions must stop claiming the wrong provenance — done

The current caption asserts "Shape is illustrative, not the fixture's coordinates" ([`catalog_svg.py:199`](https://github.com/farzinashouri/geocase/blob/main/scripts/catalog_svg.py#L199)) and the index carries a `!!! warning` saying schematics are never drawn from fixture bytes. Once previews are real those statements invert, and a docs page that lies about its own provenance is precisely the defect class Plan 28 exists to kill.

- Real previews: "Rendered from the case's actual geometry."
- Fallback previews: "Schematic only — this case's geometry could not be rendered." The distinction must be visible on the page, not silent.
- Update the index's warning block to describe both paths.
- Add `test_caption_matches_render_path` asserting the caption tracks which path was taken.

### 1.5 Regenerate and gate — done

Run `python scripts/generate_catalog_pages.py` (conda env — needs `osgeo`), inspect a sample of diffs by eye, and confirm `--check` is clean on a second run. Confirm `mkdocs build --strict` still passes.

---

## Phase 2 — The compare page — **implemented 2026-08-28**

**What differed from the plan as written:**

- The plan's column list started with a `Preview` column and named `Case`, `Category`,
  `Format`, `Geometry`, `CRS`, `Risk types` — that is what shipped, with the case cell
  carrying both the linked title and the id in a `<code>` so the search box has an
  obvious thing to match on.
- `test_compare_page_lists_every_case` matches on `data-case-id` attributes rather than
  reading ids out of the link hrefs: the attribute is what the filter script keys on, so
  gating it means the test breaks if the JS contract breaks, not only if a row vanishes.
- Filtering is done by toggling the row's `hidden` property rather than a class, so a
  filtered-out row is hidden from assistive technology too, not just visually.
- The script binds through Material's `document$` observable as well as
  `DOMContentLoaded`: Material swaps page content on in-site navigation without a reload,
  and a `DOMContentLoaded`-only binding leaves the table inert after the first hop.
- **Pre-existing, fixed in passing:** one `ruff format` deviation in
  `generate_catalog_pages.py`. The remaining four `ruff check` findings in `scripts/`
  predate this plan and are outside the repo's lint gate, which covers `src tests`.

### 2.1 Failing test: the page exists and covers every case — done

- `test_compare_page_lists_every_case` — assert `docs/_generated/catalog/compare.md` exists and contains a row for all 135 case ids. Fails: no such file.
- `test_compare_page_links_resolve` — reuse the existing raw-HTML href checks from `test_catalog_diagrams.py`; these anchors bypass mkdocs link rewriting exactly as the card grid does, so they carry the same silent-breakage risk that shipped 187 broken links in Batch 5.

### 2.2 Render the table — done

`_render_compare_page()` in `generate_catalog_pages.py`, emitting raw HTML (not a Markdown table — cells carry inline SVG):

| Preview | Case | Category | Format | Geometry | CRS | Risk types |

Sorted by category then geometry type then id, so related shapes sit adjacent. Preview cell reuses `case_thumbnail`. Case cell links to the case page. Raster rows show the band-stack schematic; NetCDF rows, which have no drawable diagram, get an explicit em-dash rather than an empty cell.

### 2.3 Filtering and sorting — done

A small vanilla-JS file at `docs/javascripts/catalog-compare.js`, registered via `extra_javascript` in `mkdocs.yml`:

- Text box filtering on id/title/risk substring.
- Dropdown filters for category, format, geometry type, built from the rendered rows.
- Click-to-sort on column headers.
- A live "showing N of 135" count.

Constraints: no external library, and **the table must be fully readable with JS disabled** — filtering is progressive enhancement over a complete server-rendered table.

### 2.4 Nav and styling — done

- Add to `mkdocs.yml` nav under the catalog section as "Compare All Cases".
- Table styles into `docs/stylesheets/catalog.css` using the existing `--gc-*` custom properties so light/dark tracks the Material toggle. Add `overflow-x: auto` on the table wrapper — seven columns will not fit a phone.

---

## Phase 3 — Raster previews — **implemented 2026-08-28**

Independent of Phases 1–2, and explicitly droppable without stranding them. It
was not dropped.

**What differed from the plan as written:**

- **Neither encoding option needed Pillow.** The PNG writer in
  `scripts/catalog_raster.py` is ~30 lines of `struct` + `zlib` from the
  standard library. The `catalog` CI job installs `.[raster,vector]` and
  nothing else, so this phase, like Phase 1, needed **no dependency change** —
  only the new `--check` step in the job.
- **The selector is `expected_shape`, and it covers 17 of the 30 raster
  cases.** The other 13 declare no shape, band count or dtype at all, so they
  had no band-stack schematic to begin with and now still have none. A case
  with metadata but no preview keeps the schematic; the two paths are
  captioned differently, exactly as Phase 1 does for vector.
- **`dem_nan_nodata_small` is not entirely NaN** — 2 of its 256 pixels are.
  That is a better test than the plan assumed: it forces the gate to assert
  the flagged pixels are *distinguishable from* the ramp rather than merely
  present, which is the property that matters.
- **Per-band stretching had to go for the RGB path.** Stretching each of the
  first three bands to its own range rendered `optical_rgb_small` — three
  identical gradients offset by a constant — as pure grayscale, normalizing
  away the exact relative-brightness signal that `incorrect_band_order` cases
  turn on. The three channels now share one span. Single-band previews still
  stretch to their own range, and the caption says "contrast-stretched" rather
  than claiming absolute values.
- **Pre-existing, fixed in passing:** Phase 2's compare-page case links were
  broken. `compare.md` is served at `/catalog/compare/`, its own directory, so
  `href="cases/<id>/"` resolved to `/catalog/compare/cases/<id>/`. The Phase 2
  test only checked that a page with that *basename* existed, so it passed on
  all 135 broken links. Links are now `../cases/<id>/` and
  `test_compare_page_links_resolve` gates the depth, not just the basename.

### 3.1 Decide the encoding first — done, separate PNG files

Real pixels cannot be text. Two options, to be settled before any code:

- **Embedded PNG data-URI in the markdown.** Self-contained, but base64 blobs in a generated file make `--check` diffs unreviewable — the gate degrades to "some bytes changed".
- **PNG files under `docs/_generated/catalog/previews/` referenced by path.** Diffs stay readable (a binary file changed, by name), reviewable per case, and the existing `generate_checksums.py` pattern extends to cover them.

**Settled: separate PNG files**, one per case, written by
`scripts/generate_raster_previews.py`. It preserves the reviewability property
that motivated the text-only constraint originally: a failing `--check` names
the case whose pixels moved. Determinism is what makes that gate meaningful, so
the encoder pins its zlib level and uses filter type 0 on every scanline — a
library default changing underneath us cannot silently rewrite all 17 files.

### 3.2 Failing test, then render — done

Tests in `tests/unit/test_catalog_raster_previews.py`, all watched failing
first (the module did not exist, so collection errored):

- `test_every_shaped_raster_case_has_a_preview` and
  `test_no_previews_for_unshaped_cases` — coverage in both directions, so a
  removed case leaves no orphan PNG behind.
- `test_nodata_renders_off_the_ramp` / `test_valid_pixels_are_not_the_nodata_colour`
  — NoData is magenta, every valid pixel is clamped one step away from the
  channel extremes so real data can never land on it, and the rest of a
  single-band preview stays strictly grayscale.
- `test_small_rasters_are_upscaled_without_blending` — nearest-neighbour by an
  *integer* factor, so no source pixel ends up wider than its neighbours.
- `test_stored_previews_match_a_fresh_render` — the determinism property the
  `--check` gate rests on, asserted in the test suite too rather than only in CI.

Rendering reads through `case.open()` (rasterio) rather than the
`geocase.raster` primitive: the primitive *writes* fixtures, it does not read
the catalog's existing GeoTIFFs. Grayscale ramp lifted off pure black for
single-band, first-three-bands composite for 3+, NoData flagged.

`scripts/catalog_svg.py` gained a `preview_url_provider` mirroring Phase 1's
`geometry_provider`, so raster cases render an `<img>` at their preview when
one exists and fall back to the band-stack schematic when it does not. It
re-checks `expected_shape` itself rather than trusting the provider's URL to
exist — a broken image on a page is worse than an honest schematic.

### 3.3 Gate the artifacts — done

`python scripts/generate_raster_previews.py --check` runs in the `catalog` CI
job right after the catalog-pages gate. `docs/stylesheets/catalog.css` sets
`image-rendering: pixelated` on `.gc-preview` so the browser cannot undo the
nearest-neighbour upscaling with a smooth resample.

---

## Verification

1. `pytest tests/unit/test_catalog_diagrams.py -q` — green, including the new distinctness tests.
2. `python scripts/generate_catalog_pages.py --check` — clean after regeneration.
3. `mkdocs build --strict` — no broken links.
4. `ruff format --check scripts tests && ruff check scripts tests` and `mypy src`.
5. **By eye:** `dateline_crossing_polygon`, `self_intersecting_bowtie`, and `simple_valid_polygon` must be visibly different from one another, and each must look like what its title says. This is the check that actually decides whether the plan worked — the automated tests can only prove the drawings differ, not that they are *right*.
6. Confirm `unclosed_ring_polygon` renders its fallback with the honest caption rather than breaking the build.
7. `python scripts/generate_raster_previews.py --check` — clean after regeneration.
8. **By eye, for Phase 3:** a NoData case must show magenta where the fixture has fill, and a
   multi-band case must not render grayscale. Both were checked by tiling the generated PNGs
   into one image; the grayscale check is what caught the per-band-stretch bug.

**Run 2026-08-28 (conda `geocase`):** `pytest tests -q` 1738 passed / 37 skipped;
both `--check` gates clean; `mkdocs build --strict` clean; `mypy src` clean;
`ruff format --check` and `ruff check` clean on every file this plan touched.
Four pre-existing `ruff` findings remain in `scripts/` (two `I001`, two `E501`,
in `catalog_svg.py` and `validate_case_content.py`) — outside the repo's lint
gate, which covers `src tests`, and untouched here.

## Risks

- **Preview churn on regeneration.** Mitigated by fixed 2-decimal rounding in 1.2; if diffs still churn, the rounding is the first thing to tighten.
- **Generator runtime.** 103 case loads on every docs regeneration. Acceptable at this size; if it bites, cache keyed on the payload checksums that `generate_checksums.py` already maintains.
- **A preview could mislead more than an archetype.** A fit-to-viewport transform normalizes away real scale, so a continent-sized and a metre-sized polygon can render identically. The caption must not overclaim: it says the geometry is real, not that the scale is comparable across cases.
- ~~**Phase 3 weakens the `--check` gate** whichever encoding wins.~~ Resolved by the
  separate-files encoding plus a deterministic encoder: the gate now reports drift *by case
  id*, which is arguably a sharper signal than a line diff inside one large generated file.
  The residual weakness is that a reviewer cannot read what changed without opening the PNG.
- **Raster previews drift with their fixtures.** `generate_raster_fixtures.py` and
  `generate_raster_previews.py` must be regenerated together; the CI job runs both `--check`
  gates, so a mismatch fails rather than shipping a preview of pixels that no longer exist.
