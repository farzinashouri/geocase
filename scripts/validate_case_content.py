"""Validate that every bundled case's declared assertions match its real bytes.

The companion to ``validate_catalog.py``, split by dependency profile:

* ``validate_catalog.py`` stays reader-dependency-free (it imports only
  ``geocase.catalog.*``), so it keeps running in the ``tests`` CI job and in a
  contributor's ``.venv``. It checks schema, file existence and payload size.
* This script opens the data, so it needs rasterio/geopandas/GDAL and runs in
  the ``catalog`` CI job inside the GDAL image. A gate on plain ``ubuntu-latest``
  would skip exactly the cases most likely to drift.

The checks themselves live in :mod:`geocase.catalog.content` so the pytest job
can unit-test them without this script.

Exits non-zero if any case's declaration is not backed by its data.

See docs/plans/28-validate-geocase.md, Phase 1.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
PACKAGE_ROOT = SRC_ROOT / "geocase"
CASE_INDEX_PATH = PACKAGE_ROOT / "metadata" / "case-index.yaml"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from geocase.catalog.content import check_case_content  # noqa: E402
from geocase.catalog.loader import load_case_index, load_case_metadata  # noqa: E402
from geocase.catalog.models import CaseMetadata  # noqa: E402


def _iter_cases(case_index: Path):
    """Yield ``(case_dir, metadata)`` for every case in the index."""
    for rel in load_case_index(case_index):
        case_yaml = PACKAGE_ROOT / rel
        metadata = load_case_metadata(case_yaml)
        yield case_yaml.parent, metadata


def _selected(
    metadata: CaseMetadata, only: str | None, category: str | None
) -> bool:
    if only is not None and metadata.id != only:
        return False
    if category is not None and metadata.category != category:
        return False
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check every bundled case's declared assertions against its actual "
            "pixels and features."
        )
    )
    parser.add_argument(
        "--case-index",
        type=Path,
        default=CASE_INDEX_PATH,
        help="Path to case-index.yaml",
    )
    parser.add_argument("--only", help="Check a single case id.")
    parser.add_argument(
        "--category",
        choices=["vector", "raster", "netcdf", "satellite"],
        help="Restrict the check to one category.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit machine-readable JSON instead of the per-case report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    checked = 0
    skipped = 0
    failures: dict[str, list[str]] = {}

    for case_dir, metadata in _iter_cases(args.case_index):
        if not _selected(metadata, args.only, args.category):
            continue
        if metadata.storage_class != "bundled":
            skipped += 1
            continue

        checked += 1
        errors = check_case_content(case_dir, metadata)
        if errors:
            failures[metadata.id] = errors

    if args.as_json:
        print(
            json.dumps(
                {
                    "checked": checked,
                    "skipped": skipped,
                    "failed": len(failures),
                    "errors": failures,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1 if failures else 0

    if failures:
        print("Case content validation failed:")
        for case_id in sorted(failures):
            for error in failures[case_id]:
                print(f"  {error}")
        print()
        print(f"- Cases checked: {checked}")
        print(f"- Cases failing: {len(failures)}")
        return 1

    print("Case content validation passed")
    print(f"- Cases checked: {checked}")
    print(f"- Cases skipped (not bundled): {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
