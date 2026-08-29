# Plan 33 — Map Identity, Real Geography, and Non-Trivial Geometry

> **Status: implemented 2026-08-29.** All three phases landed. Outcomes measured
> against the defects in Context: the worst 1-degree box now holds **15 of 139**
> placed cases (was 58 of 127), the catalog spans **4 UTM zones** — 32601, 32632,
> 32633, 32756 — (was 1), maximum polygon vertex count is **4097** (was 10), and
> every extent rect on the world maps carries `data-case-id` and a naming
> `<title>`. Catalog grew 136 → 143 cases.
>
> Deviations from the plan, all recorded in the phase sections below:
> `_decimate` lives in `catalog_geometry.py` (re-exported from `catalog_svg`) to
> avoid an import cycle; the dense ring needed a third case
> (`dense_ring_polygon_4k_gpkg`) since a GPKG sibling could not be a transcoding;
> a `_write_geojson` backend had to be added, as nothing previously *wrote*
> GeoJSON; and the plan's ~88 KB size estimate held only after dropping JSON
> indentation. Twelve example-suite nodes moved to strict `xfail` and two
> selectors were narrowed — see Phase 3.

## Context

Reviewing the overview maps on the generated compare page surfaced four defects and two answered questions.

Answers (no work needed): **multi-continent extents** are only 3 of 127 cases, and they are honest bbox arithmetic — `north_pole_polygon`/`south_pole_polygon` are diamonds encircling a pole, so their bbox legitimately spans 180° of longitude. That is correct data rendered misleadingly, which Phase 1 addresses.

Defects to fix:

1. **The map has no identity.** `catalog_svg.py:626-637` draws extent `<rect>`s with no `<title>` and no case id. A reader who sees a footprint cannot find out what it is; only cluster markers carry a prose tooltip.
2. **54% of the catalog sits in one place.** 58 of 127 placed cases fall in a single 1° box at 10E/50N. Cause: 60 vector cases are format-transcodings sharing 6 hand-authored GeoJSON canonicals, all in Thuringia/Copenhagen. The clump is an unexamined default, not a design choice.
3. **One UTM zone.** Only 4 distinct CRSs exist (4326 ×105, 32633 ×24, 3857 ×1, 3995 ×1). Cases *named* for zone behaviour (`geotiff_utm_boundary`, `utm_zone_33_polygon`) all resolve to 33N, so cross-zone reprojection is untested by the bundled catalog.
4. **Geometry is trivial.** Max vertex count in the entire catalog is **10**; 12 canonicals are plain 5-vertex rectangles; max 3 features. Nothing stresses a vertex-dense consumer.

Outcome: a map you can interrogate, a catalog whose cases are actually distributed, and geometry that can fail a real implementation.

**Sequencing.** Phase 1 (map) → Phase 2 (geometry) → Phase 3 (geography). Phase 1 is self-contained and lands the visible win, Phase 2 is additive, and Phase 3 goes last because its regeneration churn is wide — running it after Phase 2 means one sweep rather than two.

---

## Phase 1 — Give the map identity (done)

### 1.1 Tests first — done — `tests/unit/test_catalog_diagrams.py`

- `test_world_map_extent_rects_carry_case_identity` — render `world_map([...dateline_crossing_polygon])`; both split rects carry `data-case-id="dateline_crossing_polygon"` and a `<title>` naming id + title. Identity is per-box, shared across an antimeridian split (`_extent_boxes()` at `catalog_svg.py:526` returns two boxes for one case).
- `test_world_map_marks_pole_caps_distinctly` — `north_pole_polygon`'s rect has `class="gc-map-extent gc-map-polar"` and a `<title>` containing "pole" and "bounding box".
- `test_pole_cap_is_detected_from_extent_not_declared` — `_is_pole_cap(SpatialExtent(west=-90, south=84, east=90, north=89.5))` is True; a same-width equatorial box is False; `dateline_crossing_polygon` is False.
- `test_compare_map_and_table_share_case_ids` — every `data-case-id` inside a `gc-worldmap` SVG in `docs/_generated/catalog/compare.md` also appears as a `<tr data-case-id>`. Guards the JS contract at generation time.

New `tests/unit/test_catalog_compare_js.py`:
- `test_compare_js_binds_map_to_table` — source-text assertions on `docs/javascripts/catalog-compare.js`: references `gc-worldmap`, `caseId`, `scrollIntoView`; contains no `http` URL (the no-CDN constraint from plan 31).

