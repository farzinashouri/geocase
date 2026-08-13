# Plan 14 — Reposition GeoCase as a geospatial correctness library

> **Status: REJECTED — Step 0 ran on 2026-08-09 and hit the Stop row.** Ten fresh coding
> agents given the neutral prompts got **9 of 10 operations fully correct**, including
> Svalbard/Norway UTM exceptions, the NoData sentinel, the TMS row flip, the donut label
> point, Voronoi cell ordering, and dateline clustering/length/interpolation. The single
> reproducible silent failure (2/2 independent trials) was `buffer_m` across the
> antimeridian — an invalid bowtie both agents' own tests missed. Per the decision rule
> fixed in advance below, the library is redundant; do not begin Step 1. Harness,
> verbatim prompts, generated code, and full table:
> `tests/benchmark/agent_baseline/RESULTS.md`.
> Also recorded there: the prior-art table below is wrong about pyproj —
> `query_utm_crs_info` does **not** encode the Norway/Svalbard exceptions. Salvage path:
> publish the benchmark write-up, upstream the `buffer_m` finding, keep
> `format_compliance.py` and the corpus per the "if rejected" path.
>
> **That salvage path is now [Plan 15](15-geocase-as-benchmark.md),** which promotes the Step 0
> harness from a gate artifact to the product. Note that Plan 15 is not a fourth home for this
> plan's thesis — it abandons the library entirely and keeps only the instrument, whose value
> rises rather than falls as models improve.
>
> *Original header follows.*
>
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

**Intended outcome:** a public surface of ~8–10 names (Tier 1 after the prior-art screen),
rising to ~15 if every surviving Tier 2 candidate lands, adopted with one import and backed
by a corpus whose integrity is load-bearing rather than cosmetic.

### The agentic-AI objection, and what survives it

GeoCase is expected to be used alongside coding agents. That materially weakens part of this
plan and must be stated before the plan is adopted, not discovered after.

**What it kills.** The discovery and teaching value is largely gone. "Here are 130 curated
edge cases so you know what to test for" was in part a *knowledge* product, and a model asked
"what breaks in geospatial code?" will name the dateline, UTM zone exceptions, NoData
sentinels, pixel-centre-vs-corner and degrees-vs-metres immediately. The same applies to the
interview corpus as teaching material. Any residual "browse the catalog to discover edge
cases" framing should be dropped outright.

**What it does not kill.** Knowing a trap exists and reliably avoiding it are different
things, and the gap between them is where this library lives. A model asked to write
`area_m2` will usually produce something plausible — and a *different* plausible
implementation next week, in the next repository, none of them run against a polygon spanning
the antimeridian. `buffer_in_meters_perfect` is the evidence: the unwrap → project → buffer →
rewrap sequence at `:178-211` is not reliably reproduced on demand, and its failure mode is
silent. The output is a valid polygon in the wrong place. Nothing raises, and a reviewer
skimming a generated diff sees plausible code.

So the pitch shifts from **"you didn't know"** to **"this is settled, verified, and identical
everywhere."** That is a weaker claim, and it is also the claim behind most successful small
libraries — nobody adopts `tenacity` because retry logic is mysterious.

**What it strengthens.** Agents produce more code, faster, with less line-by-line review.
That systematically increases the number of plausible-looking, silently-wrong
implementations in circulation. A callable verified function is the direct mitigation:
`from geocase import area_m2` is one line an agent can emit and a reviewer can trust, against
forty lines nobody checks. On this argument agents make the library *more* valuable — but
only if it is trivially discoverable and demonstrably correct, which raises rather than
lowers the stakes on corpus integrity and on Plan 13.

**What is unaffected.** Anything depending on facts a model cannot have. `geocase doctor` is
the clearest case: no amount of reasoning reveals whether *this* machine's `proj.db` is
missing its grids. The corpus-as-evidence role also survives intact — an agent can generate a
fixture, but not a *verified* one, and Plan 13's central lesson is that unverified fixtures
are worse than none.

