"""Verify built distribution artifacts before they are uploaded to PyPI.

PyPI artifacts are immutable: a wheel that installs cleanly but ships without
``geocase/data/**`` would be a permanently broken 1.0.0. This script is the gate
that answers that risk, and it is why the build is run locally before CI is
trusted.

Checks:
- The wheel contains every case data directory named by ``case-index.yaml``.
- The wheel contains ``geocase/metadata/case-index.yaml`` itself.
- The sdist contains ``src/geocase/data``, ``src/geocase/metadata``, and ``tests``.
- Neither artifact contains ``__pycache__``, ``*.pyc``, or ``.DS_Store``.
- Neither artifact exceeds its size ceiling.
- Artifact filename versions agree with each other, with the version declared
  in ``pyproject.toml``, and -- when ``--expected-version`` is passed -- with
  the release tag.

This script deliberately does not import ``geocase``. It verifies *artifacts*,
so requiring the package to be importable would couple the gate to whatever
happens to be installed on the runner; that coupling broke the 1.0.0rc1 build.
Its only third-party dependency is PyYAML, to read the case index.
"""

from __future__ import annotations

import argparse
import re
import tarfile
import tomllib
import zipfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
PACKAGE_ROOT = SRC_ROOT / "geocase"
CASE_INDEX_PATH = PACKAGE_ROOT / "metadata" / "case-index.yaml"

#: Hard ceiling on each artifact, in bytes.
#:
#: Measured at 1.0.0: wheel 456 KB, sdist 272 KB -- both *including* the full
#: 2.1 MB source data tree, which compresses roughly 5x. (`du -sh` reports the
#: tree as 4.2 MB, but that is 4 KB block padding across 572 tiny files, not
#: bytes that reach an artifact.) The release plan guessed 8 MB from an
#: assumption that the data sat on top of a 458 KB wheel; that would have let a
#: 4x regression through unnoticed. 2 MB caught an accidental bundling of
#: uncompressed fixtures or a stray extended-manifest payload with ~4x headroom.
#:
#: **The headroom is no longer 4x.** Plan 28 phase 3 added three 10,000-feature
#: vector cases, taking the payload tree to 5.1 MB and the wheel to **1.25 MB**
#: -- 61% of this ceiling still free, but a third of what it was. Those cases
#: buy something no small fixture can (a defect past a batch boundary), and the
#: budget was checked before they landed rather than after. But the next case of
#: that size is a decision about this ceiling, not a routine addition: at ~800 KB
#: of wheel per trio, one more would leave under 500 KB. That is the point to
#: put large cases behind a remote manifest instead of in the wheel.
#:
#: The ceiling itself is deliberately *not* raised to make room. It is the only
#: thing standing between the catalog and a slow slide into a distribution
#: nobody wants to install, and raising it whenever it binds would make it
#: decorative.
_MAX_ARTIFACT_BYTES: dict[str, int] = {
    "wheel": 2 * 1024 * 1024,
    "sdist": 2 * 1024 * 1024,
}

#: Files that must never ship. ``__pycache__`` is not named in any exclude list
#: in ``pyproject.toml`` -- hatchling's VCS-aware default drops it -- so this
#: check exists to prove that default rather than assume it.
_JUNK_PATTERN = re.compile(r"(^|/)(__pycache__/|\.DS_Store$)|\.pyc$")

_VERSION_RE = re.compile(
    r"^geocase-(?P<version>[^-]+?)(?:-py3-none-any\.whl|\.tar\.gz)$"
)