### 1.2 Code — done — `scripts/catalog_svg.py`

- **`_is_pole_cap(extent) -> bool`** — derived predicate, no new schema field: True when the box reaches within `_POLE_CAP_LATITUDE = 5.0°` of ±90 **and** spans ≥ `_POLE_CAP_MIN_SPAN = 120°` of longitude. Deriving beats adding a `pole_cap` field to `case.yaml`: `case.schema.yaml` is gated by strict set equality against `CaseMetadata.model_fields`, and a derived rule cannot drift from the extent it describes. Say so in the docstring.
- **`_extent_title(case, is_cap)`** — `"{id} -- {title} ({region})"`, and for caps append that the band is a bbox artefact of a polygon encircling the pole, not the data's shape.
- **Rewrite the loop at 626-637** to `<g class="gc-map-extent-group" data-case-id="{id}"><title>…</title><rect class="gc-map-extent[ gc-map-polar]" …/></g>`. A group, not rect attributes: `<title>` must be a child element, and grouping keeps a split extent one hoverable unit. Reuse `_map_escape()` (line 662).
- Make the `_MIN_EXTENT_PIXELS` suppression **cap-aware** so a thin high-latitude band is always drawn rather than surviving by luck.
- Marker `<g class="gc-map-marker">` gains `data-case-ids="{space-separated}"` so a cluster can highlight all its rows.

Do **not** reproject or invent coordinates for polar caps. The rect stays geometrically honest; the class and tooltip carry the explanation.

`docs/stylesheets/catalog.css` (extend the block at 267-279): `.gc-map-extent-group { cursor: help }` + hover fill bump; `.gc-map-polar { stroke-dasharray: 3 2; fill-opacity: .18 }`; `tr.gc-row-highlight` using `var(--md-accent-fg-color--transparent)`.

`docs/javascripts/catalog-compare.js` — extend the existing IIFE inside `init()` after `rows` is built, keeping it progressive-enhancement-only:
- `byId` map from `rows` via `row.dataset.caseId`.
- `mouseenter`/`focus` on any `.gc-worldmap [data-case-id]` or `[data-case-ids]` toggles `gc-row-highlight` on the matching row(s).
- `click`: single id → `scrollIntoView({block:"center"})` + highlight. Cluster → set `state.mapFilter = Set(ids)`, have the existing `apply()` also test `!state.mapFilter || state.mapFilter.has(row.dataset.caseId)`, and render a dismissable "Showing N cases from the map — clear" chip beside `gc-compare-count`.
- Set `tabIndex`/`role="button"` from JS, not in the generated SVG, so the committed text stays small.

### 1.3 Regenerate — done

`python scripts/generate_catalog_pages.py` then `--check`; `mkdocs build --strict`. Only `docs/_generated/*` changes — no checksums, extents, or fixtures. Conda env (needs `osgeo`).


**As built.** Followed as written, with one structural change: `_decimate` and
`_MAX_THUMBNAIL_POINTS` live in `catalog_geometry.py`, not `catalog_svg.py`.
`catalog_svg` imports `catalog_geometry` *lazily* inside `_preview_svg`
precisely so it stays dependency-free, so putting the helper in `catalog_svg`
and importing it from `catalog_geometry` would have closed that into a cycle.
It sits with the coordinates it thins and is re-exported from `catalog_svg`
under the same names, so the planned test imports are unchanged.

`_is_pole_cap`'s thresholds were confirmed against the real data rather than
assumed: `north_pole_polygon` is `84.0N-89.5N` over a 180-degree span, which
clears both bounds comfortably.

---

## Phase 2 — Procedural non-trivial geometry (done)

### 2.1 Tests first — done — new `tests/unit/test_generated_geometry.py`