This reasoning is plausible and unproven. Step 0 tests it.

---

## Step 0 — Falsify the thesis before building anything

**Gate. One day. Blocks every other step.**

The thesis reduces to one testable claim: *a competent coding agent, given a plain
description and no hint that edge cases exist, produces geospatial code that fails at the
edges.* If false, this library is redundant and the correct answer is to stop.

Procedure:

1. Take 8–10 operations from the spine below, drawing from **both tiers** — Tier 1 to
   validate the port, Tier 2 to decide whether to write it at all. At minimum: `buffer_m`
   across the dateline, `utm_epsg_for` at Svalbard, `sample_at` against a NoData sentinel,
   `area_m2` on an antimeridian-spanning polygon, `representative_point` on a donut, and the
   XYZ/TMS tile flip. Operations the prior-art screen (see the spine section) already
   excludes from promotion — the last two among them — stay in the run anyway: for those the
   result measures whether an agent *finds* the settled answer unprompted, which is
   benchmark material even though no function will ship.
2. Prompt a current coding agent to implement each from a neutral description. **No mention
   of edge cases, no mention of GeoCase, no mention of the traps.** Record the prompts
   verbatim so the run is reproducible.
   **Do not reuse the handbook's question text as prompts** — its `## Probing` sections name
   the trap outright, which measures whether an agent can be *told*, not whether it gets
   there unprompted. Only the latter justifies the library. Strip each to a neutral task
   statement and check the phrasing does not leak the hint.
3. Run each generated implementation against the corresponding corpus cases, using the
   `params` oracles (`expected_utm_epsg`, `expected_bounds`, `max_distance_m`, …).
4. Record pass/fail per operation, and whether each failure is silent (plausible wrong
   answer) or loud (exception).
5. Record the prior-art column from the spine survey alongside each result. The decision
   rule below applies only to operations that survive the prior-art screen — an operation
   with a settled owner is excluded whatever the agent did with it, because the remedy for
   a fumbled operation with prior art is a citation, not a fork.

Decision rule, fixed in advance:

| Result | Action |
|---|---|
| Agent passes **most** operations | **Stop.** The library is redundant. Archive per the "if rejected" path and keep `format_compliance.py` and the corpus. |
| Agent produces the naive implementation **most of the time** | Proceed to Step 1 — and the run itself is now a reproducible benchmark showing agent-written geospatial code fails at the edges. That is simultaneously the justification and the marketing. |
| Mixed | Promote only the operations the agent got wrong. The ones it reliably gets right do not need shipping. |

Note the asymmetry: the mixed outcome is the most likely, and it is *useful* — it converts
the spine table below from an intuition-ranked list into a demand-ranked one.

Store the harness under `tests/benchmark/agent_baseline/` and the results in a committed
markdown table. Silent failures are the headline number, not the raw pass rate: a loud
failure is one an agent's own test run would catch, and does not justify a dependency.

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

**Scope boundary.** This library covers only operations where the obvious implementation is
*silently* wrong — it returns a plausible value that is not the right one. That set is
genuinely small, perhaps 20–30 across the whole domain, because most geospatial operations
either fail loudly or have no trap at all. `polygon.contains(point)` is simply correct;
`polygon.area` is a trap. A loud failure does not justify a dependency, because the caller's
own test run catches it. This is a supplement to shapely/pyproj/rasterio, never a platform,
and marketing it as the latter fails.

Promote roughly 8–15. Selection criteria, **both** required: does the naive implementation
return a plausible-looking wrong answer, and does no maintained package or
shapely/pyproj/rasterio one-liner already own the correct one?

#### Evidence base — the trap survey is already done

An earlier draft called this list "intuition-ranked" and proposed surveying GIS StackExchange
to fix that. **That survey is unnecessary:** `~/projects/GeoCase_Studies` (the Geospatial
Interview Handbook) contains 54 questions, each with a `## Probing` section that names the
specific trap the question exists to surface, each backed by a runnable solution and a pytest
suite. That is a better source than a StackExchange trawl — it is already curated, already
verified, and already written in prose that becomes each function's documentation.

