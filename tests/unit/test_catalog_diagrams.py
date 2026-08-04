"""Gates for the generated catalog schematics.

The class of bug these exist to catch: card anchors are *raw HTML*, so mkdocs
does not rewrite ``.md`` targets inside them the way it does for Markdown
links, and ``mkdocs build --strict`` does not validate href attributes in raw
HTML either. A wrong prefix there ships broken links that nothing else notices
-- which is exactly how Batch 5's 187 broken links happened.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
GENERATED = REPO_ROOT / "docs" / "_generated" / "catalog"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# mypy cannot see scripts/ (it is outside the gated `mypy src` scope), so the
# sys.path import above is invisible to it.
from catalog_svg import (  # type: ignore[import-not-found] # noqa: E402
    case_diagram,
    case_thumbnail,
)

sys.path.insert(0, str(REPO_ROOT / "src"))

from geocase.catalog.registry import get_registry  # noqa: E402


@pytest.fixture(scope="module")
def cases() -> list:
    return list(get_registry().list_cases())


def _category(case) -> str:
    return str(getattr(case.category, "value", case.category))


def test_every_vector_case_has_a_schematic(cases: list) -> None:
    """Vector cases all declare a geometry type, so all must draw."""
    missing = [
        case.id
        for case in cases
        if _category(case) == "vector" and not case_thumbnail(case)
    ]
    assert missing == [], f"vector cases with no schematic: {missing}"


def test_schematics_use_theme_variables_not_hex(cases: list) -> None:
    """A hard-coded colour would strand the diagram in one Material scheme."""
    for case in cases:
        svg = case_thumbnail(case)
        if svg:
            assert "#" not in svg, f"{case.id} hard-codes a colour"


def test_schematics_are_labelled(cases: list) -> None:
    """The diagrams carry information, so they need an accessible name."""
    for case in cases:
        svg = case_thumbnail(case)
        if svg:
            assert 'role="img"' in svg and "aria-label=" in svg, case.id


def test_caption_declares_the_metadata_provenance(cases: list) -> None:
    """Every schematic must say it is not a picture of the data."""
    for case in cases:
        figure = "".join(case_diagram(case))
        if figure:
            assert "Schematic:" in figure, case.id
            assert "not the fixture" in figure or "not from the pixels" in figure, (
                case.id
            )


def test_generated_card_links_have_no_markdown_targets() -> None:
    """Raw-HTML card hrefs must be resolved URLs, never ``.md`` paths."""
    offenders: list[str] = []
    for page in GENERATED.rglob("*.md"):
        for line in page.read_text(encoding="utf-8").splitlines():
            if 'class="gc-card"' in line and ".md" in line:
                offenders.append(f"{page.relative_to(REPO_ROOT)}: {line.strip()}")
    assert offenders == [], "card links must not use .md targets:\n" + "\n".join(
        offenders
    )


def test_generated_card_links_resolve_to_real_case_pages() -> None:
    """Each card must point at a case page that exists on disk."""
    case_dir = GENERATED / "cases"
    broken: list[str] = []
    for page in GENERATED.rglob("*.md"):
        for href in re.findall(
            r'class="gc-card" href="([^"]+)"', page.read_text(encoding="utf-8")
        ):
            case_id = href.rstrip("/").rsplit("/", 1)[-1]
            if not (case_dir / f"{case_id}.md").exists():
                broken.append(f"{page.relative_to(REPO_ROOT)} -> {href}")
    assert broken == [], "card links with no target page:\n" + "\n".join(broken)