- `test_koch_ring_is_deterministic_across_calls` — two calls, byte-identical WKT; plus a source grep asserting no `random`/`time`/`uuid` import, so determinism is structural.
- `test_koch_ring_vertex_count_matches_the_closed_form` — `sides * 4**depth + 1` coordinates, exactly, for two `(sides, depth)` pairs.
- `test_high_vertex_case_exceeds_two_thousand_vertices` — load the stress case through the registry; `len(geom.exterior.coords) >= 2000` and `geom.is_valid`.
- `test_irregular_polygon_is_not_a_rectangle` — `geom.area / geom.minimum_rotated_rectangle.area < 0.9` and vertex count > 8.
- `test_generated_fixtures_stay_under_the_size_budget` — primary + sidecars under `_MAX_BYTES_NON_SPATIALITE`.
- `test_single_feature_invariant_still_holds_for_canonicals` — `_canonical_geometry()` still raises on a two-feature canonical (locks in that the guard is kept, not loosened).
- `test_thumbnail_decimates_a_dense_geometry` (in `test_catalog_diagrams.py`) — the emitted thumbnail path has < ~300 points regardless of input size.

### 2.2 Code — done — `scripts/generate_vector_fixtures.py`

New section after `_canonical_geometry()` (line ~210), before `_specs()`:

- `_koch_segment(a, b, depth)` / `_koch_ring(sides, depth, radius, centre)` — start from a regular `sides`-gon on a circle of `radius` degrees; each Koch pass replaces `a→b` with `a, a+(b-a)/3, apex, a+2(b-a)/3, b`, apex being the third point rotated 60° outward. Pure `math`. **No `random`, seeded or otherwise** — a PRNG is reproducible only as long as CPython's stream is, and this repo gates on byte-identical regeneration.
- `_dense_parametric_ring(vertices, radius, lobes, amplitude, centre)` — `r(θ) = radius * (1 + amplitude·cos(lobes·θ))` at `vertices` equal steps. `vertices` is an exact dial, so fixture size is chosen rather than discovered.
- Both round to 6 decimals, matching `catalog_extent.py`'s `PRECISION`, so nothing churns on FP noise across platforms.

New cases (own ids, **no** `canonical_source_case_id` and no `cross_format_canonical` tag, so they sit outside the 60-member family):

- `fractal_coastline_polygon` — GeoJSON, `_koch_ring(sides=6, depth=4)` → 1537 coordinates. Tags `irregular_geometry`, `procedural`.
- `dense_ring_polygon_4k` — GeoJSON + a GPKG transcoding so the vertex count is exercised through a driver. `_dense_parametric_ring(vertices=4096, lobes=17, amplitude=0.18)`. At ~22 bytes/pair this is ~88 KB WKT / ~64 KB WKB — comfortably inside `_MAX_BYTES_NON_SPATIALITE`, and the test asserts it rather than trusting the estimate.

**The single-feature invariant is kept, not relaxed.** It scopes the *canonical sources of the transcoding families*, whose purpose is one-to-one comparability — still exactly right. The procedural cases are not canonicals, so the guard never sees them. But `generate_vector_fixtures.py:74` currently claims it of the whole catalog ("Every bundled baseline fixture holds exactly one feature at EPSG:4326"); rescope that sentence to baseline/canonical-family fixtures in the same change, and mirror it in `_canonical_geometry()`'s docstring.

Write them via a new `_write_procedural_cases()` called from `main()`, under the same `--check` semantics (these formats are byte-comparable → strict byte path).

**Also required:** `catalog_svg.py`'s vector thumbnail draws real coordinates, so a 4096-vertex case would emit an enormous `<path>` into `compare.md` and break its text-diffability. Add a decimation stride (or simplification) capped at ~300 points to the vector path, covered by the thumbnail test above.

Register any new tag / risk-type values in whatever vocabulary `scripts/validate_catalog.py` enforces — check before writing.

### 2.3 Regenerate — done

`generate_vector_fixtures.py` → `build_case_index.py` → `catalog_extent.py --write` → `generate_checksums.py` → `validate_catalog.py` + `validate_case_content.py` → `generate_catalog_pages.py` → `generate_vector_coverage_matrix.py --output docs/_generated/vector-coverage-matrix.md`. Then `--check` each. Conda.


**As built.** Three deviations, all forced by things the plan could not see
from outside the generator:

1. **A `_write_geojson` backend was required.** `_write_fixture` had no GeoJSON
   branch at all, because the family's GeoJSON canonicals are hand-authored
   *inputs* -- nothing had ever needed to write the format. Added as a
   pure-Python writer (no driver, so no version or timestamp is stamped in),
   alongside a new `_BYTE_COMPARABLE_FORMATS` set so `--check` byte-compares it
   the way it does WKT/WKB/CSV_WKT.