Classifying all 54 by the scope boundary above gives three groups. **Only the first is in
scope.**

**Group A — silent failure. Candidate spine members.**

| Handbook | Trap, as the handbook states it |
|---|---|
| ANA-0037 | Voronoi cell order does not match input point order; skipping the sjoin back "silently mislabels every catchment" |
| ALG-0022 / VIZ-0052 | XYZ counts Y southward, TMS northward — "the single most common bug in tile code"; the map renders, mirrored |
| VEC-0012 | Boundary point: `within` silently drops it, `intersects` silently quadruplicates the row |
| VEC-0007 | `.centroid` of a C-shape or donut lands outside the polygon; `representative_point()` is guaranteed inside |
| VEC-0014 | `make_valid` can change geometry *type*; `buffer(0)` "quietly deletes bowtie lobes" |
| VEC-0013 | WKB equality misses rings that start at a different vertex but are geometrically identical |
| VEC-0008 | RFC 7946 specifies EPSG:4326; writing a projected frame to GeoJSON "silently produces a non-conformant file" |
| VEC-0029 | Densifying after reprojection instead of before makes a straight line visibly wrong on a curved projection |
| VEC-0002 | WKT is `x y` = lon lat, the reverse of the `lat, lon` convention most APIs use |
| ALG-0028 | Collinear overlapping segments return `None` — "a real bug in a topology tool" |
| ALG-0021 | Points metres apart across the equator or prime meridian share no geohash prefix |
| FND-0027 | Geodesic area — the same degrees trap as `area_m2`, on the ellipsoid |
| FND-0010 | `length_m` — the degrees trap applied to length |
| FND-0047 | Antimeridian splitting, generalising `bounds` and `crosses_antimeridian` |
| TRJ-0036 | Linear lat/lon interpolation is wrong across the antimeridian; interpolating across a 3-hour gap "produces confident nonsense" |
| RAS-0024 | Zonal statistics with partial pixel coverage and NoData |
| SQL-0042 | `eps` in input units — clustering EPSG:4326 with `eps := 500` means 500 *degrees* (confirms `cluster_points_m`) |

**Group B — real but out of scope.** Performance and index traps: ALG-0031, DAT-0017,
DAT-0046, VEC-0018, SQL-0040/0041/0043/0044. These produce *slow* or *loud* failures, not
wrong numbers. Belongs in the handbook, not here.

**Group C — interview exercises, not library functions.** ALG-0003, ALG-0004, ALG-0019,
ALG-0020, FND-0001, FND-0015, FND-0016, VEC-0005, VEC-0011, VEC-0034, RSN-0054, SYS-0053.
Implement-this problems where the naive answer is correct or loudly wrong. **Promoting these
would be exactly the filler that dilutes the correctness claim.**

The Group A rows above are candidates, not commitments — the prior-art screen below removes
several outright, and Step 0 removes any survivor a coding agent reliably gets right. Note
that three of them (FND-0010, FND-0027, FND-0047) confirm gaps guessed in the earlier draft,
and SQL-0042 independently confirms `cluster_points_m`; the rest were not on that list,
which is the point.

#### Prior art — the second exclusion criterion

An earlier draft screened candidates against a single question: *does a coding agent get
this wrong?* That is necessary but not sufficient. The other disqualifier is prior art — a
maintained package, or a one-liner on shapely/pyproj/rasterio, that already owns the
operation. Where that exists, "use X" is a documentation line, not a function to maintain,
and shipping a duplicate dilutes the correctness claim exactly as Group C filler would. The
two screens are independent: an agent can fumble an operation whose settled answer exists —
it fails Step 0 *and* is still excluded, because the remedy is to cite the answer, not to
fork it. (Step 0 gains a second use here: for excluded operations it measures whether agents
*reach* the prior art unprompted, which is benchmark material.)

