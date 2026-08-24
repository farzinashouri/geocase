"""The raster fixture primitive.

One low-level call that produces a small raster with deliberately awkward
metadata. Spec-accurate products (:mod:`geocase.raster.presets`) are built *on*
this, not the other way round — because the evaluations that asked for fixtures
did not want L2A specifically, they wanted control over the axes that break
raster-reading code.

Two design constraints come straight from the evaluation reports:

**The escape hatch.** :func:`raster_fixture` returns a :class:`FixtureSpec` with
``.array``, ``.transform``, ``.crs_wkt`` and ``.profile`` as public attributes.
Writing a file is optional and lives behind ``.write(path)``. A team that
already imports ``osgeo.gdal`` and will not add rasterio for a test helper can
take the array and build the file however they like.

**Size is a parameter.** The default is 256 — above the 224 px floor a ViT
pipeline needs, and a power of two. A 32×32 fixture cannot exercise a
Prithvi/ViT pipeline at all, so the floor is a hard requirement rather than a
default (Plan 20 trap 9).

Scope boundary (trap 4): this module produces bytes and metadata. It never
processes them. The moment it acquires resampling, reprojection or band math it
is competing with rasterio and will lose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np

#: The floor below which a fixture cannot exercise a ViT/Prithvi pipeline.
#: The one confirmed compute-side adopter set this as a hard requirement.
MIN_USEFUL_SIZE = 224

#: Default edge length. Above the floor, and a power of two.
DEFAULT_SIZE = 256

_WGS84_WKT = (
    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,'
    'AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],'
    'PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
    'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],'
    'AUTHORITY["EPSG","4326"]]'
)

#: A syntactically valid WKT naming no authority — GetAuthorityCode() returns
#: None for this, which is the live crash Rejector B reported.
_NO_AUTHORITY_WKT = (
    'PROJCS["unnamed_local_grid",GEOGCS["unknown",DATUM["unknown",'
    'SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],'
    'UNIT["degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],'
    'PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",15],'
    'PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],'
    'PARAMETER["false_northing",0],UNIT["metre",1]]'
)

CrsSpec = str | int | None

Nodata = int | float | None


@dataclass(frozen=True)
class FixtureSpec:
    """A raster fixture as data, before it is a file.

    Every field is public because the escape hatch is the point: consumers who
    do not want this library's writer take ``.array`` and ``.transform`` and go.
    """

    array: np.ndarray
    transform: tuple[float, float, float, float, float, float]
    crs_wkt: str | None
    nodata: Nodata
    tags: dict[str, str] = field(default_factory=dict)
    band_tags: tuple[dict[str, str], ...] = ()
    band_descriptions: tuple[str, ...] = ()
    scales: tuple[float, ...] | None = None
    offsets: tuple[float, ...] | None = None

    @property
    def count(self) -> int:
        return int(self.array.shape[0])

    @property
    def height(self) -> int:
        return int(self.array.shape[1])

    @property
    def width(self) -> int:
        return int(self.array.shape[2])

    @property
    def dtype(self) -> str:
        return str(self.array.dtype)

    @property
    def profile(self) -> dict[str, Any]:
        """A rasterio-shaped profile dict, usable without importing rasterio."""
        profile: dict[str, Any] = {
            "driver": "GTiff",
            "height": self.height,
            "width": self.width,
            "count": self.count,
            "dtype": self.dtype,
            "transform": self.transform,
            "crs": self.crs_wkt,
        }
        if self.nodata is not None:
            profile["nodata"] = self.nodata
        return profile

    def write(self, path: str | Path, *, compress: str = "deflate") -> Path:
        """Write the fixture as a GeoTIFF.

        Imports rasterio lazily so the primitive itself stays importable — and
        usable through the escape hatch — in an environment that has no rasterio
        at all.
        """
        from geocase.raster._writer import write_geotiff

        return write_geotiff(self, Path(path), compress=compress)


def _resolve_crs(crs: CrsSpec | Literal["bogus", "no-authority"]) -> str | None:
    """Turn a CRS specification into WKT, or None.

    Accepts the adversarial forms deliberately:

    * ``None`` — no CRS at all; the fixture is ungeoreferenced.
    * ``"no-authority"`` — valid WKT whose ``GetAuthorityCode()`` is None.
    * ``"bogus"`` — a string that is not valid WKT and not a valid EPSG code.
    * ``4326`` / ``"4326"`` / ``"EPSG:4326"`` — the str-vs-int round-trip axis.
    """
    if crs is None:
        return None
    if crs == "no-authority":
        return _NO_AUTHORITY_WKT
    if crs == "bogus":
        return "NOT_A_REAL_CRS"
    if isinstance(crs, str) and crs.upper().startswith("GEOGCS"):
        return crs
    if isinstance(crs, str) and crs.upper().startswith("PROJCS"):
        return crs

    text = str(crs)
    code = text.split(":")[-1]
    if not code.isdigit():
        raise ValueError(
            f"crs={crs!r} is neither WKT, an EPSG code, nor one of the "
            f"adversarial forms 'bogus'/'no-authority'/None"
        )
    if code == "4326":
        return _WGS84_WKT
    # Any other EPSG code is emitted in the short authority form; the writer
    # resolves it. Kept as a string so the int-vs-str distinction survives to
    # the call site that cares about it.
    return f"EPSG:{code}"


def raster_fixture(
    *,
    bands: int = 1,
    dtype: str = "uint16",
    size: int | tuple[int, int] = DEFAULT_SIZE,
    crs: CrsSpec | Literal["bogus", "no-authority"] = "EPSG:32633",
    transform: tuple[float, float, float, float, float, float] | None = None,
    origin: tuple[float, float] = (500_000.0, 4_500_000.0),
    resolution: float | tuple[float, float] = 10.0,
    nodata: Nodata = None,
    nodata_border: int = 0,
    nodata_single_band: int | None = None,
    all_nodata: bool = False,
    fill: Literal["ramp", "constant", "zeros"] = "ramp",
    constant: float = 0.0,
    seed: int = 0,
    tags: dict[str, str] | None = None,
    band_descriptions: tuple[str, ...] = (),
    band_tags: tuple[dict[str, str], ...] = (),
    scales: tuple[float, ...] | None = None,
    offsets: tuple[float, ...] | None = None,
    values: np.ndarray | None = None,
) -> FixtureSpec:
    """Build a raster fixture with deliberately awkward metadata.

    Args:
        bands: Band count. Mismatching this against what code expects is the
            ``IndexError``-from-hardcoded-reordering axis.
        dtype: Any numpy dtype name.
        size: ``n`` for square, or ``(height, width)``. Values below
            :data:`MIN_USEFUL_SIZE` are allowed but warned about in the
            docstring rather than silently produced by default.
        crs: An EPSG code (int or str), WKT, ``None``, ``"bogus"``, or
            ``"no-authority"``.
        transform: A full affine as ``(a, b, c, d, e, f)``. Supply this for
            rotated or non-square-pixel geometry. Overrides *origin* and
            *resolution*.
        nodata: The declared nodata value, or ``None`` to declare none. Note
            that declaring none while writing nodata *pixels* is itself an
            adversarial case, and a common one in the wild.
        nodata_border: Width in pixels of a nodata frame around the scene. The
            axis with 3/3 evidence: interpolating resampling across this border
            without ``src_nodata``/``dst_nodata`` smears it into valid data.
        nodata_single_band: If set, writes the nodata value into exactly one
            band at an interior pixel, leaving the other bands valid there. This
            is what slips an "all bands are zero" nodata heuristic.
        all_nodata: Fill the entire array with nodata. Produces the degenerate
            statistics case — a ``max() == 0`` normalizer yielding silent NaN.
        fill: Valid-pixel pattern. ``"ramp"`` is deterministic and varies across
            the scene; ``"zeros"`` produces valid pixels that are legitimately
            zero, which is the ambiguity when nodata is also 0.
        values: Supply the valid-pixel content directly, instead of *fill*.
            Presets use this to write spec-accurate radiometry while still
            getting the nodata axes applied on top. Must match
            ``(bands, height, width)``.
        scales: Per-band scale factors, as GDAL's ``value = raw * scale +
            offset``.
        offsets: Per-band offsets, in the scaled unit.

    Returns:
        A :class:`FixtureSpec`. Call ``.write(path)`` for a GeoTIFF, or take
        ``.array`` / ``.transform`` / ``.crs_wkt`` and build the file yourself.
    """
    height, width = (size, size) if isinstance(size, int) else size

    if bands < 1:
        raise ValueError("bands must be >= 1")
    if height < 1 or width < 1:
        raise ValueError("size must be positive")
    if nodata_border < 0:
        raise ValueError("nodata_border must be >= 0")
    if nodata_border * 2 >= min(height, width) and nodata_border:
        raise ValueError(
            f"nodata_border={nodata_border} leaves no valid pixels in a "
            f"{height}x{width} fixture"
        )
    if (
        nodata_border or nodata_single_band is not None or all_nodata
    ) and nodata is None:
        raise ValueError(
            "nodata pixels were requested but nodata=None. Either declare the "
            "sentinel (nodata=0) or, to build the undeclared-nodata case "
            "deliberately, pass fill='zeros' and leave nodata=None."
        )

    if values is not None:
        expected = (bands, height, width)
        if values.shape != expected:
            raise ValueError(f"values has shape {values.shape}, expected {expected}")
        array = values.astype(dtype, copy=True)
    else:
        array = _fill_array(
            bands=bands,
            height=height,
            width=width,
            dtype=dtype,
            fill=fill,
            constant=constant,
            seed=seed,
        )

    if all_nodata:
        array[...] = nodata
    else:
        if nodata_border:
            array[:, :nodata_border, :] = nodata
            array[:, -nodata_border:, :] = nodata
            array[:, :, :nodata_border] = nodata
            array[:, :, -nodata_border:] = nodata
        if nodata_single_band is not None:
            if not 0 <= nodata_single_band < bands:
                raise ValueError(
                    f"nodata_single_band={nodata_single_band} is not a valid "
                    f"band index for bands={bands}"
                )
            row, col = height // 2, width // 2
            array[nodata_single_band, row, col] = nodata

    if transform is None:
        res_y, res_x = (
            (resolution, resolution)
            if isinstance(resolution, (int, float))
            else resolution
        )
        transform = (res_x, 0.0, origin[0], 0.0, -res_y, origin[1])

    return FixtureSpec(
        array=array,
        transform=transform,
        crs_wkt=_resolve_crs(crs),
        nodata=nodata,
        tags=dict(tags or {}),
        band_descriptions=band_descriptions,
        band_tags=band_tags,
        scales=scales,
        offsets=offsets,
    )


def _fill_array(
    *,
    bands: int,
    height: int,
    width: int,
    dtype: str,
    fill: str,
    constant: float,
    seed: int,
) -> np.ndarray:
    """Deterministic valid-pixel content. No RNG, so fixtures are reproducible."""
    if fill == "zeros":
        return np.zeros((bands, height, width), dtype=dtype)
    if fill == "constant":
        return np.full((bands, height, width), constant, dtype=dtype)
    if fill != "ramp":
        raise ValueError(f"unknown fill={fill!r}")

    rows = np.arange(height).reshape(-1, 1)
    cols = np.arange(width).reshape(1, -1)
    planes = []
    for b in range(bands):
        # Offset per band so band-ordering bugs are visible in the values.
        plane = (rows * 3 + cols * 5 + (b + seed) * 17) % 2000 + 1
        planes.append(plane)
    stacked = np.stack(planes)

    if np.issubdtype(np.dtype(dtype), np.floating):
        return (stacked / 10000.0).astype(dtype)
    return stacked.astype(dtype)
