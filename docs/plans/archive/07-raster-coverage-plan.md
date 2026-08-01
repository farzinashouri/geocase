# Raster Coverage Plan

> **Archived — superseded. Retained as an implementation log.** Executed by plan 08; the coverage strategy it defines is reflected in the raster catalog.
>
> The single active roadmap is [`docs/contributing/development-plan.md`](../../contributing/development-plan.md).

> Created: April 2026
> Status: Superseded (July 2026)

This document captures the proposed implementation plan for expanding
**raster coverage** in GeoCase toward a practical v1.0 baseline.

The focus of this plan is not generic raster coverage in the abstract. It is
coverage that reflects the kinds of raster data users are most likely to work
with in real geospatial pipelines:

- optical satellite imagery,
- multispectral imagery,
- radar / SAR imagery,
- DEM and terrain rasters,
- derived products such as NDVI,
- land / water masks and related classification products,
- and both classic GeoTIFF and Cloud-Optimized GeoTIFF delivery styles.

This plan also distinguishes between two kinds of raster coverage:

1. **bundled synthetic fixtures** that are small, fast, redistributable, and
   suitable for CI,
2. **realistic remote scenes** that belong in manifests and later storage-backed
   workflows.

That split keeps the package small while still designing toward realistic Earth
Observation use cases.

For the high-level roadmap context, see
[`docs/plans/03-consolidation-roadmap.md`](03-consolidation-roadmap.md).
For how remote scenes eventually connect to manifests and storage, see
[`docs/plans/06-manifest-support.md`](06-manifest-support.md) and
[`docs/contributing/manifests-and-storage.md`](../../contributing/manifests-and-storage.md).

---

## Goal

Implement the smallest **high-value** raster expansion that gives GeoCase a
credible v1.0 foundation for common Earth Observation and raster-analysis
workflows.

That means GeoCase should be able to test code against representative raster
families such as:

- optical RGB imagery,
- multispectral imagery,
- SAR / radar imagery,
- DEM rasters,
- NDVI-style derived products,
- binary and categorical masks,
- GeoTIFF / COG packaging differences,
- and geographically meaningful edge cases such as coastal, polar,
  equatorial, and dateline-adjacent scenes.

This phase should prioritize **breadth of behavior coverage** over huge volumes
of data.

---

## Why this matters

Raster support is now one of the clearest remaining v1.0 gaps.

GeoCase already has meaningful vector breadth and a working manifest layer, but
its raster coverage is still uneven relative to the kinds of datasets users
actually process in production.

In practice, many geospatial workflows depend on operations such as:

- land / water masking,
- NoData-aware statistics,
- DEM-based terrain calculations,
- multispectral band selection,
- NDVI or similar index calculations,
- working across land and ocean boundaries,
- handling different raster dtypes and scaling conventions,
- and opening the same logical product in both GeoTIFF and COG-style layouts.

Without stronger raster coverage, GeoCase risks overfitting to a small set of
simple GeoTIFF fixtures rather than the broader EO-style cases it is meant to
help validate.

---

## Existing repo inputs

The repository already contains a useful raster starting point:

- `src/geocase/data/core/raster/`
- `src/geocase/cases/raster.py`
- `src/geocase/assertions/raster.py`
- `tests/unit/test_raster_loaders.py`
- `examples/test_raster_nodata_suite.py`
- `examples/test_gdal_footprint.py`
- `docs/contributing/raster-dtypes-and-radiometric-resolution.md`

The current bundled raster tree already covers:

- baseline GeoTIFF loading,
- explicit NoData handling,
- shifted alignment,
- multiband GeoTIFF behavior,
- several dtype families,
- UTM / reprojection boundary behavior,
- and a set of footprint-related raster edge cases.

That means this plan should **not** restart from zero.
It should re-baseline reality, then fill the highest-value remaining gaps.

---

## Scope of this plan

### In scope

- EO-oriented bundled raster fixtures that are small and synthetic but
  structurally realistic,
- coverage for optical, multispectral, SAR, DEM, derived-index, and mask
  products,
- GeoTIFF and COG-related fixture coverage,
- geographic diversity relevant to real workflows,
- metadata-driven raster assertions,
- parameterized raster suites driven by the live catalog,
- and planning hooks for future manifest-backed realistic scenes.

### Out of scope for this phase

- large real satellite scenes bundled directly inside the package,
- downloader / cache implementation,
- a full remote-scene runtime pipeline,
- and exhaustive coverage of every remote-sensing product family.