Prior art known against the current candidates. Verify each row during Step 0 — most of
these claims are one `pip install` away from being checked:

| Candidate | Prior art | Consequence |
|---|---|---|
| `representative_point` | shapely ships `geom.representative_point()` verbatim | **Excluded** — docs line only |
| `tile_xyz_to_tms` / `tile_bounds` | `mercantile` / `morecantile` own tile math completely | **Excluded** |
| `zonal_stats` | `rasterstats`; `exactextract` for fractional pixel coverage | **Excluded** |
| `split_at_antimeridian` | the `antimeridian` package (maintained, STAC ecosystem) owns splitting, fixing, and bounds | **Excluded** — also contests Tier 1's `bounds` / `crosses_antimeridian` |
| `pixel_to_world` | rasterio's `dataset.xy(row, col)` returns the pixel **centre** by default | **Contested** — likely a docs line once the raster spine is rasterio-based |
| `utm_epsg_for` | `geopandas.estimate_utm_crs()` / `pyproj.database.query_utm_crs_info` select zones from EPSG areas of use, which encode the Norway exceptions | **Contested** — verify the Svalbard case explicitly; if pyproj gets it right, docs line |
| `geodesic_area_m2`, `length_m` | one-liners on `pyproj.Geod.geometry_area_perimeter` / `geometry_length` | **Contested** — the trap is real but the settled answer is one call |
| `cluster_points_m` | sklearn DBSCAN with `metric="haversine"` is the standard answer, and great-circle distance is dateline-safe | **Contested** |
| `dedupe_geometries` | `shapely.normalize()` is the settled canonicalisation primitive | **Contested** — the function reduces to normalise-then-dedupe |
| `to_geojson` | `gdf.to_crs(4326).to_json()`; GDAL's GeoJSON driver has an RFC 7946 mode | **Contested** |
| `buffer_m`, `fix_geometry`, `dissolve`, `sample_at`, `sjoin_boundary_safe`, `voronoi_labelled`, `interpolate_track`, `densify_m` | none found (shapely `segmentize` is planar-only, so `densify_m` stands) | Candidates stand |

**Contested** means the settled answer exists but is partial or under-discoverable: promote
only if Step 0 shows agents fail to reach it *and* the wrapper adds a real guarantee (as
`fix_geometry` does over bare `make_valid`); otherwise cite it. Every Contested row must be
resolved to Excluded or Stands during Step 0 — none may still read Contested when Step 1
begins.

#### Division of labour with the handbook

Do **not** merge the two repositories. They serve different audiences with the same
knowledge: the handbook explains *why* a trap exists to a human, the library makes it
*impossible to hit* from code. Merging would wreck both — the handbook's value is being
readable, the library's is being importable.

Cross-reference instead. Each promoted function cites its handbook id in its docstring; each
handbook question gains a line naming the library function as the production answer. Add the
handbook id to the corpus `params` so the link is machine-checkable rather than prose.

**Import the handbook's enforcement mechanism.** It solved the exact problem that produced
GeoCase's corpus defect: prose and code are structurally prevented from disagreeing, because
a fenced `python` block in a question file *is a failing test*. GeoCase's failure was the
mirror image — 60 fixtures whose `notes.md` claimed something the bytes did not support, and
727 tests that never checked. That mechanism is worth more than any individual question.

**Tier 1 — already implemented and hardened in `examples/`.** Promote first; these need
porting, not writing.

