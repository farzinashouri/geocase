"""Adversarial axes as named fixtures.

Tier 1 of Plan 20 §3.2. Each function here builds one fixture that exposes one
confirmed failure mode, named after the bug rather than after the data, so a
test reads as a statement about what is being defended against.

**Nodata (3/3 evidence, confirmed live).** The first three are the carve-out:
they are exempt from the Phase 2 interview gate because their evidence is a
measured bug in a real compute-side repository, not a prediction about what
maintainers want. Everything else in Phase 3 waits on the interviews.

**Not here, deliberately:** anything reachable in four lines of numpy.
``np.zeros((4, 32, 32))`` is not a fixture library's job, and shipping it
invites exactly the conclusion Rejector C drew — that the generator adds nothing
over what a maintainer writes inline.
"""

from __future__ import annotations

from geocase.raster.primitive import DEFAULT_SIZE, FixtureSpec, raster_fixture

__all__ = [
    "nodata_border",
    "ambiguous_zero",
    "all_nodata",
    "missing_crs_authority",
    "epsg_str_vs_int",
    "band_count_mismatch",
    "rotated_transform",
    "nonsquare_pixels",
]


# --------------------------------------------------------------- nodata (3/3)


def nodata_border(
    *, size: int = DEFAULT_SIZE, bands: int = 4, border: int = 48, nodata: int = 0
) -> FixtureSpec:
    """A scene with a wide nodata frame around valid data.

    **The bug:** interpolating resampling (bilinear, cubic, lanczos) with
    neither ``src_nodata`` nor ``dst_nodata`` declared averages the nodata
    region into its valid neighbours. The smear is in-bounds, in the right CRS,
    and plausible — so nothing downstream notices. In the adopter's repository
    this contaminated a 4.6M-pixel region.

    **How to use it:** resample this fixture the way your pipeline does, then
    assert that no pixel adjacent to the border moved toward the nodata value.
    A correct pipeline declares nodata on both ends, or resamples with nearest.
    """
    return raster_fixture(
        bands=bands,
        size=size,
        nodata=nodata,
        nodata_border=border,
        tags={
            "GEOCASE_AXIS": "nodata_border",
            "GEOCASE_EXPECTS": (
                "src_nodata and dst_nodata declared before any interpolating "
                "resample; otherwise the border smears into valid pixels"
            ),
        },
    )


def ambiguous_zero(
    *, size: int = DEFAULT_SIZE, bands: int = 6, band: int = 2
) -> FixtureSpec:
    """Valid dark pixels at 0, plus one band reading 0 in an otherwise valid pixel.

    **The bug:** post-offset-removal, 0 is both the nodata sentinel and a
    representable valid reflectance. An "all bands are zero" nodata heuristic
    therefore lets a single-band zero through in a pixel that is otherwise
    valid. In the adopter's pipeline that sample normalised to about −0.48σ — a
    plausible-looking dark outlier rather than a masked pixel.

    The fixture combines both halves: ``fill="zeros"`` is not used (that would
    make everything ambiguous and prove nothing), instead the scene is a normal
    ramp with a single interior pixel zeroed in exactly one band.

    **How to use it:** run your nodata mask over this and assert the interior
    pixel is either masked in that band or explicitly documented as valid. If
    your mask is all-bands-zero, it will report the pixel as valid data.
    """
    return raster_fixture(
        bands=bands,
        size=size,
        nodata=0,
        nodata_single_band=band,
        tags={
            "GEOCASE_AXIS": "ambiguous_zero",
            "GEOCASE_EXPECTS": (
                "per-band nodata handling; an all-bands-zero heuristic misses "
                "the single-band zero at the centre pixel"
            ),
        },
    )


def all_nodata(
    *, size: int = DEFAULT_SIZE, bands: int = 4, nodata: int = 0
) -> FixtureSpec:
    """A scene that is entirely nodata.

    **The bug:** degenerate statistics. A normaliser computing ``x / max(x)``
    divides by zero and yields silent NaN; a percentile stretch over an empty
    valid-pixel set raises or returns garbage depending on the library. Real
    archives contain these — an entirely-cloud tile, a scene-edge granule.

    **How to use it:** feed it to your normalisation path and assert it either
    raises a clear error or returns a documented empty result. Silent NaN
    propagating into a model is the failure.
    """
    return raster_fixture(
        bands=bands,
        size=size,
        nodata=nodata,
        all_nodata=True,
        tags={
            "GEOCASE_AXIS": "all_nodata",
            "GEOCASE_EXPECTS": (
                "explicit handling of an empty valid-pixel set; not silent NaN"
            ),
        },
    )


