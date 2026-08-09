# Plan 14 — Reposition GeoCase as a geospatial correctness library

> **Status: proposed, and gated.** This plan proposes a change of product direction. If
> adopted, it supersedes the catalog-as-product framing in
> [`development-plan.md`](development-plan.md) and reduces the scope of
> [Plan 13](13-cross-format-canonical-convergence.md); if rejected, both stand unchanged.
>
> **Do not begin Step 1 until Step 0 has run and passed.** Step 0 is a one-day experiment
> that can invalidate this entire plan. It exists because the thesis has been revised twice
> already, each time by relocating where the value sits — a pattern that warrants a
> falsifiable test rather than a third argument.

## Context

Three independent evaluation pilots ran GeoCase against real repositories. They found the
corpus defect recorded in [Plan 13](13-cross-format-canonical-convergence.md) — 54 of 60
`*_baseline` fixtures did not contain the geometry their name promised — and reached a
broader verdict: as a set of static example files GeoCase is well-built but **replaceable by
a committed `tests/fixtures/` directory**.

That verdict is correct, and Plan 13 does not answer it. Plan 13 fixes the corpus; it does
not change what the corpus is worth.

### Why the catalog-as-product thesis fails

A test needs three things: the input, the expected answer, and the code under test.

GeoCase supplies the input. **The input is the cheap part.** A dateline-crossing polygon is
six lines of Shapely and a 2 KB commit — ten minutes, once. Against that, a dependency costs
install, version pins, CI integration, three markers to learn, and a permanent supply-chain
surface. The dependency must beat ten minutes of work, permanently.

The expensive part is the **expected answer**, and a general-purpose catalog structurally
cannot supply it, because "correct" depends on what the consumer's function is meant to do.
For `dateline_crossing_polygon` the right answer differs if you are computing area (split at
the antimeridian), computing bounds (normalise longitude), rendering (handle the wrap), or
reprojecting. GeoCase cannot know which, so it ships the file plus a prose `behavioral_goal`
and leaves the user to write the assertion — at which point they have done 90% of the work.

The codebase already concedes this, and the concession is measurable:

| Claim | Where it lives | Typed? | Executed by `src/`? |
|---|---|---|---|
| "3 uint8 bands, EPSG:4326" | `assertions:` (17 fields) | Yes | **Yes** |
| "Correct UTM is 32633; naive gives 32634" | `params: dict[str, Any]` | No | **No** |
| "Confirm robust Svalbard UTM handling" | `behavioral_goal:` | Prose | **No** |

Enforcement is strongest on the least interesting claim. The only references to
`expected_utm_epsg` under `src/` are in `pytest_plugin/case_diagnostics.py`, which uses the
key *name* to format a test id and never reads the value.

This is also why `sklearn.datasets.load_iris()` succeeds where this does not: those datasets
are inputs to exploration with no correctness claim attached. A *test* corpus lives or dies
on the oracle. (Note that geopandas bundled the Natural Earth datasets and removed them
in 1.0.)

### The corpus defect as disconfirming evidence

The entire value of someone else's corpus is that you do not have to verify it. A corpus that
silently yields fabricated differential results is worth **less than an empty directory** —
the pilot who nearly filed a false cross-format bug report would have been better off with
nothing.

The defect reached `1.0.0rc1` past 727 tests and CI gates on checksums, catalog validity,
generated-page freshness, lint and types. Those tests assert
`case.title == "Simple Valid Polygon"`, `case.primary_exists() is True`, `len(gdf) == 1`,
`crs is not None` — they verify that the YAML loader loads YAML. The quality apparatus was
aimed at **form** (do files hash, do docs regenerate) and never at **substance** (do the
files contain what they claim).

### The proposed fix

**Stop selling the input; sell the answer.** `examples/interview_questions/` already contains
roughly 20 operations in naive and `*_perfect` pairs, with 36 `xfail(strict=True)` entries in
`examples/conftest.py` proving the naive versions fail. Promote the hardened implementations
into `src/` as the product. The 130-case corpus stops being the product and becomes the test
suite that substantiates the correctness claim — the role it was always best at.