def _expected_case_files() -> list[str]:
    """Return the package-root-relative metadata path of every indexed case.

    Each entry is a path string such as
    ``data/core/raster/cog_multispectral_small/case.yaml``. These are checked
    file-by-file rather than by containing directory: ``footprint_edge_cases/``
    holds five ``*.yaml`` cases in a single directory, so a directory-level
    check would still pass with four of them deleted.

    The index is parsed here rather than via ``geocase.catalog.loader`` on
    purpose. Importing the package drags in ``geocase/__init__.py`` and its
    whole dependency chain, which made this gate fail on a clean CI runner
    with ``ModuleNotFoundError: No module named 'yaml'`` -- a verifier for
    *artifacts* should not depend on the package being importable at all.
    This mirrors ``load_case_index``, which is a dozen lines over the same
    file; ``tests/unit/test_verify_dist.py`` pins the two together.
    """
    if not CASE_INDEX_PATH.exists():
        raise FileNotFoundError(f"Case index file not found: {CASE_INDEX_PATH}")

    raw = yaml.safe_load(CASE_INDEX_PATH.read_text())
    if raw is None or "cases" not in raw:
        return []

    return [entry["path"] for entry in raw["cases"]]


def _wheel_names(wheel: Path) -> list[str]:
    with zipfile.ZipFile(wheel) as archive:
        return archive.namelist()


def _sdist_names(sdist: Path) -> list[str]:
    with tarfile.open(sdist, "r:gz") as archive:
        return archive.getnames()


def _strip_sdist_prefix(names: list[str]) -> list[str]:
    """Drop the ``geocase-<version>/`` root directory every sdist entry carries."""
    stripped: list[str] = []
    for name in names:
        _, _, rest = name.partition("/")
        if rest:
            stripped.append(rest)
    return stripped


def _check_junk(label: str, names: list[str], errors: list[str]) -> None:
    junk = sorted({name for name in names if _JUNK_PATTERN.search(name)})
    if junk:
        shown = ", ".join(junk[:5])
        more = f" (and {len(junk) - 5} more)" if len(junk) > 5 else ""
        errors.append(f"{label} contains excluded files: {shown}{more}")


def _check_size(label: str, path: Path, kind: str, errors: list[str]) -> int:
    size = path.stat().st_size
    ceiling = _MAX_ARTIFACT_BYTES[kind]
    if size > ceiling:
        errors.append(
            f"{label} is {size / 1024 / 1024:.2f} MB, over the "
            f"{ceiling / 1024 / 1024:.2f} MB ceiling"
        )
    return size


def _check_wheel_data(names: list[str], errors: list[str]) -> int:
    """Cross-check the wheel's data tree against the case index."""
    expected = _expected_case_files()
    present = set(names)

    missing = sorted(
        case_file for case_file in expected if f"geocase/{case_file}" not in present
    )
    if missing:
        shown = ", ".join(missing[:5])
        more = f" (and {len(missing) - 5} more)" if len(missing) > 5 else ""
        errors.append(
            f"wheel is missing {len(missing)} of {len(expected)} indexed cases: "
            f"{shown}{more}"
        )

    # A case is more than its metadata file -- catch a directory that shipped
    # `case.yaml` but none of its payload.
    empty = sorted(
        case_file
        for case_file in expected
        if not any(
            name.startswith(f"geocase/{case_file.rpartition('/')[0]}/")
            and not name.endswith((".yaml", ".md", ".sha256"))
            for name in present
        )
    )
    if empty:
        shown = ", ".join(empty[:5])
        more = f" (and {len(empty) - 5} more)" if len(empty) > 5 else ""
        errors.append(f"wheel ships metadata with no data payload for: {shown}{more}")

    if "geocase/metadata/case-index.yaml" not in present:
        errors.append("wheel is missing geocase/metadata/case-index.yaml")

    return len(expected)


def _check_sdist_contents(names: list[str], errors: list[str]) -> None:
    required = ("src/geocase/data/", "src/geocase/metadata/", "tests/")
    for prefix in required:
        if not any(name.startswith(prefix) for name in names):
            errors.append(f"sdist is missing {prefix}")


def _artifact_version(path: Path, errors: list[str]) -> str | None:
    match = _VERSION_RE.match(path.name)
    if match is None:
        errors.append(f"cannot parse a version from artifact filename {path.name}")
        return None
    return match.group("version")


