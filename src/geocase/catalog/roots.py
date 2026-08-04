"""Case root resolution — where on disk a case id's data lives.

The registry answers *what a case is*; this module answers *where it is*, and
turns the pair into a runtime :class:`~geocase.cases.base.BaseCase`.

It lived inside ``pytest_plugin/fixtures.py`` until Step 15. The public API
needs the same mapping, and copying it would have created two ``lru_cache``s to
invalidate — one of which no ``reset_registry()`` call would ever reach.

Deliberately *not* re-exported from ``geocase.catalog``: this is the one catalog
module that imports ``geocase.cases``, and ``cases.base`` imports
``catalog.models``, so eager re-export makes the two packages circular. Import
``geocase.catalog.roots`` directly.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from geocase.cases.base import BaseCase
from geocase.cases.factory import create_case
from geocase.catalog.errors import remote_case_unavailable
from geocase.catalog.loader import load_case_index, load_case_metadata
from geocase.catalog.models import CaseMetadata
from geocase.catalog.registry import get_registry


def package_root() -> Path:
    """Return the installed ``geocase`` package directory."""
    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def case_roots_by_id() -> dict[str, Path]:
    """Map every indexed case id to the directory holding its ``case.yaml``.

    Built from ``case-index.yaml`` only, so manifest-backed (remote) case ids
    are deliberately absent — see :func:`materialize_case`.

    The result is cached; :func:`geocase.catalog.registry.reset_registry`
    clears it.
    """
    root = package_root()
    case_index_path = root / "metadata" / "case-index.yaml"
    rel_case_yaml_paths = load_case_index(case_index_path)

    out: dict[str, Path] = {}
    for rel in rel_case_yaml_paths:
        case_yaml = root / rel
        meta = load_case_metadata(case_yaml)
        out[meta.id] = case_yaml.parent
    return out


def materialize_case(meta: CaseMetadata) -> BaseCase:
    """Turn case metadata into a loadable case object.

    Raises:
        RemoteCaseUnavailableError: If the case is manifest-backed.
        KeyError: If the case id has no bundled directory.
    """
    # Checked before the cache lookup, not after: the cache is built from
    # case-index.yaml alone, so a manifest id would miss it and raise the
    # internal-sounding "No case root found" below — defeating the actionable
    # error the registry raises for exactly this situation.
    registry = get_registry()
    if registry.is_remote(meta.id):
        raise remote_case_unavailable(meta.id, registry.get_manifest(meta.id))

    roots = case_roots_by_id()
    try:
        root_dir = roots[meta.id]
    except KeyError as exc:
        raise KeyError(f"No case root found for case id '{meta.id}'") from exc
    return create_case(meta, root_dir)