**Positioning:** *geospatial operations that don't silently lie to you.* Shapely, pyproj and
rasterio get the primitives right. Nobody owns the composed operations, which is where the
silent failures live.

**Intended outcome:** a public surface of ~13 names that a user adopts with one import,
backed by a corpus whose integrity is load-bearing rather than cosmetic.

---

## Decisions

### Two problems that must be fixed during promotion

Neither is a refactor. Shipping either as-is would reproduce the trust failure this plan
exists to correct.

#### 1. `_looks_geographic` must go — blocking

Every metric function branches on it
(`examples/interview_questions/easy_geospatial_interview_questions.py:13`), guessing from
coordinate *ranges* whether a bare Shapely geometry is in degrees. A projected geometry with
small coordinates is silently treated as lon/lat and reprojected from EPSG:4326.

**That is precisely the class of silent lie the library claims to prevent** — and it would be
ours.

Shapely geometries carry no CRS, so the public API must take it explicitly:

```python
area_m2(geom, crs="EPSG:4326")   # required — no default, no guess
area_m2(gdf)                      # GeoSeries/GeoDataFrame — CRS read from .crs
```

Accept a Shapely geometry plus explicit `crs`, or a GeoSeries/GeoDataFrame. Raise on a bare
geometry with no CRS rather than guessing. Retain the check only as a private short-circuit
*after* the CRS is known (`crs.is_geographic`), where it is a fact rather than a heuristic.

#### 2. `osgeo` must not reach the public API

`clip_raster_perfect`, `pixel_to_world_perfect` and `rasters_aligned_perfect` use
`osgeo.gdal`. `osgeo` is not reliably pip-installable and is the single largest adoption
barrier in Python geospatial.

Reimplement the raster spine on **rasterio**, which is already an optional dependency and
ships wheels. The rotated-geotransform fallback at `clip_raster_perfect:429-446` is real
logic worth keeping — port it (`rasterio.warp.reproject` in place of `gdal.Warp`) rather than
dropping it.

The dependency story improves sharply. Today's `pydantic` + `pyyaml` core exists only to
parse catalog YAML. A function library's core is **shapely + pyproj**, with `rasterio` as a
`[raster]` extra; pydantic and PyYAML become dev-only dependencies of the internal corpus.

### The spine — which functions ship

Promote roughly 12. Selection criterion: does the hardened version differ from the naive one
in a way that costs real money?

| Public name | Source | Why it earns its place |
|---|---|---|
| `area_m2` | `area_m2_perfect` | Equal-area projection; naive returns square degrees |
| `buffer_m` | `buffer_in_meters_perfect` | Dateline unwrap + AEQD; the unwrap at `:178-211` is real work |
| `utm_epsg_for` | `get_utm_epsg_perfect` | Svalbard and SW Norway exceptions (`:241-253`) |
| `bounds` | `get_bbox_perfect` | Antimeridian-safe bounding box |
| `crosses_antimeridian` | `crosses_antimeridian_perfect` | Longitude normalisation |
| `pixel_to_world` | `pixel_to_world_perfect` | Pixel **centre**, not corner |
| `sample_at` | `sample_raster_at_lonlat_perfect` | CRS transform + NoData masking; naive returns `-9999` as data |
| `rasters_aligned` | `rasters_aligned_perfect` | CRS and geotransform comparison with tolerance |
| `cluster_points_m` | `cluster_points_perfect` | Metric threshold, not degrees |
| `find_intersections` | `find_intersections_perfect` | Metric area |
| `dissolve` | `dissolve_polygons_perfect` | Repairs invalid input before union; deterministic ordering |
| `fix_geometry` | `fix_geometry_perfect` | Repair with a validity guarantee |

