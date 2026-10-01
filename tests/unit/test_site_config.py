"""The docs site's publishing surface: blog plugin, descriptions, post hygiene."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"


def _mkdocs_config() -> dict[str, Any]:
    # mkdocs.yml uses `!!python/name:` tags nowhere today, but be tolerant of
    # unknown tags so a future emoji/slugify line does not break this test.
    class _Loader(yaml.SafeLoader):
        pass

    _Loader.add_multi_constructor("", lambda loader, suffix, node: None)
    return yaml.load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"), Loader=_Loader)


def _nav_files(node: Any) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        return [f for item in node for f in _nav_files(item)]
    if isinstance(node, dict):
        return [f for value in node.values() for f in _nav_files(value)]
    return []


def _front_matter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    return yaml.safe_load(text[4:end]) or {}


def _plugin(config: dict[str, Any], name: str) -> dict[str, Any] | None:
    for entry in config["plugins"]:
        if entry == name:
            return {}
        if isinstance(entry, dict) and name in entry:
            return entry[name] or {}
    return None


def test_blog_plugin_is_configured() -> None:
    blog = _plugin(_mkdocs_config(), "blog")
    assert blog is not None, "the Material blog plugin is not in `plugins`"
    assert blog["blog_dir"] == "posts"
    assert blog["draft_if_future_date"] is True
    assert blog["post_url_format"] == "{slug}"


def test_articles_nav_entry_sits_between_validation_and_catalog() -> None:
    titles = [next(iter(item)) for item in _mkdocs_config()["nav"]]
    assert titles.index("Articles") == titles.index("Validation Report") + 1
    assert titles.index("Articles") + 1 == titles.index("Catalog")


def _published_pages() -> list[Path]:
    pages = {DOCS / name for name in _nav_files(_mkdocs_config()["nav"])}
    pages |= set((DOCS / "posts").glob("**/*.md"))
    return sorted(pages)


@pytest.mark.parametrize(
    "page", _published_pages(), ids=lambda p: str(p.relative_to(DOCS))
)
def test_published_page_has_description(page: Path) -> None:
    description = _front_matter(page).get("description")
    assert isinstance(description, str) and description.strip(), (
        f"{page.relative_to(ROOT)} has no `description:` front matter"
    )


@pytest.mark.parametrize(
    "post",
    sorted(p for p in (DOCS / "posts").glob("**/*.md") if p.name != "index.md"),
    ids=lambda p: p.name,
)
def test_post_with_todo_marker_is_a_draft(post: Path) -> None:
    if "TODO:" in post.read_text(encoding="utf-8"):
        assert _front_matter(post).get("draft") is True, (
            f"{post.name} has TODO: but is not `draft: true`"
        )