2. **The dense ring became two cases, not one plus a transcoding.** The plan
   called for "GeoJSON + a GPKG transcoding", but a transcoding is defined by
   `canonical_source_case_id`, and these cases deliberately have none. The GPKG
   is therefore its own procedural case, `dense_ring_polygon_4k_gpkg`, sharing
   one geometry object built once in `_procedural_geometries()`.
3. **The size estimate only held after dropping JSON indentation.** At
   `indent=2` the 4096-vertex GeoJSON came to **315 KB**, well past the 256 KB
   budget -- the plan's ~88 KB figure was for compact WKT. Written with
   `separators=(",", ":")` it lands at 91 KB. The budget test caught this
   rather than the estimate being trusted, which was the point of writing it.

Final sizes: `fractal_coastline_polygon` 32 KB / 1537 vertices,
`dense_ring_polygon_4k` 91 KB / 4097, `dense_ring_polygon_4k_gpkg` 160 KB / 4097.
No tag vocabulary registration was needed -- `tags` and `risk_types` are
`list[str]` with no closed vocabulary in `validate_catalog.py`.

---

## Phase 3 — Spread the geography (done)

**Recommendation: relocate 5 of the 6 canonicals, and add 4 UTM cases.** Relocating is the only thing that fixes the map — 60 placed cases inherit position from those 6 files, so adding new cases leaves the 58-case dot exactly where it is. The churn is large but bounded and fully mechanical: every downstream artefact is produced by a gated generator. It would be the wrong call if a test asserted a coordinate literal; `_specs()`'s docstring already records by grep that none does, and the two near-misses are named below.

Keep `simple_valid_polygon` at 10E/50N: it carries `params.expected_bounds`, is the JSON-LD example asserted at `tests/unit/test_catalog_diagrams.py:338`, and is cited across the docs. Moving five of six breaks the clump; moving the sixth costs doc churn for no map gain.

### 3.1 Tests first — done — new `tests/unit/test_catalog_geography.py`

- `test_canonical_sources_are_geographically_distinct` — pairwise degree separation between the 6 canonical extents > 20°. Fails today at 0°.
- `test_no_single_degree_box_holds_more_than_a_fifth_of_the_catalog` — bucket placed centroids into 1° boxes; `max(count) <= len(placed) // 5`. Fails today at 58/127.
- `test_catalog_covers_multiple_utm_zones` — ≥ 4 distinct UTM EPSG codes, including a southern-hemisphere `327xx` and an adjacent pair. Fails today (only 32633).
- `test_a_case_straddles_a_utm_zone_boundary` — a case whose extent crosses a 6°-multiple meridian while declaring a single UTM CRS, tagged `utm_zone_boundary`.

### 3.2 Data changes — done

Edit the **6 hand-authored canonical GeoJSON files only** — `_canonical_geometry()` needs no change, since it dereferences whatever is on disk. Shape and vertex count stay identical; only the origin moves.

| canonical | new locale | approx | region |
|---|---|---|---|
| `simple_valid_polygon` | unchanged (Thuringia) | 10–11E / 50–51N | Central Europe |
| `simple_valid_point` | Wellington | 174.78E / 41.29S | New Zealand |
| `simple_valid_linestring` | Patagonia | 72.5W / 50.9S | Southern Andes |
| `simple_valid_multipoint` | Hokkaido | 142.4E / 43.1N | Northern Japan |
| `simple_valid_multilinestring` | Great Rift Valley | 36.1E / 0.5S | East Africa (equator) |
| `simple_valid_multipolygon` | Nunavut | 96W / 68N | Canadian Arctic |

Update each case's hand-written `region:` to match, and any `params.expected_bounds` on a moved canonical (`tests/unit/test_catalog_extent.py:45` compares against that param, so it stays green if the param moves with the data).

Four new UTM cases, each `case.yaml` + payload + `checksums.sha256` + `notes.md` per `docs/adding-a-case.md`:

1. `utm_zone_1n_small` — EPSG:32601, hard against the antimeridian; pairs with the existing dateline cases.
2. `utm_zone_56s_small` — EPSG:32756, Sydney; exercises the 10 000 000 m false northing.
3. `utm_zone_boundary_straddle` — polygon spanning 5.5E–6.5E declared EPSG:32632, extending past its own zone's eastern edge. Tag `utm_zone_boundary`, risk `utm_zone_mismatch`. This is the case that makes cross-zone reprojection testable.
4. `utm_zone_33n_to_32n_pair` — the same geometry recorded in adjacent zones, so a consumer can assert round-trip agreement within tolerance.

