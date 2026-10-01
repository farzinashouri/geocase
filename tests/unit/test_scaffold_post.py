"""scripts/scaffold_post.py writes draft posts from the registry (Plan 47 Phase 3)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from geocase.catalog.registry import get_registry
from geocase.catalog.risk_types import RISK_TYPE_DESCRIPTIONS

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "scaffold_post.py"


def _scaffold(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--output-dir", str(tmp_path), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _front_matter(text: str) -> dict[str, object]:
    return yaml.safe_load(text.split("---\n", 2)[1])


def test_spotlight_writes_a_prefilled_draft(tmp_path: Path) -> None:
    result = _scaffold(
        tmp_path,
        "--pillar",
        "spotlight",
        "--case",
        "geotiff_nodata_small",
        "--date",
        "2026-10-05",
    )
    assert result.returncode == 0, result.stderr

    post = tmp_path / "2026-10-05-geotiff-nodata-small.md"
    text = post.read_text(encoding="utf-8")
    case = get_registry().get("geotiff_nodata_small")
    meta = _front_matter(text)

    assert meta["description"] == " ".join((case.description or "").split())
    assert meta["cases"] == ["geotiff_nodata_small"]
    assert meta["risk_types"] == sorted(case.risk_types)
    assert meta["draft"] is True
    assert "previews/geotiff_nodata_small.png" in text
    assert "TODO:" in text
    # Ground-truth table.
    assert "expected_mean_masked" in text and "48.0787352901" in text
    assert "expected_mean_naive" in text and "-152.8628394157" in text
    assert "nodata_pixel_count" in text
    # Extent / region line.
    assert "**Where:**" in text
    assert case.extent is not None and f"{case.extent.west:.2f}°E" in text


def test_failure_mode_prefills_description_and_declaring_cases(tmp_path: Path) -> None:
    result = _scaffold(
        tmp_path,
        "--pillar",
        "failure-mode",
        "--risk",
        "nodata/ignored",
        "--date",
        "2026-10-06",
    )
    assert result.returncode == 0, result.stderr

    text = (tmp_path / "2026-10-06-nodata-ignored.md").read_text(encoding="utf-8")
    meta = _front_matter(text)
    declaring = sorted(
        c.id for c in get_registry().list_cases() if "nodata/ignored" in c.risk_types
    )

    assert meta["description"] == RISK_TYPE_DESCRIPTIONS["nodata/ignored"]
    assert meta["risk_types"] == ["nodata/ignored"]
    assert meta["cases"] == declaring
    assert meta["draft"] is True
    for case_id in declaring:
        assert case_id in text


def test_unknown_case_fails_without_writing(tmp_path: Path) -> None:
    result = _scaffold(
        tmp_path,
        "--pillar",
        "spotlight",
        "--case",
        "no_such_case",
        "--date",
        "2026-10-05",
    )
    assert result.returncode != 0
    assert list(tmp_path.iterdir()) == []


def test_refuses_to_overwrite_an_existing_post(tmp_path: Path) -> None:
    args = (
        "--pillar",
        "spotlight",
        "--case",
        "geotiff_nodata_small",
        "--date",
        "2026-10-05",
    )
    assert _scaffold(tmp_path, *args).returncode == 0
    assert _scaffold(tmp_path, *args).returncode != 0
