"""Generate and verify SHA-256 checksums for bundled case data files.

Implements Step 3 of ``docs/plans/08-raster-action-plan.md``: a consistent
maintainer workflow for refreshing fixture checksums so that committed binary
fixtures (rasters in particular) do not silently drift.

For each case directory under ``src/geocase/data/core`` that contains a
``case.yaml``, this writes a sibling ``checksums.sha256`` file listing the
SHA-256 of every non-metadata data file in that directory.

Usage::

    python scripts/generate_checksums.py            # write checksums.sha256
    python scripts/generate_checksums.py --check     # verify, non-zero on drift
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "src" / "geocase" / "data" / "core"

CHECKSUM_FILE = "checksums.sha256"
# Files that describe rather than constitute the fixture payload.
_SKIP_NAMES = {CHECKSUM_FILE, "case.yaml", "notes.md", ".DS_Store"}


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 digest of *path*."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _data_files(case_dir: Path) -> list[Path]:
    """Return sorted payload files in *case_dir* (non-recursive)."""
    return sorted(
        p
        for p in case_dir.iterdir()
        if p.is_file() and p.name not in _SKIP_NAMES
    )


def compute_manifest(case_dir: Path) -> str:
    """Build the deterministic ``checksums.sha256`` text for *case_dir*."""
    lines = [f"{sha256_file(p)}  {p.name}" for p in _data_files(case_dir)]
    return "\n".join(lines) + ("\n" if lines else "")


def discover_case_dirs(data_root: Path) -> list[Path]:
    """Return all directories under *data_root* that hold a ``case.yaml``."""
    return sorted({p.parent for p in data_root.rglob("case.yaml")})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or verify SHA-256 checksums for bundled fixtures."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if any checksums.sha256 is missing or stale.",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DATA_ROOT,
        help="Root directory to scan for case.yaml directories.",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    case_dirs = discover_case_dirs(args.data_root)
    # Directories with no payload files (e.g. placeholder cases) are skipped.
    case_dirs = [d for d in case_dirs if _data_files(d)]

    if args.check:
        stale: list[str] = []
        for case_dir in case_dirs:
            expected = compute_manifest(case_dir)
            target = case_dir / CHECKSUM_FILE
            current = target.read_text() if target.exists() else None
            if current != expected:
                stale.append(str(case_dir.relative_to(REPO_ROOT)))
        if stale:
            print("Checksums out of date for:")
            for entry in stale:
                print(f"  {entry}")
            return 1
        print(f"Checksums up to date ({len(case_dirs)} case dirs)")
        return 0

    written = 0
    for case_dir in case_dirs:
        manifest = compute_manifest(case_dir)
        (case_dir / CHECKSUM_FILE).write_text(manifest)
        written += 1
    print(f"Wrote {written} {CHECKSUM_FILE} files under {args.data_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
