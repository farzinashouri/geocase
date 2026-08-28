"""Render a raster case's real pixels as a small PNG preview.

Phase 3 of Plan 29. Vector previews could stay inline SVG because a projected
polygon is text; pixels cannot. Two encodings were on the table -- a base64
data-URI inside the generated markdown, or separate files -- and files won:
a base64 blob degrades the ``--check`` gate to "some bytes changed", while a
file diff names the case whose pixels moved and can be reviewed one at a time.

Three properties are load-bearing:

- **Deterministic bytes.** The PNG is written with a fixed zlib level and a
  fixed filter byte, so the same pixels always produce the same file. Without
  that the gate churns and stops meaning anything.
- **NoData is off the ramp.** :data:`NODATA_RGB` is a colour the grayscale and
  RGB paths can never emit, so "no data here" can never be mistaken for a
  valid value. The catalog exists to make NoData handling visible; a preview
  that hides it would be worse than none.
- **Nearest-neighbour upscaling.** Most payloads are 16x16 or 64x64. Shown at
  their true size they are invisible; shown blurred they imply a resolution
  the fixture does not have.

The PNG encoder is hand-rolled against ``zlib`` from the standard library
rather than pulling in Pillow: the catalog CI job installs ``.[raster,vector]``
and nothing more, and one more image dependency in that job buys nothing that
40 lines of ``struct`` do not.
"""

from __future__ import annotations

import struct
import zlib
from typing import Any


#: Reserved colour for NoData pixels. Deliberately a saturated magenta: it is
#: not on the grayscale ramp, and the RGB path clamps away from it (see
#: :func:`_reserve`), so its presence in a preview always means NoData.
NODATA_RGB = (255, 0, 255)

#: Preview edge length in pixels, before the aspect ratio of a non-square
#: raster is taken into account. Big enough that a 16x16 fixture reads as a
#: grid of blocks rather than a smudge.
TARGET_SIZE = 256

#: Grayscale ramp floor. Pure black reads as "missing" to most eyes, which is
#: the one thing this preview must reserve for NoData.
_RAMP_FLOOR = 24

#: zlib level, pinned. The default is already 6, but naming it here means a
#: library default changing under us cannot silently rewrite every preview.
_ZLIB_LEVEL = 6

Pixel = tuple[int, int, int]


def encode_png(rows: list[list[Pixel]]) -> bytes:
    """Encode 8-bit RGB rows as a PNG.

    Filter type 0 on every scanline: the images are tiny and blocky, so the
    compression a smarter filter would buy is not worth making the output
    depend on a heuristic that could change.
    """
    height = len(rows)
    width = len(rows[0]) if height else 0

    raw = bytearray()
    for row in rows:
        raw.append(0)
        for red, green, blue in row:
            raw.extend((red, green, blue))

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return (
            struct.pack(">I", len(payload))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    # bit depth 8, colour type 2 (truecolour), no interlace.
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            chunk(b"IHDR", header),
            chunk(b"IDAT", zlib.compress(bytes(raw), _ZLIB_LEVEL)),
            chunk(b"IEND", b""),
        ]
    )


def preview_cases(cases: list[Any]) -> list[Any]:
    """Return the raster cases that get a pixel preview, in id order.

    The selector is ``expected_shape``: a case that declares its pixel
    dimensions is one whose pixels the catalog is making a claim about. Rasters
    with no declared shape keep the metadata band-stack schematic, which is
    honest about being metadata.
    """
    selected = []
    for case in cases:
        if str(getattr(case.category, "value", case.category)) != "raster":
            continue
        assertions = getattr(case, "assertions", None)
        if assertions is not None and assertions.expected_shape:
            selected.append(case)
    return sorted(selected, key=lambda case: case.id)


def _reserve(value: int) -> int:
    """Clamp a channel so a valid pixel can never land on :data:`NODATA_RGB`.

    Only the extremes need moving: magenta is (255, 0, 255), so pulling both
    ends in by one leaves the flag colour unreachable from real data while
    costing less than half a percent of the dynamic range.
    """
    return min(254, max(1, value))