**Deliberately excluded** — too thin to justify an import, and filler dilutes the correctness
claim: `point_in_polygon`, `reproject_point`, `reproject_geometry`, `detect_null_island`,
`validate_coordinate_bounds`. `clip_raster` and `rasterize_geometries` are deferred to a
second release, pending the rasterio port.

Layout: `src/geocase/vector.py` and `src/geocase/raster.py`, re-exported flat from
`src/geocase/__init__.py`. Flat is correct — `from geocase import area_m2` is the adoption
path.

### What happens to the existing `src/`

**Keep:**

- `assertions/format_compliance.py` (352 LOC) — the most original code in the repository.
  Becomes public as `geocase.formats.check(path, declared_format)`. It currently covers 14 of
  17 `FormatType` values; `GeoTIFF`, `NetCDF` and `Other` raise. Either fill them or document
  the gap.
- `assertions/footprint.py` — the only true golden-file comparator in the package.
- `catalog/`, `cases/`, `loaders/` — **moved to `tests/corpus/`**, not deleted. They are how
  the new library's test suite reaches the 130 cases.

**Remove from the public surface:**

- `pytest_plugin/` (314 LOC), `api/public.py`, `catalog/suites.py`, `catalog/manifests.py`.
  Markers, suites and the auto-parametrising fixture exist only to serve a
  catalog-as-product; keeping them means keeping a compatibility promise on the thing being
  retired.
- The ~21 one-line assertions. `assert_band_count(src, 3)` is `assert src.count == 3` with a
  message; users of a function library do not need it.

This is a large deletion, and that is the point. `tests/unit/test_public_api.py` currently
pins 6 functions and 19 types for a catalog. The new surface is ~12 functions plus
`formats.check`.

### Relationship to Plan 13 — reduced scope, now a precondition

Under this direction the corpus becomes the evidence for every correctness claim the library
makes, so its integrity is load-bearing rather than cosmetic. Plan 13 is therefore a hard
precondition, executed at reduced scope:

- **Execute** Steps 1–7: metadata gate, derive specs from canonical, write backends,
  generalised `--check`, regenerate, `shapefile_ring_orientation` as a named case, and tests.
- **Drop** Step 8's docs, `CHANGELOG` and coverage-matrix work. Internal fixtures need no
  consumer-facing migration note, and there is no longer a 1.0.0 catalog release to protect.
  Keep only the CI install-line change to `-e .[raster,vector] "numpy<2"`.
- Plan 13's Verification step 4 — the negative controls, watching each new gate go red —
  applies unchanged and remains the most important part of it.

### Why the existing test suite must not be trusted

727 tests did not notice that 90% of the flagship fixture family was wrong. `examples/` is
worse, asserting tautologies such as `stats["max"] >= stats["min"]` and `area_sum > 0`.

The new suite must assert **values**, using the oracles already present and unused in
`params`: `expected_utm_epsg`, `expected_footprint`, `expected_cluster_count`,
`expected_bounds`, `max_distance_m`. Roughly 25 such entries exist across the catalog. They
are a specification that was written and never executed — wire them up.

Carry `examples/conftest.py`'s 36 `xfail(strict=True)` entries over as **the regression
suite**: keep the naive implementations in `tests/` as known-bad references and assert that
the library's answer differs from theirs in the documented way. This converts the strongest
asset in the repository from a demo into a permanent guard, and `strict=True` means a naive
implementation that accidentally starts passing fails the build.

---

## Files

**New**

- `src/geocase/vector.py`, `src/geocase/raster.py` — the promoted spine
- `src/geocase/formats.py` — `format_compliance.py` promoted to public
- `tests/regression/` — naive-vs-hardened suite carrying the 36 strict xfails

**Moved**

- `src/geocase/{catalog,cases,loaders}/` → `tests/corpus/`
- `examples/interview_questions/` → source material for the above; naive halves retained
  under `tests/regression/`

**Modified**