This is a **high-value representative set**, not a complete EO data catalog.

---

## Design principles

### 1. Small bundled core, realistic future path

Bundled raster cases should remain tiny enough for fast tests and clean package
size. They should be synthetic and license-safe.

Realistic scenes such as Sentinel, Landsat, Copernicus DEM, or similar assets
should eventually live in manifests and storage-backed workflows, not in the
core package.

### 2. Product-family coverage beats random fixture growth

New raster cases should be chosen to represent the main product families users
actually encounter, rather than adding more generic GeoTIFFs without a clear
use-case rationale.

### 3. Geography matters

Raster behavior often changes in meaningful ways by geography:

- land vs water boundaries,
- coastal masks,
- polar projection behavior,
- equatorial positioning,
- and dateline-adjacent or zone-boundary cases.

At least some bundled cases should reflect these realities.

### 4. Structural realism is enough for bundled fixtures

Bundled fixtures do not need to be visually realistic satellite scenes.
They do need to encode the right structural behavior:

- band count,
- dtype,
- nodata conventions,
- scaling assumptions,
- compression,
- overviews,
- tiling,
- masks,
- and expected metadata.

### 5. Metadata should drive tests

Where possible, raster expectations should live in case metadata rather than in
ad hoc assertions scattered across tests.

---

## Coverage model

The raster backlog should be organized along three axes:

1. **product family**
2. **delivery / format style**
3. **geographic scenario**

### Product families to cover

The core v1.0 raster matrix should include at least these families:

- optical RGB imagery,
- optical multispectral imagery,
- SAR / radar imagery,
- DEM,
- NDVI or similar derived continuous index products,
- categorical land-cover style products,
- and binary water / land mask products.

### Delivery / format styles to cover

For the above families, GeoCase should cover at least:

- classic GeoTIFF,
- tiled GeoTIFF,
- internal-overview / COG-style layout,
- optional external overview layout,
- and several common compression strategies.

### Geographic scenarios to cover

For realism, at least some fixtures should be designed around:

- mixed land / water coastal scenes,
- mountainous terrain,
- equatorial scenes,
- polar scenes,
- dateline-adjacent scenes,
- and existing UTM boundary behavior.

---

## Proposed bundled fixture families

The goal is not to add all of these in one burst without prioritization.
These are the target families that cover most common raster use cases.

### Optical

- `optical_rgb_small`
- `multispectral_s2_like_small`
- `multispectral_mixed_resolution_small`

These cover:

- simple RGB workflows,
- Sentinel-2-like multispectral behavior,
- band selection logic,
- scale-factor handling,
- and mixed-resolution product structures.

### Radar / SAR

- `sar_vv_small`
- `sar_dualpol_small`

These cover:

- single-polarization radar,
- dual-polarization behavior,
- float or DN-style intensity handling,
- and non-optical raster value distributions.

### Elevation / terrain

- `dem_small`
- `dem_nan_nodata_small`

These cover:

- signed elevation values,
- sea / missing-value handling,
- terrain workflows,
- and nodata conventions that differ from optical imagery.

### Derived continuous products

- `ndvi_small`
- optional later: `ndvi_scaled_int16_small`

These cover:

- floating continuous derived products,
- value-range expectations such as `[-1, 1]`,
- and scaled-int versus float representations.

### Masks and classifications

- `water_mask_small`
- `landcover_small`

These cover:

- binary masks,
- land / water operations,
- categorical rasters,
- and class-coded raster behavior distinct from continuous products.

### Delivery-style fixtures

- `cog_singleband_small`
- `cog_multispectral_small`
- `geotiff_external_overviews_small`
- `geotiff_deflate_small`
- `geotiff_lzw_small`
- `geotiff_packbits_small`

These cover:

- COG-style layout,
- overviews,
- tiling,
- multi-band COG handling,
- and common compression variants.

### Geography-specific fixtures

- `optical_coastal_small`
- `optical_equator_small`
- `optical_polar_small`
- `optical_dateline_small`

These cover:

- land / water boundaries,
- equatorial placement,
- polar CRS behavior,
- and dateline-adjacent logic.

Existing fixtures such as `geotiff_utm_boundary` and the footprint edge-case
set should remain part of the live raster matrix rather than being replaced.

---

## Recommended prioritization

The full family list above is broader than the minimum first pass.
The implementation order should prioritize cases with the highest reuse across
real workflows.

### Priority 1: land / water + common EO structure

Add first:

- `optical_rgb_small`
- `multispectral_s2_like_small`
- `water_mask_small`
- `dem_small`
- `ndvi_small`