def _declared_version(errors: list[str]) -> str | None:
    """Return ``project.version`` from pyproject.toml.

    ``tomllib`` is stdlib from 3.11, and the package requires >=3.11, so this
    adds no dependency to the gate.
    """
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.exists():
        errors.append(f"pyproject.toml not found at {pyproject}")
        return None

    data = tomllib.loads(pyproject.read_text())
    version = data.get("project", {}).get("version")
    if not isinstance(version, str):
        errors.append("pyproject.toml has no [project] version string")
        return None

    return version


def _check_versions(
    wheel: Path, sdist: Path, expected: str | None, errors: list[str]
) -> str | None:
    wheel_version = _artifact_version(wheel, errors)
    sdist_version = _artifact_version(sdist, errors)

    if wheel_version and sdist_version and wheel_version != sdist_version:
        errors.append(f"wheel version {wheel_version} != sdist version {sdist_version}")

    # Read the declared version from pyproject.toml rather than importing
    # `geocase.__version__`. That attribute resolves through
    # `importlib.metadata`, so it reports whatever is *installed* -- a stale
    # editable install makes this fail with a confusing mismatch, and on a
    # clean CI runner the import fails outright. pyproject.toml is the source
    # hatchling built these artifacts from, so it is the honest comparand.
    declared_version = _declared_version(errors)
    if wheel_version and declared_version and wheel_version != declared_version:
        errors.append(
            f"artifact version {wheel_version} != "
            f"pyproject.toml version {declared_version}"
        )

    if expected is not None:
        tag_version = expected.removeprefix("v")
        if wheel_version and wheel_version != tag_version:
            errors.append(
                f"artifact version {wheel_version} != tag version {tag_version}"
            )

    return wheel_version


def _find_one(dist_dir: Path, pattern: str, errors: list[str]) -> Path | None:
    matches = sorted(dist_dir.glob(pattern))
    if not matches:
        errors.append(f"no artifact matching {pattern} in {dist_dir}")
        return None
    if len(matches) > 1:
        names = ", ".join(path.name for path in matches)
        errors.append(
            f"expected exactly one {pattern} in {dist_dir}, "
            f"found {len(matches)}: {names} -- clear stale builds first"
        )
        return None
    return matches[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify built sdist/wheel artifacts before upload."
    )
    parser.add_argument(
        "dist_dir",
        type=Path,
        nargs="?",
        default=REPO_ROOT / "dist",
        help="Directory holding the built artifacts (default: ./dist)",
    )
    parser.add_argument(
        "--expected-version",
        help="Release version or tag (e.g. 1.0.0 or v1.0.0) the artifacts must match.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dist_dir: Path = args.dist_dir

    if not dist_dir.is_dir():
        print("Distribution verification failed:")
        print(f"{dist_dir} is not a directory")
        return 1

    errors: list[str] = []

    wheel = _find_one(dist_dir, "*.whl", errors)
    sdist = _find_one(dist_dir, "*.tar.gz", errors)
    if wheel is None or sdist is None:
        print("Distribution verification failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    wheel_names = _wheel_names(wheel)
    sdist_names = _strip_sdist_prefix(_sdist_names(sdist))

    indexed_cases = _check_wheel_data(wheel_names, errors)
    _check_sdist_contents(sdist_names, errors)
    _check_junk("wheel", wheel_names, errors)
    _check_junk("sdist", sdist_names, errors)
    wheel_size = _check_size("wheel", wheel, "wheel", errors)
    sdist_size = _check_size("sdist", sdist, "sdist", errors)
    version = _check_versions(wheel, sdist, args.expected_version, errors)

    if errors:
        print("Distribution verification failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Distribution verification passed")
    print(f"- Version: {version}")
    print(f"- Indexed cases present in wheel: {indexed_cases}")
    print(f"- Wheel: {wheel.name} ({wheel_size / 1024:.0f} KB)")
    print(f"- Sdist: {sdist.name} ({sdist_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