- `src/geocase/__init__.py` — new flat surface (~13 names)
- `tests/unit/test_public_api.py` — repinned
- `pyproject.toml` — core deps become `shapely` + `pyproj`; `pydantic`/`pyyaml` move to dev
- `.github/workflows/ci.yml` — install line per Plan 13

**Deleted**

- `src/geocase/pytest_plugin/`, `src/geocase/api/public.py`,
  `src/geocase/catalog/{suites,manifests}.py`, the one-line assertion modules

---

## Traps

1. **The CRS fix is not cosmetic.** Any function that still infers CRS from coordinate ranges
   reintroduces the exact failure mode this plan is built to eliminate. Verify by observation
   (see Verification item 2), not by inspection.
2. **`osgeo` can re-enter through a transitive import.** Verify in a clean virtualenv with no
   `osgeo` installed, not in the development environment.
3. **Plan 13 must land first.** If the fixtures lie, every correctness claim built on them is
   worthless.
4. **Deleting the plugin breaks `examples/`.** Most of that corpus imports
   `geocase.pytest_plugin.case_diagnostics` and `geocase.catalog` directly, bypassing the
   public API, and hard-codes `_REPO_ROOT / "src" / "geocase" / "data" / "core"`. Port what
   moves to `tests/`; do not attempt to keep `examples/` running as-is.
5. **`_test_easy_geospatial_interview_questions_all.py` (2,113 LOC) is uncollectable** — the
   leading underscore means pytest's default glob never sees it. Decide deliberately whether
   it is carried over or dropped; do not discover it mid-migration.

---

## Verification

```bash
# 1. Corpus integrity first (Plan 13), including its negative controls
python scripts/validate_catalog.py && python scripts/build_case_index.py --check
python scripts/generate_vector_fixtures.py --check

# 2. The CRS-guessing bug must be observably gone
python -c "
from shapely.geometry import Point
from geocase import area_m2
area_m2(Point(5,5).buffer(1))             # must RAISE: no CRS supplied
area_m2(Point(5,5).buffer(1), crs=32633)  # must return ~pi, not a degrees-derived number
"

# 3. Value assertions, not tautologies
python -m pytest tests -q
grep -rn "assert .* is not None\|assert len(gdf) == 1" tests/ | wc -l   # should trend to 0

# 4. The naive-vs-hardened regression suite
python -m pytest tests/regression -q     # all 36 strict xfails must still xfail

# 5. Adoption smoke test — in a clean venv with NO osgeo installed
pip install -e ".[raster]" && python -c "from geocase import area_m2, utm_epsg_for, sample_at"

# 6. The surface is actually smaller
python -c "import geocase; print(len(geocase.__all__))"   # ~13, not 25

ruff format --check src tests && ruff check src tests && mypy src
```

Item 5 matters most. If `import geocase` requires `osgeo`, the library is unadoptable however
correct it is.

---

## Explicitly out of scope

- **`geocase doctor`.** Environment probing (missing `proj.db`, absent datum-shift grids,
  deprecated EPSG codes, driver availability) is runtime introspection plus a handful of
  floats and integers — it needs at most a dozen small files and none of the catalog
  machinery. That makes it a separate, small project. Revisit after the library ships.
- **The GDAL/PROJ version matrix.** One version-sensitive result in 27 pilot findings, and a
  perpetual CI grid across releases is a solo-maintainer trap. This answers follow-on
  question 1 of Plan 13 in the negative.
- **Remote dataset transport**, the docs site ([Plan 12](12-docs-site-publication.md)) and
  the PyPI/conda release as currently scoped ([Plan 11](11-distribution-pypi-and-conda.md)) —
  all three describe shipping the catalog as the product.

## Main risk, stated plainly

This is roughly 1,500 lines of utilities, and someone will say "just use pyproj properly."
That is equally true of `dateutil` and `tenacity`. The defence is not the code, it is the
evidence: the corpus and the 36 strict xfails are what make the correctness claim credible.
Which is why Plan 13 comes first — if the fixtures lie, the claim is worthless and this
becomes another utils package.
