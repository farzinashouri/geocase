"""Gates for the Files section of a generated case page.

A case page used to name its data files as inline code and link only
``source.url``, which points at the *upstream* dataset rather than at GeoCase's
own bytes. Guessing the repo path does not work either: the vector tree is
nested by geometry type. So the filenames are links, and this gate keeps them
that way.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

sys.path.insert(0, str(REPO_ROOT / "src"))

# mypy cannot see scripts/ (it is outside the gated `mypy src` scope).
from generate_catalog_pages import (  # type: ignore[import-not-found] # noqa: E402
    DEFAULT_REPO_URL,
    _render_case_page,
    _repo_relative,
)

from geocase.catalog.registry import get_registry  # noqa: E402
from geocase.catalog.roots import case_roots_by_id  # noqa: E402


def _a_case_with_a_directory() -> tuple[object, Path]:
    roots = case_roots_by_id()
    for case in sorted(get_registry().list_cases(), key=lambda case: case.id):
        directory = roots.get(case.id)
        if directory is not None:
            return case, directory
    raise AssertionError("no bundled case has an on-disk directory")


def _render(case: object, case_dir: Path | None) -> str:
    return _render_case_page(
        case,
        [case],
        "https://example.invalid",
        set(),
        case_dir,
        DEFAULT_REPO_URL,
    )


def test_repo_relative_keeps_the_nested_vector_layout() -> None:
    """``src/geocase/data/core/vector/polygon/<id>`` -- not a flattened guess."""
    _, case_dir = _a_case_with_a_directory()

    relative = _repo_relative(case_dir)

    assert relative.startswith("src/geocase/data/")
    assert relative.endswith(case_dir.name)
    assert "\\" not in relative, "the URL path must use posix separators"


def test_files_section_links_the_primary_file() -> None:
    case, case_dir = _a_case_with_a_directory()

    page = _render(case, case_dir)
    files = page.split("## Files", 1)[1]
    expected = (
        f"{DEFAULT_REPO_URL}/raw/main/{_repo_relative(case_dir)}/{case.files.primary}"
    )

    assert expected in files, "the primary file is not linked to its bytes"
    section = files.split("\n## ", 1)[0]
    assert f"- Primary: `{case.files.primary}`" not in section, (
        "the primary file is still a bare code span"
    )


def test_files_section_links_the_case_directory() -> None:
    case, case_dir = _a_case_with_a_directory()

    page = _render(case, case_dir)
    files = page.split("## Files", 1)[1]

    assert f"{DEFAULT_REPO_URL}/tree/main/{_repo_relative(case_dir)}" in files


def test_a_case_without_a_directory_falls_back_to_plain_code() -> None:
    """A manifest-backed (remote) case has no directory to link into."""
    case, _ = _a_case_with_a_directory()

    page = _render(case, None)
    files = page.split("## Files", 1)[1]

    assert f"`{case.files.primary}`" in files
    assert "/raw/main/" not in files
