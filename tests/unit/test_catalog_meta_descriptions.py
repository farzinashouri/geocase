"""Gates for the SEO meta description of a generated case page.

A description longer than the meta limit used to be cut mid-sentence and end in
an ellipsis in search results. The generator now cuts at a sentence boundary, and
every bundled description has to open with a sentence that fits.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

sys.path.insert(0, str(REPO_ROOT / "src"))

# mypy cannot see scripts/ (it is outside the gated `mypy src` scope).
from generate_catalog_pages import (  # type: ignore[import-not-found] # noqa: E402
    MAX_META_DESCRIPTION,
    _meta_description,
)

from geocase.catalog.registry import get_registry  # noqa: E402


def _case(description: str) -> SimpleNamespace:
    return SimpleNamespace(
        id="x", description=description, behavioral_goal=None, title="T"
    )


def test_long_description_is_cut_at_a_sentence_boundary() -> None:
    first = "Reading the raw array gives wrong means because NoData is not masked."
    second = (
        "A second sentence that is long enough to push the text past the limit. " * 3
    )
    case = _case(first + " " + second)

    result = _meta_description(case)

    assert result.startswith(first)
    assert result.endswith(".")
    assert len(result) <= MAX_META_DESCRIPTION


def test_description_without_an_early_sentence_end_is_still_ellipsised() -> None:
    case = _case("word " * 100)

    result = _meta_description(case)

    assert result.endswith("…")
    assert len(result) <= MAX_META_DESCRIPTION


def test_no_bundled_case_has_an_ellipsised_meta_description() -> None:
    cut = [
        case.id
        for case in get_registry().list_cases()
        if _meta_description(case).endswith("…")
    ]

    assert cut == []
