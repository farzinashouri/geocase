"""Hub and case pages link back to the posts that declare them (Plan 47 Phase 2)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

# mypy cannot see scripts/ (it is outside the gated `mypy src` scope).
from generate_catalog_pages import (  # type: ignore[import-not-found] # noqa: E402
    build_pages,
)

from geocase.catalog.registry import get_registry  # noqa: E402

POST = """\
---
title: NoData that is not -9999
description: A GeoTIFF whose NoData is ignored gives the wrong mean.
date: 2026-01-05
risk_types: [nodata/ignored]
cases: [geotiff_nodata_small]
---

# NoData that is not -9999
"""


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    posts = tmp_path_factory.mktemp("posts")
    (posts / "2026-01-05-nodata.md").write_text(POST, encoding="utf-8")
    (posts / "2026-01-06-draft.md").write_text(
        POST.replace("2026-01-05", "2026-01-06").replace(
            "---\n\n#", "draft: true\n---\n\n#"
        ),
        encoding="utf-8",
    )
    (posts / "index.md").write_text(
        "---\ndescription: x\n---\n# Articles\n", encoding="utf-8"
    )
    cases = get_registry().list_cases()
    return build_pages(cases, "https://example.invalid", posts_dir=posts)


def test_risk_hub_links_the_post(pages: dict[str, str]) -> None:
    page = pages["risk/nodata-ignored.md"]
    assert "## Read more" in page
    assert "(../../../posts/2026-01-05-nodata.md)" in page
    assert "NoData that is not -9999" in page


def test_case_page_links_the_post(pages: dict[str, str]) -> None:
    page = pages["cases/geotiff_nodata_small.md"]
    assert "## Read more" in page
    assert "(../../../posts/2026-01-05-nodata.md)" in page


def test_unrelated_pages_have_no_read_more(pages: dict[str, str]) -> None:
    assert "## Read more" not in pages["cases/geotiff_nodata_small_shifted.md"]
    assert "## Read more" not in pages["risk/nodata-nan-mishandled.md"]


def test_draft_posts_are_not_linked(pages: dict[str, str]) -> None:
    assert "2026-01-06-draft" not in pages["risk/nodata-ignored.md"]


def test_no_posts_dir_changes_nothing() -> None:
    cases = get_registry().list_cases()
    empty = build_pages(
        cases, "https://example.invalid", posts_dir=Path("/nonexistent")
    )
    assert not any("## Read more" in page for page in empty.values())
