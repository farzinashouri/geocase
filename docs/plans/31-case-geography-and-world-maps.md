# Plan 31 — Case Geography: Extents, Region Labels, and World Maps

> **Status: implemented 2026-08-28.** All four phases landed. Three things
> turned out differently from the plan; each is noted inline below.

## Context

The catalog's whole premise is *realistic geospatial edge cases*, but nothing in the docs says **where on Earth a case is**. A reader looking at `dateline_crossing_polygon` cannot tell from the page that it straddles 180°; a reader looking at a polar case sees no indication it is polar. The one spatial signal published today is a bare CRS string — [`_attribute_rows()`](https://github.com/farzinashouri/geocase/blob/main/scripts/generate_catalog_pages.py#L165) emits a CRS row, `_badges()` a CRS chip, and `_json_ld()` maps it into a thin `spatialCoverage.Place` carrying a `coordinateReferenceSystem` property and nothing else. **CRS is a coordinate convention, not a location.**

Two asks:

1. **Per case**: say where in the world it is.
2. **On the compare page**: a world map showing roughly where the data lives — with separate vector and raster maps, because the cases overlap.

### What I verified in this tree

- **`CaseMetadata` has no spatial extent field at all** — no `bbox`, `extent`, `centroid`, `region`, or `location` ([`models.py:139-176`](https://github.com/farzinashouri/geocase/blob/main/src/geocase/catalog/models.py#L139-L176)). The only geographic-ish fields are `crs: str | None` and `assertions.expected_epsg`. Exactly one case carries bounds, informally, in its free-form `params`: `simple_valid_polygon.params.expected_bounds: [10.0, 50.0, 11.0, 51.0]`.
- **All 130 bundled cases declare a CRS**, so every case has a resolvable Earth location. Distribution: `EPSG:4326` ×105, `EPSG:32633` ×23, `EPSG:3857` ×1 (`web_mercator_baseline`), `EPSG:3995` ×1 (Arctic polar stereographic). There is no local-engineering or unspecified CRS, so **no "synthetic / nowhere" escape hatch is needed**.
- **Raster metadata cannot yield an extent.** Raster `case.yaml` carries `expected_shape` (pixel dimensions) and `crs`, but no transform or origin — the bbox must be read from the bytes (`src.bounds`). Vector likewise needs `gdf.total_bounds`.
- **The `catalog` CI job can already do this.** It installs `-e .[raster,vector]` ([`ci.yml:137`](https://github.com/farzinashouri/geocase/blob/main/.github/workflows/ci.yml#L137)) — geopandas, shapely, pyarrow, rasterio, and pyproj transitively — and it is the job that already runs `generate_catalog_pages.py --check`. **No CI change is required.** The `docs` job only runs `mkdocs build --strict` over already-written markdown and never invokes the generator.
- **Most fixtures cluster at shared synthetic origins.** 23 rasters share one transform, `from_origin(500000, 4500000, 10, 10)` in UTM 33N ([`generate_raster_fixtures.py:41-42`](https://github.com/farzinashouri/geocase/blob/main/scripts/generate_raster_fixtures.py#L41-L42)) — that is roughly 15°E, 40.6°N, southern Italy. Vector baselines sit at 10-11°E / 50-51°N (Germany), the KML fixture at 12.5°E / 55.7°N (Copenhagen). **The maps must handle heavy overlap by design.** This is the stated reason for splitting vector and raster, and it also forces marker clustering with counts.
- **The dateline cases genuinely differ**: `dateline_crossing_polygon` spans 170→190°E. A naive `total_bounds` gives a wrong, world-spanning bbox for antimeridian crossers. Prior art for the correct convention already exists in the repo — [`benchmark/tasks/geojson_bounds/grader.py`](https://github.com/farzinashouri/geocase/blob/main/src/geocase/benchmark/tasks/geojson_bounds/grader.py) uses the `min_lon > max_lon` wrap convention.
- **The schema YAML is gated by strict set equality.** [`case.schema.yaml`](https://github.com/farzinashouri/geocase/blob/main/src/geocase/metadata/schemas/case.schema.yaml) is documentation nothing reads at runtime, but `test_top_level_properties_match_case_metadata_fields` asserts `set(schema["properties"]) == set(CaseMetadata.model_fields)`. Adding a model field **without** updating the schema is an immediate test failure.
- **[`catalog_svg.py`](https://github.com/farzinashouri/geocase/blob/main/scripts/catalog_svg.py) is already the dependency-free inline-SVG emitter**, with a projector, `_polyline`, theme-variable styling, and a `test_schematics_use_theme_variables_not_hex` gate. A world map is an extension of it, not new machinery.
- `unclosed_ring_polygon` cannot load (deliberately malformed), and `MAX_VECTOR_FALLBACKS = 10` guards against mass-fallback. Extent extraction must tolerate load failure the same way [Plan 29](29-real-geometry-previews-and-compare-page.md) does.

### Intended outcome

1. Every case page states where it is: a WGS84 extent plus a human-readable region.
2. The compare page carries **two** world maps — one vector, one raster — plotting roughly where the data sits, with overlap made legible rather than hidden.
3. The `--check` text-diff property survives: maps are generated inline SVG, stored as text.

### Non-goals

- No interactive/slippy map, no tile basemap, no CDN. The docs build ships no bundler and no external JavaScript; preserving that is worth more than pan-and-zoom.
- No reprojection beyond "to EPSG:4326 for display".
- No change to case ids, the pytest fixture surface, or anything else in the v1.0 compatibility promise. Both new fields are **optional**, so `import geocase` stays backward compatible.

### Decisions taken

| Question | Decision |
|---|---|
| Where does location come from? | **Computed bbox + optional hand-written region label.** The extent is derived from the real bytes so it cannot drift; `region:` is an optional editorial string in `case.yaml`. |
| How is the map rendered? | **Generated inline SVG**, extending `scripts/catalog_svg.py`. Text-diffable, no CDN, works with JavaScript off. |
| Where does location go on a case page? | **A row in the existing `_attribute_rows()` table.** No per-case locator map. |

---

## Phase 1 — The extent model and the region label

### 1.1 Failing test: `CaseMetadata` accepts an extent and a region -- **done**

In [`tests/unit/test_case_models.py`](https://github.com/farzinashouri/geocase/blob/main/tests/unit/test_case_models.py), add to the `CaseMetadata` test class:

- a case constructed with `extent: {"west": 10.0, "south": 50.0, "east": 11.0, "north": 51.0}` and `region: "Central Europe (synthetic)"` round-trips;
- a case with neither still validates — the fields are optional, and 130 existing files must keep parsing;
- an extent with `north < south` is rejected;
- an extent with longitude outside [-180, 180] or latitude outside [-90, 90] is rejected;
- **`west > east` is accepted** and means an antimeridian crossing. Document this in the field docstring; it is the `geojson_bounds` grader convention.

Run and watch these fail.

### 1.2 Add `SpatialExtent` and the two fields -- **done**

In [`src/geocase/catalog/models.py`](https://github.com/farzinashouri/geocase/blob/main/src/geocase/catalog/models.py), add a nested model alongside `SourceInfo`/`RemoteInfo`:

```python
class SpatialExtent(BaseModel):
    """WGS84 bounding box. ``west > east`` means the box crosses the antimeridian."""

    west: float
    south: float
    east: float
    north: float
```

with field validators for the coordinate ranges and `north >= south`. Then on `CaseMetadata`, next to `crs` (line 159):

```python
    extent: SpatialExtent | None = None
    region: str | None = None
```

Export `SpatialExtent` wherever `CaseMetadata` is exported so the public surface stays coherent.

### 1.3 Update the schema YAML in lockstep — required -- **done**

Add `extent` (an object with the four numeric properties) and `region` (a string) to `properties` in [`case.schema.yaml`](https://github.com/farzinashouri/geocase/blob/main/src/geocase/metadata/schemas/case.schema.yaml). Without this, `test_top_level_properties_match_case_metadata_fields` fails on the strict set comparison.

### 1.4 Metadata-only validation -- **done**

In [`scripts/validate_catalog.py`](https://github.com/farzinashouri/geocase/blob/main/scripts/validate_catalog.py) — which must stay reader-dependency-free — add a check that any declared `extent` is in range and internally consistent. It opens no data file; comparison against real bytes is Phase 2.

---

## Phase 2 — Compute extents from the real data and populate the catalog

### 2.1 Failing test: extent extraction -- **done**

New `tests/unit/test_catalog_extent.py`:

- a vector case returns its known bbox — `simple_valid_polygon` → `(10.0, 50.0, 11.0, 51.0)`, which its own `params.expected_bounds` already asserts;
- a UTM raster reprojects to plausible WGS84 lon/lat (roughly 15°E, 40.6°N for the shared `EPSG:32633` transform) rather than returning metres;
- `dateline_crossing_polygon` yields a **wrapped** box (`west=170`, `east=-170`, i.e. `west > east`), not a world-spanning one;
- an unloadable case (`unclosed_ring_polygon`) returns `None` without raising.

### 2.2 New helper: `scripts/catalog_extent.py` -- **done**

A sibling to the existing [`catalog_geometry.py`](https://github.com/farzinashouri/geocase/blob/main/scripts/catalog_geometry.py) / [`catalog_raster.py`](https://github.com/farzinashouri/geocase/blob/main/scripts/catalog_raster.py) helpers, following their conventions: lazy imports, swallow load errors, and round to a fixed precision so generated pages do not churn on floating-point noise (`catalog_geometry.PRECISION = 2` sets the precedent).

- `case_extent(case) -> SpatialExtent | None`, dispatching on `case.category`.
- **Vector**: go through `geocase.load_case(id).load()` and `gdf.total_bounds`, then `gdf.to_crs(4326)` when needed. **Not** bare `geopandas.read_file()` — Plan 29 established that reaches only 78 of 104 cases; the WKB/WKT/CSV_WKT/Arrow families need `VectorCase.load()`.
- **Raster**: `rasterio.open(...)`, `src.bounds`, then `rasterio.warp.transform_bounds(src.crs, "EPSG:4326", *src.bounds)`.
- **NetCDF**: skipped, consistent with [`content.py`](https://github.com/farzinashouri/geocase/blob/main/src/geocase/catalog/content.py) — xarray is not in the catalog CI install set. The single netcdf case declares `EPSG:4326` and can take a hand-written `region` only.
- **Antimeridian handling**: when a geometry's longitudes span more than 180°, emit the wrapped box rather than the naive envelope. Reuse the convention (not necessarily the code) from the `geojson_bounds` grader.

### 2.3 Populate `extent:` across the catalog -- **done**

Extend [`scripts/build_case_index.py`](https://github.com/farzinashouri/geocase/blob/main/scripts/build_case_index.py) — or add a small `--write-extents` mode to the new helper — to compute and write `extent:` into each `case.yaml`, then run it once. Because it is computed, this stays regenerable rather than hand-maintained.

Hand-write `region:` per case as an editorial pass — short, and honest about synthetic placement: `"Central Europe (synthetic)"`, `"Antimeridian, North Pacific"`, `"Arctic"`. Where no meaningful region applies, leave it unset and let the page fall back to the extent alone.

### 2.4 Content gate: declared extent vs. real bytes -- **done**

In [`src/geocase/catalog/content.py`](https://github.com/farzinashouri/geocase/blob/main/src/geocase/catalog/content.py), add a check comparing a declared `extent` against the computed one within a tolerance, collected through the existing `_collect()` pattern. Per that module's design constraint — *the gate and the user-facing check are the same code* — add a matching `assert_extent` / `assert_bounds` helper under [`src/geocase/assertions/`](https://github.com/farzinashouri/geocase/blob/main/src/geocase/assertions/) and export it from `assertions/__init__.py`. There is no bbox assertion today; [`footprint.py`](https://github.com/farzinashouri/geocase/blob/main/src/geocase/assertions/footprint.py) operates only on a caller-supplied GeoDataFrame.

---

## Phase 3 — Surface geography in the generated pages

### 3.1 Failing test: pages show location -- **done**

Extend [`tests/unit/test_catalog_diagrams.py`](https://github.com/farzinashouri/geocase/blob/main/tests/unit/test_catalog_diagrams.py), the page-content gate:

- a case page's attribute table contains an extent/region row;
- the compare page contains both a vector map and a raster map, each carrying markers;
- the maps use theme CSS variables, not hex literals — the existing `test_schematics_use_theme_variables_not_hex` rule extends to them.

### 3.2 Per-case pages -- **done**

In [`scripts/generate_catalog_pages.py`](https://github.com/farzinashouri/geocase/blob/main/scripts/generate_catalog_pages.py), add a **Location** row to `_attribute_rows()` (line 165): the `region` when set, followed by the formatted extent (e.g. `10.00°E, 50.00°N → 11.00°E, 51.00°N`), with an explicit note when the box wraps the antimeridian.

Also upgrade `_json_ld()` (lines ~340-348): replace the thin `spatialCoverage.Place` with a real `Place` carrying a `GeoShape` `box`. This is the SEO payoff — schema.org understands a box, and today it understands nothing about our geography.

### 3.3 Two world maps on the compare page -- **done**

Add to [`scripts/catalog_svg.py`](https://github.com/farzinashouri/geocase/blob/main/scripts/catalog_svg.py) a `world_map(cases, title)` emitting an equirectangular (plate carrée) SVG:

- A **coarse, hand-embedded continental outline** as a module constant — a low-vertex path set, a few hundred points total, so the file stays reviewable and the module stays dependency-free, which is its existing constraint. Graticule lines every 30°, plus a marked antimeridian, since the catalog cares about it.
- Linear lon/lat → viewport projection; equirectangular needs no math beyond a scale. Reuse the `_Projector` pattern already in `catalog_geometry.py`.
- One marker per case at its extent centroid; extents wide enough to be visible drawn as rectangles instead. **Cluster co-located cases** — markers within a few pixels collapse into one marker with a count badge. This is the direct answer to the overlap problem.
- Antimeridian-wrapping extents drawn as two rectangles, one against each edge.
- Styling via the theme CSS variables already in [`docs/stylesheets/catalog.css`](https://github.com/farzinashouri/geocase/blob/main/docs/stylesheets/catalog.css), so both light and dark palettes work.

In `_render_compare_page()` (line 570), insert a section above the controls holding two maps — **Vector coverage** and **Raster coverage** — built by filtering `cases` on `category`. Separate maps, because a single map would pile all 130 markers onto two synthetic points.

Optionally wire the markers to the filter JS in [`docs/javascripts/catalog-compare.js`](https://github.com/farzinashouri/geocase/blob/main/docs/javascripts/catalog-compare.js) so clicking a marker filters the table. The page must remain fully readable with JavaScript off, as that file's docstring requires.

### 3.4 Regenerate every artifact -- **done**

```bash
python scripts/build_case_index.py
python scripts/generate_catalog_pages.py
python scripts/generate_raster_previews.py
```

All ~187 generated pages change; `--check` fails in CI otherwise.

---

## Phase 4 — Docs and bookkeeping

- [`docs/adding-a-case.md`](../adding-a-case.md) — document `extent` (computed, regenerable) and `region` (hand-written, optional).
- [`docs/assertions-reference.md`](../assertions-reference.md) — the new bbox assertion.
- [`CLAUDE.md`](https://github.com/farzinashouri/geocase/blob/main/CLAUDE.md) — add any new generator command to the catalog-gates block.
- Flip this document's `Status:` to `implemented YYYY-MM-DD` and mark each `### N.M` done as it lands; update the row in [`index.md`](index.md).

---

## What actually landed

**Coverage.** 132 of 135 cases resolve an extent; 135 of 135 carry a hand-written
`region`. The four without an extent are the honest cases: `empty_polygon` (no
geometry), `unclosed_ring_polygon` (deliberately malformed), `latlon_small`
(netcdf, out of scope), and `out_of_bounds_coordinates`.

**Three departures from the plan:**

1. **`out_of_bounds_coordinates` gets no extent, and that is a finding the plan
   did not anticipate.** Its point sits at latitude 100, outside the WGS84
   domain entirely. The first implementation clamped latitudes into range,
   which published a plausible-looking box for data whose whole purpose is
   having no valid position -- precisely the false green light this catalog
   exists to remove. `catalog_extent.py` now refuses rather than clamps, and
   `--write` *removes* a stale block when a case stops being placeable.

2. **`validate_catalog.py` does not reject a zero-area extent.** The plan's
   "internally consistent" check first flagged 14 point baselines as
   degenerate. A single-point case legitimately has zero width and zero
   height; only a negative span is impossible. The near-global-without-a-wrap
   check, which catches the naive-`total_bounds` bug, is the rule that earns
   its place.

3. **Case YAML is not always `case.yaml`.** `raster/footprint_edge_cases/`
   holds five cases in one directory as `case_<id>.yaml`, so the writer
   resolves paths through the case index rather than by convention; the naive
   form silently skipped all five.

**Also done, beyond the plan:** `python scripts/catalog_extent.py --check` was
added to the `catalog` CI job. The plan established no CI change was *required*
for the reader dependencies, but the new generated field needs a gate like
every other one, or an extent can drift from its data unnoticed.

**Coastline provenance:** the `_COASTLINE` constant in `catalog_svg.py` is 11
rings / ~460 points, derived once from Natural Earth 110m (public domain),
simplified to ~1.2 degrees and embedded as data. Nothing is fetched at build or
render time; the module stays dependency-free.

**Clustering, measured:** 101 placed vector cases collapse to 18 markers
(largest cluster 60); 30 rasters to 8 markers (largest 16). Every case is
accounted for in exactly one cluster and none falls outside the viewport.

The optional marker-to-filter JS wiring in 3.3 was **not** built. The maps are
static SVG and the page is fully readable with JavaScript off, which was the
binding requirement; the interaction was explicitly optional.

---

## Verification

Run under the conda `geocase` environment — the only one with `osgeo`, which the catalog gates need:

```bash
# Unit tests first -- each phase's tests should fail before its code lands
pytest tests/unit/test_case_models.py tests/unit/test_catalog_extent.py \
       tests/unit/test_catalog_diagrams.py tests/unit/test_case_content.py -q

# Full suite
pytest tests -q

# Catalog gates -- these are what CI runs
python scripts/build_case_index.py --check
python scripts/validate_catalog.py
python scripts/validate_case_content.py
python scripts/generate_catalog_pages.py --check
python scripts/generate_raster_previews.py --check

# Lint / typecheck (catalog.* and api.* are strict under mypy)
ruff format --check src tests && ruff check src tests
mypy src

# Docs build -- broken internal links fail the build
mkdocs build --strict
```

**Manual checks that matter:**

1. Open `site/_generated/catalog/compare/` and confirm two maps render, that the continents are recognizable, and that the ~23 co-located UTM rasters show as one clustered marker with a count rather than 23 stacked dots.
2. Toggle the docs dark/light palette and confirm both maps stay legible — theme variables, not hex.
3. Open `site/_generated/catalog/cases/dateline_crossing_polygon/` and confirm the extent reads as a wrapped box (170°E → -170°E), *not* -180→180, and that the map draws it as two edge rectangles.
4. Open the polar case's page and confirm it is placed at the top of the map, not clipped away.
5. Disable JavaScript and reload the compare page — the maps and the full table must still render.
6. Confirm `simple_valid_polygon`'s generated extent matches the `params.expected_bounds` it has always declared.