These five cases immediately cover a large portion of common raster logic:

- RGB loading,
- multispectral band handling,
- masking,
- DEM usage,
- and derived continuous products.

### Priority 2: format and packaging realism

Add next:

- `cog_singleband_small`
- `cog_multispectral_small`
- `geotiff_external_overviews_small`
- compression variants

These fixtures are important because GeoTIFF vs COG behavior is a practical
source of real-world differences.

### Priority 3: radar and geography

Add after the core optical / DEM / mask set is stable:

- `sar_vv_small`
- `sar_dualpol_small`
- `optical_polar_small`
- `optical_dateline_small`
- `optical_equator_small`

These fixtures deepen realism and broaden the use-case surface, but are less
foundational than the first two priorities.

### Priority 4: mixed-resolution and scaled variants

Add last in the bundled phase:

- `multispectral_mixed_resolution_small`
- `dem_nan_nodata_small`
- `ndvi_scaled_int16_small`
- `landcover_small`

These are valuable, but can follow once the main EO raster model is in place.

---

## Metadata changes needed

To make raster coverage scalable, some expectations should move from informal
convention into the typed metadata model.

### Extend raster assertion metadata

Add raster-oriented assertion fields in `src/geocase/catalog/models.py`, such
as:

- `expected_band_count`
- `expected_dtype`
- `expected_shape`
- `expected_nodata_value`
- `nodata_convention`
- `expected_compression`
- `expected_overviews`
- `expected_band_names`
- `expected_scale_factor`
- `expected_colormap_present`
- `is_cog`

This allows each raster case to describe itself more explicitly.

### Clarify tag vocabulary

Raster coverage will be easier to select and test if tags are standardized.
Recommended tags include:

- product family tags:
  - `optical`
  - `multispectral`
  - `sar`
  - `dem`
  - `index-product`
  - `mask`
  - `classification`
- geography tags:
  - `coastal`
  - `land-water`
  - `equatorial`
  - `polar`
  - `dateline`
  - `mountainous`
- delivery tags:
  - `cog`
  - `overviews`
  - `tiled`
  - `compressed`

The exact model representation can stay simple, but the vocabulary should be
consistent.

---

## Assertion and test work needed

### Raster assertions

Expand `src/geocase/assertions/raster.py` with helpers such as:

- compression checks,
- overview presence checks,
- NaN nodata checks,
- COG structure checks,
- band-name checks,
- scale-factor checks,
- and categorical / colormap checks where relevant.

These should remain lightweight and aligned with GeoCase’s current assertion
style.

### Integration suite

`tests/integration/test_core_raster_suite.py` is the natural place to become the
canonical raster integration suite.

That suite should:

- resolve live raster cases from the registry,
- open each case through `RasterCase`,
- dispatch metadata-driven assertions,
- and verify that the raster catalog remains internally consistent.

### Example/sample-function tests

Raster examples should mirror the same general idea already used for vector
examples: simple realistic functions tested across multiple raster cases.

Candidate examples include:

- water masking from a raster mask,
- NDVI-style calculations,
- DEM hillshade or terrain preprocessing,
- and simple SAR summary statistics.

The goal is to demonstrate that GeoCase can test **real algorithm behavior**,
not only file loading.

---

## Fixture generation approach

These raster fixtures should be generated, not hand-authored.

Recommended additions under `scripts/`:

- `generate_optical_raster_cases.py`
- `generate_sar_raster_cases.py`
- `generate_dem_raster_cases.py`
- `generate_cog_raster_cases.py`
- or a single consolidated generator if that proves cleaner.

Each generator should:

- create reproducible arrays from code,
- write raster metadata intentionally,
- keep artifacts small,
- and emit `case.yaml` fields that match the actual raster content.

This keeps the fixture set reproducible, license-safe, and easier to maintain.

---

## Relationship to manifests and storage

This raster plan intentionally separates **bundled structural coverage** from
**realistic remote-scene coverage**.

### Bundled core cases

Bundled cases should stay:

- tiny,
- redistributable,
- synthetic,
- deterministic,
- and suitable for CI.

### Future manifest-backed scenes

Realistic scenes such as:

- Sentinel-2 coastal tiles,
- Sentinel-1 SAR scenes,
- Landsat imagery,
- Copernicus DEM tiles,
- or other larger EO products,

should live in manifests and later use storage support for fetching and caching.

That future work should treat bundled cases and remote scenes as **paired
analogs** where possible.