| Public name | Source | Handbook | Why it earns its place |
|---|---|---|---|
| `area_m2` | `area_m2_perfect` | FND-0006 | Equal-area projection; naive returns square degrees |
| `buffer_m` | `buffer_in_meters_perfect` | FND-0009 | Dateline unwrap + AEQD; the unwrap at `:178-211` is real work |
| `utm_epsg_for` | `get_utm_epsg_perfect` | — | Svalbard and SW Norway exceptions (`:241-253`) |
| `bounds` | `get_bbox_perfect` | FND-0047 | Antimeridian-safe bounding box |
| `crosses_antimeridian` | `crosses_antimeridian_perfect` | FND-0047 | Longitude normalisation |
| `pixel_to_world` | `pixel_to_world_perfect` | — | Pixel **centre**, not corner |
| `sample_at` | `sample_raster_at_lonlat_perfect` | RAS-0025 | CRS transform + NoData masking; naive returns `-9999` as data |
| `cluster_points_m` | `cluster_points_perfect` | SQL-0042 | Metric threshold, not degrees |
| `dissolve` | `dissolve_polygons_perfect` | VEC-0033 | Repairs invalid input before union; deterministic ordering |
| `fix_geometry` | `fix_geometry_perfect` | VEC-0014 | Repair with a validity guarantee; `make_valid` can change geometry *type* |

Tier 1 is not exempt from the prior-art screen: `utm_epsg_for`, `pixel_to_world`,
`cluster_points_m` and the `bounds`/`crosses_antimeridian` pair are Contested above and must
be resolved during Step 0. `buffer_m` has no owner anywhere and is the flagship;
`fix_geometry` and `dissolve` earn their place by the guarantee they add over the bare
primitive, which no prior art supplies.

**Tier 2 — new, justified by the handbook survey.** Write only if Step 0 shows agents get
them wrong **and** the prior-art screen leaves them standing. The screen already removes
`representative_point`, `tile_xyz_to_tms`/`tile_bounds`, `zonal_stats` and
`split_at_antimeridian`, and puts four more on notice — see the prior-art table above. What
remains, ordered by how silent the failure is:

| Public name | Handbook | Trap |
|---|---|---|
| `voronoi_labelled` | ANA-0037 | Cell order ≠ input order; silently mislabels every catchment |
| `sjoin_boundary_safe` | VEC-0012 | `within` drops boundary points, `intersects` quadruplicates them |
| `interpolate_track` | TRJ-0036 | Antimeridian-safe, with a mandatory max-gap cutoff |
| `densify_m` | VEC-0029 | Densify *before* reprojection, geodesically; shapely `segmentize` is planar-only |
| `length_m` | FND-0010 | The degrees trap, applied to length — *contested* |
| `geodesic_area_m2` | FND-0027 | Ellipsoidal area, where planar equal-area is not enough — *contested* |
| `dedupe_geometries` | VEC-0013 | Normalises ring start vertex before comparing — *contested* |
| `to_geojson` | VEC-0008 | RFC 7946 mandates EPSG:4326; reproject or refuse — *contested* |

**Deliberately excluded** — Groups B and C above, plus `point_in_polygon`, `reproject_point`,
`reproject_geometry`, `detect_null_island`, `validate_coordinate_bounds`. Also dropped from
the earlier draft: **`rasters_aligned`** and **`find_intersections`**, which the survey did not
corroborate as silent-failure traps. `clip_raster` and `rasterize_geometries` remain deferred
pending the rasterio port.

Layout: `src/geocase/vector.py` and `src/geocase/raster.py`, re-exported flat from
`src/geocase/__init__.py`. Flat is correct — `from geocase import area_m2` is the adoption
path. If every surviving Tier 2 candidate lands the surface is ~15 names, which is still
small enough for a flat namespace; revisit only if it passes ~30.

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
pins 6 functions and 19 types for a catalog. The new surface is ~8–10 functions (Tier 1
after the prior-art screen) plus `formats.check`, reaching ~15 only if every surviving
Tier 2 candidate is justified by Step 0.

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
- `tests/benchmark/agent_baseline/` — the Step 0 harness, verbatim prompts, and a committed
  results table. Kept after the gate and treated as a **first-class deliverable**, not a
  gate artifact: "N neutral geospatial tasks, X silent failures from a frontier agent" is a
  publishable, linkable result — realistically the only marketing channel this project has —
  and it doubles as the launch write-up. Re-run it when major new models ship.

**Moved**

- `src/geocase/{catalog,cases,loaders}/` → `tests/corpus/`
- `examples/interview_questions/` → source material for the above; naive halves retained
  under `tests/regression/`