def _band_to_bytes(
    band: Any, valid: Any, span: tuple[float, float] | None = None
) -> Any:
    """Stretch a band's *valid* pixels to 0-255, as a uint8 array.

    ``span`` overrides the band's own min/max. The RGB path passes one shared
    span across all three channels on purpose: stretching each band to its own
    range would normalize away the relative brightness between them, and the
    relative brightness is precisely what an ``incorrect_band_order`` case
    exists to make visible.
    """
    import numpy as np

    finite = band[valid]
    if finite.size == 0:
        return np.zeros(band.shape, dtype="uint8")

    low, high = span if span is not None else (float(finite.min()), float(finite.max()))
    if high <= low:
        # A constant band. Mid-grey rather than a division by zero, and
        # deliberately not the ramp floor: "flat" and "dark" are different
        # facts about a fixture.
        return np.full(band.shape, 128, dtype="uint8")

    # Invalid pixels are painted over with NODATA_RGB later, but they must be
    # finite *before* the cast: casting NaN to uint8 is undefined and numpy
    # warns about it, which would put noise in every regeneration's output.
    filled = np.where(valid, band.astype("float64"), low)
    scaled = (filled - low) / (high - low)
    return np.clip(scaled * 255.0, 0, 255).astype("uint8")


def _valid_mask(array: Any, nodatavals: Any) -> Any:
    """True where a pixel carries data, across every band.

    A pixel is NoData if *any* band says so: an RGB composite with one band
    masked out is not a colour anybody should trust.
    """
    import numpy as np

    valid = np.ones(array.shape, dtype=bool)
    # NaN is NoData whether or not the file declares it -- float payloads in
    # this catalog use it as the convention (``dem_nan_nodata_small``).
    if np.issubdtype(array.dtype, np.floating):
        valid &= np.isfinite(array)

    for index, nodata in enumerate(nodatavals or ()):
        if nodata is None:
            continue
        if nodata != nodata:  # NaN, already covered by the isfinite pass.
            continue
        valid[index] &= array[index] != nodata

    return valid


def _composite(array: Any, nodatavals: Any) -> list[list[Pixel]]:
    """Turn a (bands, rows, cols) array into RGB rows with NoData flagged."""
    valid = _valid_mask(array, nodatavals)
    # One band masked anywhere masks the pixel everywhere, so the composite
    # never mixes a real value with a fill value.
    pixel_valid = valid.all(axis=0)

    if array.shape[0] >= 3:
        # First three bands, in file order. Not a "true colour" claim -- band
        # order is exactly the thing several cases exist to get wrong, so the
        # preview shows the order the file actually declares.
        rgb = array[:3]
        rgb_valid = valid[:3]
        finite = rgb[rgb_valid]
        span = (float(finite.min()), float(finite.max())) if finite.size else (0.0, 1.0)
        channels = [_band_to_bytes(rgb[i], rgb_valid[i], span) for i in range(3)]
    else:
        gray = _band_to_bytes(array[0], valid[0])
        # Lift off pure black so a dark valid pixel stays distinguishable
        # from the frame and from anything that reads as "absent".
        gray = (
            _RAMP_FLOOR + gray.astype("uint16") * (255 - _RAMP_FLOOR) // 255
        ).astype("uint8")
        channels = [gray, gray, gray]

    rows: list[list[Pixel]] = []
    for row in range(array.shape[1]):
        line: list[Pixel] = []
        for col in range(array.shape[2]):
            if not pixel_valid[row, col]:
                line.append(NODATA_RGB)
                continue
            line.append(
                (
                    _reserve(int(channels[0][row, col])),
                    _reserve(int(channels[1][row, col])),
                    _reserve(int(channels[2][row, col])),
                )
            )
        rows.append(line)
    return rows


def _upscale(rows: list[list[Pixel]], target: int = TARGET_SIZE) -> list[list[Pixel]]:
    """Enlarge nearest-neighbour by an integer factor, preserving aspect ratio.

    An integer factor specifically: a fractional resize would make some source
    pixels wider than others, which turns a uniform grid into a misleading one.
    """
    height = len(rows)
    width = len(rows[0]) if height else 0
    if not height or not width:
        return rows

    factor = max(1, target // max(width, height))
    if factor == 1:
        return rows

    out: list[list[Pixel]] = []
    for row in rows:
        wide = [pixel for pixel in row for _ in range(factor)]
        out.extend([list(wide) for _ in range(factor)])
    return out


def render_preview(case: Any) -> bytes | None:
    """Render one raster case's pixels as PNG bytes, or ``None`` if unreadable.

    ``None`` is a real outcome, not an error path: a case whose payload cannot
    be opened falls back to the band-stack schematic, exactly as the vector
    previews fall back to their archetype.
    """
    try:
        import numpy as np  # noqa: F401

        import geocase
    except ImportError:  # pragma: no cover - only hit in a bare checkout
        return None

    try:
        loaded = geocase.load_case(case.id)
        with loaded.open() as src:
            array = src.read()
            nodatavals = src.nodatavals
    except Exception:
        return None

    if array is None or array.ndim != 3 or array.shape[0] == 0:
        return None

    try:
        rows = _upscale(_composite(array, nodatavals))
    except Exception:
        return None
    if not rows:
        return None

    return encode_png(rows)
