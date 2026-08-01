"""Generate a markdown coverage matrix for core raster cases.

Mirrors ``scripts/generate_vector_coverage_matrix.py`` for the raster side
(Step 7 of ``docs/plans/archive/08-raster-action-plan.md``). Scans
``src/geocase/data/core/raster/**/case.yaml`` through the catalog loader and
emits a matrix covering product families, dtypes, delivery styles, and typed
expectation coverage.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
PACKAGE_ROOT = SRC_ROOT / "geocase"
RASTER_ROOT = PACKAGE_ROOT / "data" / "core" / "raster"
CASE_INDEX_PATH = PACKAGE_ROOT / "metadata" / "case-index.yaml"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from geocase.catalog.loader import load_case_index, load_case_metadata  # noqa: E402

PRODUCT_FAMILIES: list[tuple[str, list[str]]] = [
    ("Optical / RGB", ["optical", "rgb"]),
    ("Multispectral", ["multispectral", "sentinel2", "sentinel-2"]),
    ("Mask", ["mask", "water", "landcover"]),
    ("DEM / Terrain", ["dem", "terrain", "elevation"]),
    ("Derived index (NDVI)", ["ndvi", "index"]),
    ("SAR / Radar", ["sar", "radar"]),
    ("COG", ["cog"]),
]

DTYPE_TARGETS = ["uint8", "uint16", "int16", "int32", "float32", "float64"]

DELIVERY_STYLES: list[tuple[str, list[str]]] = [
    ("Single-file GeoTIFF", ["delivery:single-file", "single-file"]),
    ("Internal overviews / COG", ["cog", "overviews"]),
    ("External overviews", ["external_overviews", "external-overviews"]),
    ("Compression variants", ["compression", "deflate", "lzw"]),
]


def _load_raster_metadata(raster_root: Path) -> list[object]:
    """Load all valid raster case metadata, skipping placeholder/stub files.

    Globs ``*.yaml``, not ``case.yaml``: the five
    ``footprint_edge_cases/case_*.yaml`` entries share one directory, so
    matching only ``case.yaml`` silently reported 25 cases against an actual
    30 — and the generated artifact is gated by ``git diff --exit-code``, so
    CI enforced the wrong number.
    """
    entries: list[object] = []
    for case_yaml in sorted(raster_root.rglob("*.yaml")):
        try:
            meta = load_case_metadata(case_yaml)
        except Exception:
            # Placeholder/deferred stubs are skipped, as are any non-case
            # YAML files that happen to live under the raster tree.
            continue
        if getattr(meta, "category", None) != "raster":
            continue
        entries.append(meta)
    return entries


def _raster_ids_from_case_index() -> set[str] | None:
    """Return the raster case ids recorded in ``case-index.yaml``.

    Returns ``None`` when the index cannot be read, so a caller working from
    a custom ``--raster-root`` is not blocked by a missing index.
    """
    if not CASE_INDEX_PATH.exists():
        return None
    ids: set[str] = set()
    for rel in load_case_index(CASE_INDEX_PATH):
        meta = load_case_metadata(PACKAGE_ROOT / rel)
        if meta.category == "raster":
            ids.add(meta.id)
    return ids


def _check_against_case_index(entries: list[object]) -> str | None:
    """Return an error message if discovery disagrees with the case index.

    The discovery glob and the registry's index are two independent walks of
    the same tree. Nothing was comparing them, which is exactly how the
    undercount survived: the matrix said 25, the index said 30, and both were
    gated. This makes the disagreement itself a failure.
    """
    indexed = _raster_ids_from_case_index()
    if indexed is None:
        return None

    scanned = {str(getattr(meta, "id", "")) for meta in entries}
    if scanned == indexed:
        return None

    missing = sorted(indexed - scanned)
    extra = sorted(scanned - indexed)
    parts = [
        f"Raster discovery disagrees with {CASE_INDEX_PATH.name}: "
        f"scanned {len(scanned)}, indexed {len(indexed)}."
    ]
    if missing:
        parts.append(f"In the index but not scanned: {missing}")
    if extra:
        parts.append(f"Scanned but not in the index: {extra}")
    parts.append("Run: python scripts/build_case_index.py")
    return " ".join(parts)


def _case_text(meta: object) -> str:
    tags = " ".join(getattr(meta, "tags", []))
    risks = " ".join(getattr(meta, "risk_types", []))
    description = getattr(meta, "description", "") or ""
    title = getattr(meta, "title", "") or ""
    identifier = getattr(meta, "id", "") or ""
    return f"{identifier} {title} {description} {tags} {risks}".lower()


def _has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _present(flag: bool) -> str:
    return "✅ present" if flag else "❌ missing"


def _build_markdown(entries: list[object]) -> str:
    texts = [_case_text(meta) for meta in entries]

    family_counts = {
        label: sum(1 for text in texts if _has_any(text, terms))
        for label, terms in PRODUCT_FAMILIES
    }
    dtype_present = {
        dtype: any(
            getattr(getattr(meta, "assertions", None), "expected_dtype", None)
            == dtype
            for meta in entries
        )
        for dtype in DTYPE_TARGETS
    }
    delivery_present = {
        label: any(_has_any(text, terms) for text in texts)
        for label, terms in DELIVERY_STYLES
    }

    typed_band_count = sum(
        1
        for meta in entries
        if getattr(getattr(meta, "assertions", None), "expected_band_count", None)
        is not None
    )

    lines: list[str] = []
    lines.append("### Raster coverage matrix (current vs target)")
    lines.append("")
    lines.append(f"Total bundled raster cases scanned: **{len(entries)}**.")
    lines.append(
        f"Cases declaring typed band-count expectations: "
        f"**{typed_band_count}/{len(entries)}**."
    )
    lines.append("")
    lines.append("#### A) Product families")
    lines.append("")
    lines.append("| Product family | Current coverage | Target |")
    lines.append("|---|---:|---:|")
    for label, _terms in PRODUCT_FAMILIES:
        count = family_counts[label]
        status = f"✅ {count} case(s)" if count else "❌ missing"
        lines.append(f"| {label} | {status} | ✅ required |")

    lines.append("")
    lines.append("#### B) Data types")
    lines.append("")
    lines.append("| dtype | Current coverage | Target |")
    lines.append("|---|---:|---:|")
    for dtype in DTYPE_TARGETS:
        lines.append(f"| {dtype} | {_present(dtype_present[dtype])} | ✅ required |")

    lines.append("")
    lines.append("#### C) Delivery styles")
    lines.append("")
    lines.append("| Delivery style | Current coverage | Target |")
    lines.append("|---|---:|---:|")
    for label, _terms in DELIVERY_STYLES:
        lines.append(f"| {label} | {_present(delivery_present[label])} | ✅ required |")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate raster coverage matrix markdown."
    )
    parser.add_argument(
        "--raster-root",
        type=Path,
        default=RASTER_ROOT,
        help="Root directory containing raster case folders.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output markdown file path. If omitted, prints to stdout.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.raster_root.exists():
        print(f"Raster root not found: {args.raster_root}")
        return 1

    entries = _load_raster_metadata(args.raster_root)
    if not entries:
        print("No raster case metadata found.")
        return 1

    if args.raster_root == RASTER_ROOT:
        mismatch = _check_against_case_index(entries)
        if mismatch is not None:
            print(mismatch)
            return 1

    markdown = _build_markdown(entries)

    if args.output is None:
        print(markdown, end="")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown)
    print(f"Wrote coverage matrix markdown to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