**External — not modified, but load-bearing**

- `~/projects/GeoCase_Studies` — the Geospatial Interview Handbook. Supplies the trap survey
  behind the spine table and the citation for each function. Kept separate by design (see
  "Division of labour"); see trap 8 for the citation-rot risk.

**Modified**

- `src/geocase/__init__.py` — new flat surface (~8–10 names at Tier 1, ~15 with all
  surviving Tier 2 candidates)
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
6. **Step 0 must not be run with a leading prompt.** Mentioning edge cases, the dateline, or
   GeoCase itself invalidates the result — it measures whether an agent *can* be told, not
   whether it gets there unprompted, and only the latter justifies the library. Commit the
   prompts verbatim so this is auditable.
7. **Step 0 grades against the corpus, so Plan 13 partially precedes it.** The oracles used
   must be ones already verified correct. Where a Step 0 operation depends on a fixture Plan
   13 is fixing, use the `simple_valid_*` canonicals — which Plan 13 leaves untouched — or
   construct the input inline.
8. **The handbook is a separate repository with no dependency link.** Cited handbook ids are
   prose until something checks them. Either vendor the id list into the corpus `params` and
   validate it, or accept that the citations rot silently — which is the same class of defect
   as the `notes.md` claims that produced Plan 13. Do not leave this undecided.
9. **Tier 2 is not a commitment.** Even the post-screen list of eight is more code than the
   entire Tier 1 port. Write them one at a time, each justified by a Step 0 failure and a
   cleared prior-art row, and stop when the justification runs out. A surface that grows
   because the list existed is how this becomes the utils package the risk section warns
   about.

---

## Verification

```bash
# 0. THE GATE — must have run and passed before anything below is attempted
python -m pytest tests/benchmark/agent_baseline -q
#    Reports per-operation pass/fail for agent-generated implementations against the
#    corpus oracles. Headline metric is the SILENT failure count, not the pass rate:
#    a loud failure is one an agent's own test run would catch, and does not justify
#    a dependency. Apply the decision rule in Step 0 before proceeding.

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
python -c "import geocase; print(len(geocase.__all__))"   # ~9-11 at Tier 1, not 25

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
  all three describe shipping the catalog as the product. **One carve-out:** the agentic-AI
  argument makes discoverability load-bearing — an agent can only emit
  `from geocase import buffer_m` if geocase is findable — so a *minimal* distribution path
  is in scope: a PyPI wheel, a README stating the correctness claim, and the Step 0
  benchmark write-up as the launch artifact. What stays out is the catalog-shaped remainder
  of Plans 11/12 (conda packaging, the docs site, coverage matrices).

## Main risks, stated plainly

**1. "Just use pyproj properly."** This is roughly 1,500 lines of utilities, and someone will
say it. That is equally true of `dateutil` and `tenacity`. The defence is not the code, it is
the evidence: the corpus and the 36 strict xfails are what make the correctness claim
credible. Which is why Plan 13 comes first — if the fixtures lie, the claim is worthless and
this becomes another utils package. The sharper form of the objection is "just use
`antimeridian` / `mercantile` / `rasterstats` / `estimate_utm_crs`" — and where that is
true, the correct response is to agree, which is what the prior-art screen enforces. The
library's ground is only the operations nobody owns.

**2. Coding agents may already close the gap.** Addressed in Context above and tested by
Step 0. If agents reliably produce correct implementations, no amount of packaging saves
this and the plan should be abandoned rather than reframed.

**3. The thesis has been revised twice.** From "the corpus is the product" to "the functions
are the product, the corpus is the evidence," and from "you didn't know about these traps" to
"this is settled and verified everywhere." Each revision relocated the value rather than
demonstrating it. That is the signature of motivated reasoning, and it is the specific reason
Step 0 exists as a gate with a decision rule fixed in advance. **If Step 0 fails, stop — do
not look for a fourth place to put the value.**
