"""Build and validate ``src/geocase/metadata/case-index.yaml``.

Discovers case metadata files under ``src/geocase/data/core``, validates each
as ``CaseMetadata``, and writes a deterministic index used by the registry.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
PACKAGE_ROOT = SRC_ROOT / "geocase"
DATA_ROOT = PACKAGE_ROOT / "data" / "core"
INDEX_PATH = PACKAGE_ROOT / "metadata" / "case-index.yaml"

if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from geocase.catalog.loader import load_case_metadata  # noqa: E402


def _as_repo_relative(path: Path) -> str:
	"""Convert an absolute package path to a path relative to ``src/geocase``."""
	return path.relative_to(PACKAGE_ROOT).as_posix()


def discover_case_metadata_files(data_root: Path = DATA_ROOT) -> list[Path]:
	"""Return all valid case metadata YAML files under ``data_root``.

	Any ``*.yaml`` file that fails ``CaseMetadata`` validation is skipped.
	"""
	if not data_root.exists():
		raise FileNotFoundError(f"Data root not found: {data_root}")

	candidates = sorted(data_root.rglob("*.yaml"))
	valid_paths: list[Path] = []

	for path in candidates:
		try:
			load_case_metadata(path)
		except Exception:
			continue
		valid_paths.append(path)

	return sorted(valid_paths, key=lambda p: _as_repo_relative(p))


def build_case_index_payload(case_paths: list[Path]) -> dict[str, object]:
	"""Build the serializable case-index payload."""
	return {
		"schema_version": "1.0",
		"cases": [{"path": _as_repo_relative(path)} for path in case_paths],
	}


def read_existing_index(index_path: Path = INDEX_PATH) -> dict[str, object] | None:
	"""Read existing case index if present."""
	if not index_path.exists():
		return None
	with index_path.open() as handle:
		data = yaml.safe_load(handle)
	if data is None:
		return None
	if not isinstance(data, dict):
		raise ValueError(f"Invalid index format in {index_path}: expected mapping")
	return data


def write_case_index(payload: dict[str, object], index_path: Path = INDEX_PATH) -> None:
	"""Write the case index with deterministic YAML formatting."""
	index_path.parent.mkdir(parents=True, exist_ok=True)
	with index_path.open("w") as handle:
		yaml.safe_dump(payload, handle, sort_keys=False)


def parse_args() -> argparse.Namespace:
	"""Parse CLI arguments."""
	parser = argparse.ArgumentParser(
		description="Build src/geocase/metadata/case-index.yaml from case metadata files."
	)
	parser.add_argument(
		"--check",
		action="store_true",
		help="Exit non-zero if case-index.yaml is out of date instead of writing it.",
	)
	parser.add_argument(
		"--data-root",
		type=Path,
		default=DATA_ROOT,
		help="Root directory to search for case metadata YAML files.",
	)
	parser.add_argument(
		"--index-path",
		type=Path,
		default=INDEX_PATH,
		help="Output path for case-index.yaml.",
	)
	return parser.parse_args()


def main() -> int:
	"""CLI entrypoint."""
	args = parse_args()

	case_paths = discover_case_metadata_files(args.data_root)
	payload = build_case_index_payload(case_paths)

	existing = read_existing_index(args.index_path)

	if args.check:
		if existing != payload:
			print("case-index.yaml is out of date")
			return 1
		print("case-index.yaml is up to date")
		return 0

	write_case_index(payload, args.index_path)
	print(
		f"Wrote {args.index_path} with {len(case_paths)} cases discovered under {args.data_root}"
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
