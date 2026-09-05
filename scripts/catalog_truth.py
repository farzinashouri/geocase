"""Compute each bundled raster's ground truth from its real bytes.

A sibling of :mod:`catalog_extent`, and it follows the same conventions: the
geospatial imports are lazy, a load failure is an ordinary outcome rather than
a crash, and the emitted block carries a generated-by banner so a rewrite
replaces exactly what it wrote last time.

The distinction from every other generated field is *what* is generated. The
rest of the catalog declares what shape a case has -- its dtype, its band
count, its nodata tag. These four fields declare the **answer**:

- ``expected_mean_masked`` -- the mean over valid pixels, which is right.
- ``expected_mean_naive``  -- the mean including the sentinels, which is what a
  consumer that forgot to mask produces. The gap between the two *is* the
  defect the nodata cases exist to expose, so both are declared: a grader can
  tell "wrong" from "wrong in the specific way this case is about".
- ``nodata_pixel_count`` -- exact, so a masking bug is a count mismatch rather
  than a fractional drift in a mean.
- ``expected_bounds`` -- ``[west, south, east, north]`` in **the case's own
  CRS**. Not 4326: the top-level ``extent:`` is the WGS84 form, written by
  ``catalog_extent.py``, and conflating the two would put a wrong number in the
  one field whose entire purpose is to be right.

Scope is deliberately partial. The means are written only where the raster
declares a nodata value -- without one the two means are identical and the pair
says nothing. The count and the bounds are written for every readable bundled
raster.

Vector and netcdf cases are skipped: there is no mean to declare, and netcdf is
outside the ``catalog`` CI job's install set, the same cut
:mod:`geocase.catalog.content` makes.

Run ``python scripts/catalog_truth.py --write`` to populate the catalog, or
``--check`` to gate it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


#: Decimals kept in a written bound. Not six, as ``catalog_extent.py`` uses:
#: that field is a *placement*, where 10 cm of slack is meaningless, while this
#: one is the graded answer and is compared *relatively*. On a geographic case
#: whose box spans 0.005 degrees, six decimals is a 1e-4 relative error --
#: enough to fail the gate on a case that had not moved at all.
BOUNDS_PRECISION = 12

#: Decimals kept in a written mean. Deliberately finer than the bounds: the
#: mean is the graded number, and rounding it coarsely would make a consumer
#: that is genuinely right look marginally wrong.
MEAN_PRECISION = 10


def _round(value: float, precision: int) -> float:
    return round(float(value), precision)


def _is_nan(value: Any) -> bool:
    return isinstance(value, float) and value != value


def case_truth(case_id: str) -> dict[str, Any] | None:
    """Return the computed ground truth for *case_id*, or ``None``.

    ``None`` is an ordinary outcome: several bundled rasters are deliberately
    broken, and one that will not open has no answer to declare.
    """
    import numpy as np

    import geocase

    try:
        with geocase.load_case(case_id).open() as src:
            stacked = np.concatenate(
                [
                    np.asarray(src.read(band), dtype="float64").ravel()
                    for band in range(1, src.count + 1)
                ]
            )
            nodata = src.nodata
            bounds = tuple(float(value) for value in src.bounds)
    except Exception:
        return None

    truth: dict[str, Any] = {}

    if nodata is None:
        nodata_count = 0
    elif _is_nan(nodata):
        nodata_count = int(np.isnan(stacked).sum())
    else:
        nodata_count = int((stacked == nodata).sum())
    truth["nodata_pixel_count"] = nodata_count

    if nodata is not None:
        if _is_nan(nodata):
            valid = stacked[~np.isnan(stacked)]
            naive = float(np.nanmean(stacked)) if valid.size else float("nan")
        else:
            valid = stacked[stacked != nodata]
            naive = float(stacked.mean())
        if valid.size:
            # A fully-nodata raster has no masked mean to declare. Writing NaN
            # would be a number that no consumer can reproduce as an equality.
            truth["expected_mean_masked"] = _round(float(valid.mean()), MEAN_PRECISION)
            truth["expected_mean_naive"] = _round(naive, MEAN_PRECISION)

    if all(abs(value) != float("inf") and value == value for value in bounds):
        truth["expected_bounds"] = [_round(v, BOUNDS_PRECISION) for v in bounds]

    pairs = _pixel_world_pairs(case_id)
    if pairs is not None:
        truth["expected_pixel_world_pairs"] = pairs

    return truth


def _pixel_world_pairs(case_id: str) -> list[list[float]] | None:
    """Return ``[row, col, x, y]`` quadruples, for rotated rasters only.

    Plan 41 phase 3.3. Restricted to a **rotated** affine on purpose: on a
    north-up grid the round trip is ``origin + col * pixel``, which any reader
    gets right and which ``expected_bounds`` already pins. On a rotated one it
    is the operation that produced round 4's only irreducible finding, and
    ``expected_bounds`` is merely the axis-aligned envelope -- it says nothing
    about where an individual pixel went, which is precisely what was wrong.

    Two corners and the centre: the origin (where a north-up assumption still
    agrees), the far corner (where the two readings diverge most), and a
    mid-grid point (which no off-by-one at an edge can accidentally satisfy).
    """
    import geocase

    try:
        with geocase.load_case(case_id).open() as src:
            transform = src.transform
            if transform.b == 0 and transform.d == 0:
                return None
            samples = [
                (0, 0),
                (src.height - 1, src.width - 1),
                (src.height // 2, src.width // 2),
            ]
            return [
                [
                    float(row),
                    float(col),
                    _round(float(x), BOUNDS_PRECISION),
                    _round(float(y), BOUNDS_PRECISION),
                ]
                for row, col in samples
                for x, y in [src.xy(row, col)]
            ]
    except Exception:
        return None


# --- writing truth back into the catalog -------------------------------------


def _case_yaml_paths() -> list[tuple[Any, Path]]:
    """Pair each registered case with the YAML file that declares it.

    Resolved through the case index rather than by assuming ``<root>/case.yaml``:
    ``raster/footprint_edge_cases/`` holds five cases in one directory as
    ``case_<id>.yaml``, and the naive form silently skips all five.
    """
    from geocase.catalog.loader import load_case_index, load_case_metadata
    from geocase.catalog.registry import get_registry

    package_root = SRC_ROOT / "geocase"
    by_id: dict[str, Path] = {}
    for rel_path in load_case_index(package_root / "metadata" / "case-index.yaml"):
        path = package_root / rel_path
        if not path.exists():
            continue
        try:
            by_id[load_case_metadata(path).id] = path
        except Exception:
            continue

    return [
        (case, by_id[case.id])
        for case in get_registry().list_cases()
        if case.id in by_id
    ]


#: Marks the generated lines so a rewrite finds and replaces exactly what it
#: wrote last time. Indented, because the block lives *inside* ``assertions:``.
_TRUTH_HEADER = "  # Generated by scripts/catalog_truth.py -- do not edit by hand."
_TRUTH_NOTE = "  # expected_bounds is in the case CRS, not 4326 (see extent:)."

#: The keys this script owns, in the order they are written.
TRUTH_KEYS = (
    "expected_mean_masked",
    "expected_mean_naive",
    "nodata_pixel_count",
    "expected_bounds",
    "expected_pixel_world_pairs",
)


def _render_scalar(value: Any) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_render_scalar(v) for v in value) + "]"
    return repr(value)


def _render_truth_block(truth: dict[str, Any]) -> list[str]:
    lines = [_TRUTH_HEADER, _TRUTH_NOTE]
    for key in TRUTH_KEYS:
        if key not in truth:
            continue
        value = truth[key]
        # A list of lists goes one entry per line: four quadruples on one line
        # is unreadable, and these are meant to be read by a person deciding
        # whether to assert against them.
        if isinstance(value, list) and value and isinstance(value[0], list):
            lines.append(f"  {key}:")
            lines.extend(f"    - {_render_scalar(entry)}" for entry in value)
        else:
            lines.append(f"  {key}: {_render_scalar(value)}")
    return lines


def _strip_existing_truth(lines: list[str]) -> list[str]:
    """Drop a previously generated truth block, comments and all.

    Recognised by the generated header, so a hand-written value is left alone
    rather than silently rewritten -- and so a second ``--write`` is a no-op.
    """
    out: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index] == _TRUTH_HEADER:
            index += 1
            if index < len(lines) and lines[index] == _TRUTH_NOTE:
                index += 1
            while index < len(lines) and (
                any(lines[index].startswith(f"  {key}:") for key in TRUTH_KEYS)
                # Continuation lines of a list-of-lists value.
                or lines[index].startswith("    - ")
            ):
                index += 1
            while index < len(lines) and not lines[index].strip():
                index += 1
            while out and not out[-1].strip():
                out.pop()
            continue
        out.append(lines[index])
        index += 1
    return out


def _assertions_block_end(lines: list[str]) -> int | None:
    """Index just past the last line of the ``assertions:`` mapping.

    ``None`` when the file declares no assertions at all -- the truth has
    nowhere to live, and inventing an ``assertions:`` block from a generator
    would be writing structure rather than derived values.
    """
    starts = [i for i, line in enumerate(lines) if line.startswith("assertions:")]
    if not starts:
        return None
    index = starts[0] + 1
    end = index
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if not line.startswith((" ", "\t")):
            break
        index += 1
        end = index
    return end


def _write_truth(path: Path, truth: dict[str, Any] | None) -> bool:
    """Insert, replace, or remove the truth block in *path*. True if it changed.

    ``None`` *removes* a previously generated block. A case can stop having a
    computable answer -- a fixture is regenerated, a payload becomes unreadable
    -- and a stale answer surviving that is the exact drift the field exists to
    prevent.
    """
    original = path.read_text(encoding="utf-8")
    lines = _strip_existing_truth(original.splitlines())

    if truth:
        insert_at = _assertions_block_end(lines)
        if insert_at is not None:
            block = _render_truth_block(truth)
            lines = lines[:insert_at] + block + lines[insert_at:]

    text = "\n".join(lines).rstrip() + "\n"
    if text == original:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def _declared(case: Any) -> dict[str, Any]:
    """The truth a case currently declares, as the computed form would look."""
    hints = case.assertions
    out: dict[str, Any] = {}
    for key in TRUTH_KEYS:
        value = getattr(hints, key, None)
        if value is not None:
            out[key] = list(value) if isinstance(value, list) else value
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--write", action="store_true", help="write computed truth into case.yaml"
    )
    group.add_argument(
        "--check",
        action="store_true",
        help="fail if any declared value disagrees with the data",
    )
    args = parser.parse_args()

    written = 0
    skipped = 0
    stale: list[str] = []

    for case, path in _case_yaml_paths():
        category = str(getattr(case.category, "value", case.category))
        if category != "raster" or case.storage_class != "bundled":
            continue

        truth = case_truth(case.id)
        if not truth:
            skipped += 1

        if args.write:
            if _write_truth(path, truth):
                written += 1
        else:
            declared = _declared(case)
            computed = truth or {}
            if declared != computed:
                stale.append(f"  {case.id}: declared {declared}, computed {computed}")

    if args.check:
        if stale:
            print("Declared ground truth is out of date:")
            print("\n".join(stale))
            print("\nRun: python scripts/catalog_truth.py --write")
            return 1
        print(f"Ground truth up to date ({skipped} raster(s) unreadable)")
        return 0

    print(f"Wrote {written} truth block(s); {skipped} raster(s) skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