### 3.3 Regenerate — done — full blast radius, in order

```
python scripts/generate_vector_fixtures.py          # ~60 transcodings rewritten
python scripts/generate_raster_fixtures.py          # if any UTM case is raster
python scripts/build_case_index.py
python scripts/catalog_extent.py --write
python scripts/generate_checksums.py
python scripts/validate_catalog.py
python scripts/validate_case_content.py
python scripts/generate_catalog_pages.py
python scripts/generate_raster_previews.py
python scripts/generate_vector_coverage_matrix.py --output docs/_generated/vector-coverage-matrix.md
python scripts/generate_raster_coverage_matrix.py --output docs/_generated/raster-coverage-matrix.md
```

Expect ~60 fixture binaries, ~66 `case.yaml` extents, 60+ checksum files, every catalog page, both matrices, and the compare page to change.

**As built.** The five relocations and four UTM cases landed as planned. The
new UTM payloads hold **real projected coordinates**, computed with `pyproj`
rather than invented, so `utm_zone_1n_small` and `utm_zone_56s_small` genuinely
carry EPSG:32601/32756 eastings and northings (the 56S northings are ~6.26M,
exercising the 10 000 000 m false northing) and the 33N/32N pair records a
true ~412 km easting difference for one ground footprint.

Two things the plan did not anticipate, both consequences of the relocation
rather than defects in it:

- **~60 transcodings carried their own hand-written `region:`.** They inherit
  *geometry* from a canonical but not metadata, so every one still said
  "Central Europe" after the move. Synced by a one-shot script (60 files across
  two passes) so each transcoding's region matches its canonical's.
- **13 example-suite nodes failed.** Twelve are the *simple* (deliberately
  naive) implementations meeting a projected CRS -- the exact limitation the
  existing `epsg32633-rasterization-utm` entries already record, now reached by
  three more zones; they were added to `_SIMPLE_EXPECTED_FAILURES` as strict
  xfails, so they are verified to fail for the stated reason. The thirteenth
  was real: `_utm_polygon_case()` and the `get_utm_epsg` loops assumed every
  WGS84 `utm`-tagged polygon has one correct zone and a
  `params.expected_utm_epsg`. `utm_zone_33n_to_32n_pair` has neither by design,
  so those selectors now skip `utm_zone_boundary`-tagged cases -- asking a
  zone-selection helper for "the" zone of a boundary-straddling case is a
  malformed question, not a gap in the helper.

`test_a_case_straddles_a_utm_zone_boundary` was also relaxed in one respect
during implementation: it now requires *at least one* `utm_zone_boundary` case
to declare a single UTM CRS, rather than all of them. The pair case is stored
in WGS84 on purpose -- a GeoJSON FeatureCollection has one CRS, and storing its
two features projected would need two files and destroy the direct
comparability that is the case's entire purpose.

Case count went 136 → 143 (2 procedural + 1 GPKG sibling + 4 UTM), which
required updating twelve documented case-count claims across `README.md`,
`docs/`, and `recipe/meta.yaml` to keep `validate_catalog.py` green.



---

## Verification

Per phase, then once at the end — all under **conda `geocase`** (`osgeo` required; without it ~1200 tests silently skip):

```bash
pytest tests -q
pytest examples -q
ruff format --check src tests && ruff check src tests
mypy src
mkdocs build --strict
```

Then every catalog gate in `--check` form (the block in CLAUDE.md). A clean `--check` sweep with a clean `git status` is the pass condition — any drift means a generator was skipped.

Visual check: `mkdocs serve`, open `/catalog/compare/`, and confirm (a) hovering a footprint names its case and highlights its row, (b) clicking a cluster filters the table and the chip clears it, (c) the polar caps read as dashed/provisional with an explaining tooltip, (d) the markers are spread across continents rather than stacked on Germany, (e) `fractal_coastline_polygon` and `dense_ring_polygon_4k` render as recognisably irregular thumbnails without bloating the page.

Also re-run `python scripts/generate_catalog_pages.py --check` after `mkdocs build` to confirm the build did not mutate generated pages.