For example:

- bundled `multispectral_s2_like_small` ↔ manifest-backed Sentinel-2 scene,
- bundled `sar_dualpol_small` ↔ manifest-backed Sentinel-1 scene,
- bundled `dem_small` ↔ manifest-backed DEM tile.

This lets contributors prototype against bundled fixtures first, then scale to
larger real scenes once the storage layer exists.

---

## Implementation sequence

### Step 1: Re-baseline the live raster catalog

Use the existing tree under `src/geocase/data/core/raster/` as the source of
truth.

Compare it against:

- `docs/plans/03-consolidation-roadmap.md`
- `docs/plans/01-actionable-next-steps.md`
- `docs/contributing/raster-dtypes-and-radiometric-resolution.md`
- current raster tests and examples

Resolve outdated statements so the plan reflects live reality.

**Output:** a narrowed, accurate raster backlog.

### Step 2: Define the v1.0 raster matrix

Translate the product-family / delivery-style / geography model into a concrete
v1.0 target matrix.

Decide which cases are:

- required for v1.0 bundled coverage,
- desirable but deferrable,
- and explicitly remote-only later.

**Output:** a stable prioritized raster matrix.

### Step 3: Add the first bundled EO fixture tranche

Implement the first highest-value cases:

- `optical_rgb_small`
- `multispectral_s2_like_small`
- `water_mask_small`
- `dem_small`
- `ndvi_small`

These give GeoCase immediate coverage across the most common raster-analysis
patterns.

**Output:** first practical EO-oriented bundled raster set.

### Step 4: Add format / delivery fixtures

Implement the first packaging-focused cases:

- `cog_singleband_small`
- `cog_multispectral_small`
- overview fixture(s)
- compression fixture(s)

These validate format and delivery assumptions beyond plain baseline GeoTIFF.

**Output:** stronger GeoTIFF / COG structural coverage.

### Step 5: Expand metadata-driven raster assertions

Update `src/geocase/catalog/models.py` and `src/geocase/assertions/raster.py`
so raster expectations are encoded more explicitly and tested more uniformly.

**Output:** clearer and more scalable raster validation model.

### Step 6: Consolidate the raster integration suite

Make `tests/integration/test_core_raster_suite.py` the main raster suite driven
by the live registry and metadata assertions.

**Output:** one canonical raster suite instead of scattered partial coverage.

### Step 7: Add EO-style example workflows

Add example algorithms and parameterized tests using the new raster families.

**Output:** realistic demonstrations of GeoCase’s raster testing value.

### Step 8: Plan the manifest-backed realistic scene layer

Once bundled structural coverage is in place, define the paired realistic scenes
that should later live in external manifests.

**Output:** a clean bridge from bundled fixtures to remote-scene workflows.

---

## Success criteria

This phase can be considered successful when:

- the roadmap reflects the real live raster catalog,
- the bundled raster catalog covers the main EO product families,
- GeoCase can test land / water, DEM, multispectral, and derived-product logic,
- GeoTIFF and COG structural differences are represented,
- raster assertions are metadata-driven rather than ad hoc,
- `tests/integration/test_core_raster_suite.py` is meaningful and active,
- and a clear path exists from bundled raster fixtures to future manifest-backed
  realistic scenes.

---

## Questions to resolve during implementation

### 1. How much COG validation should GeoCase do?

A lightweight structural check may be enough for v1.0.
A deeper validator could require optional dependencies.

### 2. Should SAR fixtures use float backscatter or integer DN values?

Both exist in practice. The first bundled version should pick whichever yields
simpler, clearer assertions while still reflecting real workflows.

### 3. Should mixed-resolution multispectral products be bundled now or later?

They are important for realism, but they add complexity. They may be a second
wave after the simpler multispectral case lands.

### 4. Should NetCDF / Zarr EO products be part of this same phase?

Some EO workflows rely on NetCDF or Zarr rather than GeoTIFF. That may deserve
a separate follow-on plan instead of overloading this one.

### 5. How much geographic realism is required in bundled fixtures?

Bundled fixtures should be structurally meaningful, but they do not need to be
photorealistic. The right balance is “behaviorally realistic, operationally
small.”

---

## Recommended immediate next actions

1. Re-baseline the current raster case list against the live tree.
2. Finalize the Priority 1 EO raster tranche.
3. Decide the raster metadata fields to add before too many new cases are
   created.
4. Implement the first bundled fixture generator(s).
5. Move raster integration coverage into the canonical `tests/integration/`
   suite.
