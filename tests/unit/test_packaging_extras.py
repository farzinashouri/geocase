"""Tests for the packaging surface declared in ``pyproject.toml``.

These exist because `pip install "geocase[all]"` into a venv layered over a
working GDAL 3.6.2 / geopandas 0.12.2 stack pulled numpy 2.4.6 against scipy
1.10.1, shadowed the system geopandas and pandas, and left pandas unimportable
(``ImportError: C extension: None not built``). `pip install --no-deps geocase
geofacts` worked fine, which proves the core package needs none of it.

Two invariants follow, and both are asserted here rather than trusted:

1. the enumerate-and-resolve path stays dependency-free, so a user with an
   existing geo stack installs plain ``geocase`` and reads cases with the
   readers they already have;
2. every optional dependency carries an upper bound, so a future major of a
   reader cannot be resolved into an environment silently.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _ROOT / "pyproject.toml"
_SRC = _ROOT / "src" / "geocase"

#: The complete core runtime dependency set. Adding to this is a deliberate
#: decision, not a drive-by: it is what a GDAL-only consumer is asked to accept.
_ALLOWED_CORE = {"pydantic", "pyyaml", "geofacts"}

#: Optional readers. They may be imported only from ``cases/loaders/``, and
#: never at module scope in the catalog or API packages.
_OPTIONAL_READERS = {
    "geopandas",
    "rasterio",
    "xarray",
    "netCDF4",
    "pyarrow",
    "shapely",
}


@pytest.fixture(scope="module")
def pyproject() -> dict:
    return tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))


def _requirement_name(spec: str) -> str:
    """Return the distribution name from a PEP 508 requirement string."""
    name = spec.split(";", 1)[0].strip()
    for sep in ("<", ">", "=", "!", "~", "[", " "):
        name = name.split(sep, 1)[0]
    return name.strip().lower()


# ===================================================================
# Core dependencies
# ===================================================================


def test_core_dependencies_are_only_the_three_allowed(pyproject: dict) -> None:
    """The core install pulls in nothing that can read a geospatial file."""
    names = {_requirement_name(d) for d in pyproject["project"]["dependencies"]}
    assert names == _ALLOWED_CORE


def test_no_optional_reader_is_a_core_dependency(pyproject: dict) -> None:
    """No reader leaks into the core: resolving a case must not need one."""
    names = {_requirement_name(d) for d in pyproject["project"]["dependencies"]}
    leaked = names & {r.lower() for r in _OPTIONAL_READERS}
    assert not leaked, f"optional readers in core dependencies: {sorted(leaked)}"


# ===================================================================
# Upper bounds on every extra
# ===================================================================


def _third_party_extras(pyproject: dict) -> list[tuple[str, str]]:
    """Yield (group, requirement) for every non-self-referential extra entry."""
    groups = pyproject["project"]["optional-dependencies"]
    return [
        (group, spec)
        for group, specs in groups.items()
        for spec in specs
        if not spec.startswith("geocase[")
    ]


def test_every_optional_dependency_has_an_upper_bound(pyproject: dict) -> None:
    """An unbounded extra lets pip resolve a future major into a live stack."""
    unbounded = [
        f"{group}: {spec}"
        for group, spec in _third_party_extras(pyproject)
        if "<" not in spec
    ]
    assert not unbounded, "optional dependencies without an upper bound: " + repr(
        unbounded
    )


def test_reader_extras_are_bounded_at_the_next_major(pyproject: dict) -> None:
    """The four data-type groups are the ones that broke a real environment."""
    groups = pyproject["project"]["optional-dependencies"]
    for group in ("vector", "raster", "write", "netcdf"):
        for spec in groups[group]:
            assert "<" in spec, f"{group} entry {spec!r} has no upper bound"


# ===================================================================
# Import hygiene: the dependency-free path stays dependency-free
# ===================================================================


def _module_level_imports(path: Path) -> set[str]:
    """Return top-level (module-scope) imported root package names in a file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in tree.body:  # module scope only — function-local imports are fine
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
    return found


@pytest.mark.parametrize("package", ["catalog", "api"])
def test_catalog_and_api_do_not_import_optional_readers(package: str) -> None:
    """Enumerating and resolving cases must work with no reader installed.

    Optional imports belong in ``cases/loaders/``, which is reached only when a
    caller actually asks for the data.
    """
    offenders: list[str] = []
    for path in sorted((_SRC / package).rglob("*.py")):
        leaked = _module_level_imports(path) & _OPTIONAL_READERS
        if leaked:
            offenders.append(f"{path.relative_to(_ROOT)}: {sorted(leaked)}")
    assert not offenders, "module-level optional reader imports: " + repr(offenders)
