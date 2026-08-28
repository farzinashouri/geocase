"""Generate the raster pixel previews shown on the catalog pages.

Writes one PNG per raster case declaring ``expected_shape`` into
``docs/_generated/catalog/previews/``, and removes previews whose case is
gone. The rendering itself lives in :mod:`catalog_raster`; this script is only
the file-level policy plus the ``--check`` gate.

``--check`` compares stored bytes against a fresh render and reports the drift
by case id. That is the whole reason previews are separate files rather than
base64 data-URIs in the markdown: the gate stays reviewable.

Needs rasterio (the ``catalog`` CI job installs ``.[raster,vector]``). Without
it every render returns ``None``, which the script reports rather than
silently writing an empty preview set.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
PREVIEW_ROOT = REPO_ROOT / "docs" / "_generated" / "catalog" / "previews"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog_raster import preview_cases, render_preview  # noqa: E402

from geocase.catalog.registry import get_registry  # noqa: E402


def build_previews(cases: list[Any]) -> tuple[dict[str, bytes], list[str]]:
    """Render every selected case. Returns ``(previews, unrenderable_ids)``."""
    previews: dict[str, bytes] = {}
    failed: list[str] = []
    for case in preview_cases(cases):
        png = render_preview(case)
        if png is None:
            failed.append(case.id)
        else:
            previews[f"{case.id}.png"] = png
    return previews, failed


def write_previews(previews: dict[str, bytes], output_root: Path) -> int:
    """Write previews to disk, removing stale ones. Returns the file count."""
    output_root.mkdir(parents=True, exist_ok=True)
    for existing in sorted(output_root.glob("*.png")):
        if existing.name not in previews:
            existing.unlink()

    for name, data in sorted(previews.items()):
        (output_root / name).write_bytes(data)
    return len(previews)


def check_previews(previews: dict[str, bytes], output_root: Path) -> list[str]:
    """Return human-readable drift descriptions, empty when in sync."""
    problems: list[str] = []
    for name, data in sorted(previews.items()):
        target = output_root / name
        if not target.exists():
            problems.append(f"missing: {name}")
        elif target.read_bytes() != data:
            problems.append(f"out of date: {name}")

    if output_root.exists():
        for existing in sorted(output_root.glob("*.png")):
            if existing.name not in previews:
                problems.append(f"stale: {existing.name}")
    return problems


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate raster pixel previews for the catalog pages."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PREVIEW_ROOT,
        help="Directory to write the preview PNGs into.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the stored previews match the fixtures instead of writing them.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    cases = sorted(get_registry().list_cases(), key=lambda case: case.id)
    selected = preview_cases(cases)
    if not selected:
        print("No raster cases declare expected_shape; nothing to preview.")
        return 1

    previews, failed = build_previews(cases)
    if not previews:
        # Every render failing means the reader stack is missing, not that
        # every fixture broke at once. Writing an empty preview set here would
        # delete the stored ones and the gate would then "pass" on nothing.
        print(
            f"None of the {len(selected)} raster cases could be rendered. This almost "
            "always means rasterio is missing -- run from the conda `geocase` "
            "environment, or install `.[raster,vector]`."
        )
        return 1
    if failed:
        print(f"warning: {len(failed)} case(s) could not be rendered: {failed}")

    if args.check:
        problems = check_previews(previews, args.output_root)
        if problems:
            print(f"Raster previews are out of date ({len(problems)} problem(s)):")
            for problem in problems:
                print(f"  - {problem}")
            print("\nRegenerate with: python scripts/generate_raster_previews.py")
            return 1
        print(f"Raster previews are up to date ({len(previews)} files).")
        return 0

    written = write_previews(previews, args.output_root)
    print(f"Wrote {written} raster previews to {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
