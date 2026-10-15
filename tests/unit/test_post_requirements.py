"""Every post has the prose and the hub and case links Plan 51 Phase 3 requires."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

DOCS = Path(__file__).resolve().parents[2] / "docs"
POSTS = sorted(p for p in (DOCS / "posts").glob("*.md") if p.name != "index.md")


def _split(post: Path) -> tuple[dict[str, object], str]:
    _, front, body = post.read_text(encoding="utf-8").split("---", 2)
    return yaml.safe_load(front), body


def test_the_first_bug_story_post_exists() -> None:
    assert any("gdal-writes-1e-14" in p.name for p in POSTS)


@pytest.mark.parametrize("post", POSTS, ids=lambda p: p.name)
def test_post_has_prose_hub_and_case_links(post: Path) -> None:
    front, body = _split(post)
    prose = re.sub(r"```.*?```", "", body, flags=re.S)
    assert len(re.findall(r"[A-Za-z']+", prose)) >= 300
    assert re.search(r"_generated/catalog/risk/[a-z0-9-]+\.md", body)
    assert re.search(r"_generated/catalog/cases/[a-z0-9_]+\.md", body)
    for case_id in front["cases"]:
        assert f"cases/{case_id}.md" in body
    for target in re.findall(r"\]\((\.\./_generated/[^)#]+)\)", body):
        assert (post.parent / target).resolve().exists(), target
