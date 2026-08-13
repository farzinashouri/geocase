# Step 0 results — agent baseline (Plan 14 gate)

**Run date:** 2026-08-09
**Agent under test:** Claude (Fable 5) coding agents, one fresh agent per operation,
tool access enabled (shell + the sandbox interpreter), allowed to self-verify.
**Prompts:** committed verbatim under [`prompts/`](prompts/). Neutral task statements
only — no mention of edge cases, traps, the dateline, or GeoCase (Plan 14, trap 6).
Each agent worked in a clean scratch sandbox with a fresh venv (shapely, pyproj,
rasterio, numpy, scikit-learn) so no path, package list, or repo content could leak
context.
**Oracles:** constructed inline in [`grade.py`](grade.py); expected values computed from
`pyproj.Geod` and first principles, not from the (Plan-13-unverified) fixture corpus
(trap 7).
**Raw output:** [`results.json`](results.json). Generated code: [`generated/`](generated/).

## Per-operation outcome

| Operation | Control | Edge checks | Outcome | What the agent did |
|---|---|---|---|---|
| `area_m2` | pass | antimeridian box: **pass** | CORRECT | `Geod.geometry_area_perimeter` with explicit ring re-orientation (caught pyproj's signed-ring-sum hole bug on its own) |
| `buffer_m` | pass | 50 km buffer across dateline: **SILENT FAIL** (both trials) | **SILENT FAILURE — 2/2 trials** | AEQD project→buffer→project back, no unwrap; returns an invalid bowtie spanning 360° of longitude that reports a point 211 km away as inside a 50 km buffer |
| `utm_epsg_for` | pass | Svalbard 33X: **pass**; Norway 32V: **pass** | CORRECT | Hardcoded the Norway/Svalbard grid exceptions unprompted, then cross-checked against pyproj's EPSG database |
| `sample_at` | pass (UTM raster, lon/lat query) | −9999 nodata sentinel: **pass** | CORRECT | CRS transform + masked read; nodata/out-of-bounds/NaN → `None` |
| `label_point` | pass | donut: **pass**; C-shape: **pass** | CORRECT | centroid-if-inside, else `polylabel`, with `representative_point()` fallback |
| `tile_bounds` | pass | TMS row flip at z=2: **pass** | CORRECT | Knew TMS row 0 is at the south edge; derived inverse Mercator directly |
| `cluster_points_m` | pass | E–W pair at 75°N: **pass**; dateline pair: **pass** | CORRECT | Union-find over `Geod.inv` geodesic distances — immune to both degree traps |
| `length_m` | pass | 1° at lat 60: **pass**; across dateline: **pass** | CORRECT | `Geod.geometry_length` |
| `position_at` | pass | ship leg across dateline: **pass** | CORRECT | Geodesic interpolation via `Geod.inv`/`Geod.fwd`, explicitly citing antimeridian handling |
| `voronoi_cells` | pass | cell order matches input order: **pass** | CORRECT | Mapped cells back to generators by point lookup — i.e. knew the ordering was not guaranteed |

**Headline: 10 operations, 9 fully correct, 1 silent failure (`buffer_m`, reproduced in a
second independent blind trial: `generated/gen_buffer_m_trial2.py`).**

The `buffer_m` failure is a textbook silent failure and survived the agent's own
verification in both trials: both agents validated *radial error geodesically*
(`Geod.inv` from center to boundary vertices), which is invariant under longitude
wrapping — the check literally cannot see the defect it needed to catch.

## Prior-art notes recorded during the run (Plan 14, Step 0.5)

- **`utm_epsg_for` — the prior-art table in Plan 14 is wrong.** `pyproj`'s
  `query_utm_crs_info` returns 32632 for (10.5°E, 78°N) and 32631 for (4.5°E, 60°N):
  the plain 6°-slice answers, *not* the 33X/32V grid exceptions. The EPSG areas of use
  do not encode the Norway/Svalbard conventions. The Contested row resolves to
  **Stands (no prior art)** — but the operation is removed anyway because the agent
  produced the exceptions unprompted.
- **`label_point`** — agent reached the settled shapely answer (`polylabel` /
  `representative_point`) unprompted. Confirms **Excluded**.
- **`tile_bounds`** — agent derived TMS math correctly without a tile library.
  Confirms **Excluded** (and the "single most common bug in tile code" was not
  reproduced).
- **`area_m2` / `length_m`** — agents reached the `pyproj.Geod` one-liners unprompted.
  Confirms **Excluded/cite** for `geodesic_area_m2` and `length_m`.

## Decision rule (fixed in advance in Plan 14, Step 0)

> Agent passes **most** operations → **Stop.** The library is redundant. Archive per
> the "if rejected" path and keep `format_compliance.py` and the corpus.

9/10 is "most". **The rule fires: Stop.** The single mixed-row survivor would be
`buffer_m` — one function, reproducibly fumbled, whose failure is invisible to the
generating agent's own tests. One function is not a library; per the plan's own risk
section, the remedy is a citation/upstream contribution, not a package.

## Limitations, stated plainly

- One trial per operation (two for `buffer_m`). Consistency across the 2×`buffer_m`
  trials and the uniformity of the other results suggest low variance, but this is
  n=1 evidence for nine of the ten rows.
- Single agent family (Claude), which is also the family that authored GeoCase and
  this harness. The prompts and grader are committed so other agents can be run
  against the same harness.
- Agents had tool access and were told to verify their code — the realistic condition
  for 2026 coding agents, but a bare-completion model would likely do worse.
- Prompts state the *contract* ("must lie inside", "`None` if no data", "accurate
  anywhere on Earth") without naming the trap. A vaguer spec would produce more
  failures — but a vaguer spec is a requirements defect, not a library gap.

## Reproduce

```bash
# grade the committed generated code against the oracles
python tests/benchmark/agent_baseline/grade.py

# or via pytest (pins the committed outcome)
python -m pytest tests/benchmark/agent_baseline -q
```

To re-run the experiment itself: send each file in `prompts/` verbatim to a fresh
coding agent with no other context, collect `gen_<op>.py`, and run `grade.py`.
