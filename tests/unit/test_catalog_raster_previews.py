"""Gates for the generated raster pixel previews (Plan 29 Phase 3).

Rasters cannot be previewed the way vectors are: real pixels are not text, so
the previews are PNG files under ``docs/_generated/catalog/previews/`` rather
than inline SVG. That choice is what keeps the ``--check`` gate reviewable --
a diff names the case whose bytes moved instead of showing an unreadable
base64 blob.

Three properties are gated here:

- **Coverage.** Every raster case declaring ``expected_shape`` has a preview.
  Rasters with no declared shape keep the band-stack schematic.
- **NoData is visually distinct.** A preview that paints NoData somewhere on
  the same ramp as valid pixels is worse than no preview: it asserts data
  where the fixture deliberately has none.
- **Determinism.** The stored bytes equal a fresh render's bytes, which is the
  property the ``--check`` gate rests on.
"""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
PREVIEWS = REPO_ROOT / "docs" / "_generated" / "catalog" / "previews"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

sys.path.insert(0, str(REPO_ROOT / "src"))

# mypy cannot see scripts/ (outside the gated `mypy src` scope).
from catalog_raster import (  # type: ignore[import-not-found] # noqa: E402
    NODATA_RGB,
    encode_png,
    preview_cases,
    render_preview,
)

from geocase.catalog.registry import get_registry  # noqa: E402


def _decode_png(data: bytes) -> tuple[int, int, list[tuple[int, int, int]]]:
    """Decode the narrow PNG dialect ``encode_png`` emits: 8-bit RGB, no filter."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos = 8
    width = height = 0
    idat = b""
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        payload = data[pos + 8 : pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, colour = struct.unpack(">IIBB", payload[:10])
            assert (depth, colour) == (8, 2), (depth, colour)
        elif kind == b"IDAT":
            idat += payload
        pos += 12 + length

    raw = zlib.decompress(idat)
    stride = width * 3
    pixels: list[tuple[int, int, int]] = []
    for row in range(height):
        start = row * (stride + 1)
        assert raw[start] == 0, "expected filter type 0"
        line = raw[start + 1 : start + 1 + stride]
        pixels.extend((line[i], line[i + 1], line[i + 2]) for i in range(0, stride, 3))
    return width, height, pixels


@pytest.fixture(scope="module")
def cases() -> list:
    return list(get_registry().list_cases())


def test_encode_png_round_trips() -> None:
    """The hand-rolled encoder must produce a PNG a decoder can read back."""
    rows = [[(255, 0, 0), (0, 255, 0)], [(0, 0, 255), (8, 8, 8)]]
    width, height, pixels = _decode_png(encode_png(rows))
    assert (width, height) == (2, 2)
    assert pixels == [px for row in rows for px in row]


def test_every_shaped_raster_case_has_a_preview(cases: list) -> None:
    """Coverage gate: a declared shape means the pixels are previewable."""
    expected = {case.id for case in preview_cases(cases)}
    assert expected, "no raster cases were selected for preview"
    missing = sorted(cid for cid in expected if not (PREVIEWS / f"{cid}.png").exists())
    assert missing == [], f"raster cases with no stored preview: {missing}"


def test_no_previews_for_unshaped_cases(cases: list) -> None:
    """Stale previews are drift: only the selected cases may have a file."""
    expected = {case.id for case in preview_cases(cases)}
    stale = sorted(
        path.stem for path in PREVIEWS.glob("*.png") if path.stem not in expected
    )
    assert stale == [], f"previews with no matching case: {stale}"


def test_nodata_renders_off_the_ramp() -> None:
    """``dem_nan_nodata_small`` carries NaN fill, which must not read as a value.

    Only 2 of its 256 pixels are NaN, so this is the real shape of the risk:
    the flagged pixels have to be visibly *not* on the ramp the other 254 use,
    or a reader sees an elevation where the fixture has nothing.
    """
    pytest.importorskip("rasterio")
    case = get_registry().get("dem_nan_nodata_small")
    png = render_preview(case)
    assert png is not None

    _, _, pixels = _decode_png(png)
    colours = set(pixels)
    assert NODATA_RGB in colours, "NaN pixels were painted as if they were data"
    # Everything else is grayscale, so the flag colour cannot be confused with
    # a dark or bright valid pixel.
    assert all(px == NODATA_RGB or px[0] == px[1] == px[2] for px in colours)


def test_valid_pixels_are_not_the_nodata_colour() -> None:
    """A case with no NoData must never paint the reserved flag colour."""
    pytest.importorskip("rasterio")
    case = get_registry().get("optical_rgb_small")
    png = render_preview(case)
    assert png is not None

    _, _, pixels = _decode_png(png)
    assert NODATA_RGB not in set(pixels)


def test_small_rasters_are_upscaled_without_blending() -> None:
    """16x16 payloads must be enlarged nearest-neighbour, not shown 16 px wide."""
    pytest.importorskip("rasterio")
    case = get_registry().get("optical_rgb_small")
    png = render_preview(case)
    assert png is not None

    width, height, pixels = _decode_png(png)
    assert width >= 128 and height >= 128
    # Nearest neighbour replicates each source pixel into a solid block, so
    # the distinct-colour count cannot exceed the 16x16 source's.
    assert len(set(pixels)) <= 16 * 16


def test_stored_previews_match_a_fresh_render(cases: list) -> None:
    """The ``--check`` property: the stored bytes equal a regeneration's bytes."""
    pytest.importorskip("rasterio")
    drift = []
    for case in preview_cases(cases):
        path = PREVIEWS / f"{case.id}.png"
        if not path.exists():
            continue
        if path.read_bytes() != render_preview(case):
            drift.append(case.id)
    assert drift == [], f"previews out of date: {drift}"