# ------------------------------------------------- metadata adversariality
# Rejector B's axes. Gated behind Phase 2 for *expansion*, but these three are
# cheap, confirmed-live, and share the primitive, so they ship with it.


def missing_crs_authority(*, size: int = DEFAULT_SIZE, bands: int = 1) -> FixtureSpec:
    """Valid WKT with no EPSG authority code.

    **The bug:** ``int(dataset.GetSpatialRef().GetAuthorityCode(None))`` raises
    ``TypeError`` on ``None``, usually far from the code that assumed every
    raster has an EPSG code. Confirmed live by Rejector B.
    """
    return raster_fixture(
        bands=bands,
        size=size,
        crs="no-authority",
        tags={
            "GEOCASE_AXIS": "missing_crs_authority",
            "GEOCASE_EXPECTS": "handle GetAuthorityCode() -> None without int(None)",
        },
    )


def epsg_str_vs_int(*, size: int = DEFAULT_SIZE, bands: int = 1) -> FixtureSpec:
    """A fixture in EPSG:4326, for the str-vs-int identity round-trip.

    **The bug:** ``4326 == "EPSG:4326"`` is False, and so is
    ``"4326" == "EPSG:4326"``. Code comparing a CRS it read against a CRS it was
    configured with silently takes the "mismatch" branch — reprojecting data
    that was already in the target CRS, or refusing to merge tiles that match.
    """
    return raster_fixture(
        bands=bands,
        size=size,
        crs=4326,
        resolution=0.0001,
        origin=(11.0, 46.0),
        tags={
            "GEOCASE_AXIS": "epsg_str_vs_int",
            "GEOCASE_EXPECTS": "normalise CRS identity before comparing",
        },
    )


def band_count_mismatch(*, size: int = DEFAULT_SIZE, bands: int = 3) -> FixtureSpec:
    """A raster with fewer bands than a hardcoded reordering expects.

    **The bug:** ``array[[3, 2, 1]]`` against a 3-band raster raises
    ``IndexError``; against a 10-band one it silently selects the wrong bands.
    Named by both Rejector B and Rejector C.
    """
    return raster_fixture(
        bands=bands,
        size=size,
        tags={
            "GEOCASE_AXIS": "band_count_mismatch",
            "GEOCASE_EXPECTS": "check band count before reordering by index",
        },
    )


# ------------------------------------------------------ geotransform axes
# Plan 18's "deliberately not in this plan" fixtures re-enter here as
# *fixtures* (the oracles over them remain out of scope — that is benchmark
# scale-out, which Phase 4 freezes).


def rotated_transform(
    *, size: int = DEFAULT_SIZE, bands: int = 1, rotation: float = 0.1
) -> FixtureSpec:
    """A raster whose affine has non-zero rotation terms.

    **The bug:** computing pixel coordinates as ``(x - c) / a`` drops the ``b``
    and ``d`` terms. The result stays in-bounds and in the correct CRS while
    being tens of metres wrong — measured at 32.6 m on the corpus fixture this
    replaces.
    """
    import math

    res = 10.0
    cos_t, sin_t = math.cos(rotation), math.sin(rotation)
    transform = (
        res * cos_t,
        -res * sin_t,
        500_000.0,
        -res * sin_t,
        -res * cos_t,
        4_500_000.0,
    )
    return raster_fixture(
        bands=bands,
        size=size,
        transform=transform,
        tags={
            "GEOCASE_AXIS": "rotated_transform",
            "GEOCASE_EXPECTS": "use the full affine; do not assume b == d == 0",
        },
    )


def nonsquare_pixels(
    *,
    size: int = DEFAULT_SIZE,
    bands: int = 1,
    resolution: tuple[float, float] = (30.0, 60.0),
) -> FixtureSpec:
    """A raster with different x and y pixel sizes.

    **The bug:** area computed as ``count * res**2`` using one axis' resolution
    is wrong by the ratio between them — exactly 2× for the default 60×30 m.
    """
    res_y, res_x = resolution
    return raster_fixture(
        bands=bands,
        size=size,
        resolution=(res_y, res_x),
        tags={
            "GEOCASE_AXIS": "nonsquare_pixels",
            "GEOCASE_EXPECTS": "compute area from both axes of the transform",
        },
    )
