"""The grading environment is recorded, so a re-grade knows what it is comparing.

Found by CI on 2026-09-20: ``test_committed_gradings_still_reproduce`` failed on
the 3.11 floor and passed on 3.14 for one trial. The cause was not the grader and
not the record — it was rasterio:

* ``rasterio.crs.CRS.equals()`` does not exist in **1.4.4** (the ``.venv`` floor)
  and does exist in **1.5.0** (the conda env).
* ``2026-09-13_claude-haiku-4-5_effort-low/trial2``'s ``gen_sample_at.py`` calls
  it, so the same bytes grade ``CORRECT`` under 1.5.0 and ``LOUD`` under 1.4.4.

An outcome that moves with the interpreter's package versions is not
reproducible, and the pin test cannot tell that case apart from a real grader
regression. So the environment that produced a grading is recorded beside it,
and the pin test compares only when the environment still matches.
"""

from __future__ import annotations

from geocase.benchmark.runner.record import GRADING_PACKAGES, grading_env


def test_grading_env_reports_a_version_for_every_grading_package():
    """Every package a grader can import is pinned in the record."""
    env = grading_env()
    for package in GRADING_PACKAGES:
        assert package in env, f"{package} is not recorded in the grading env"


def test_grading_env_records_the_python_version():
    """The interpreter is part of the environment, not just the packages."""
    import sys

    env = grading_env()
    expected = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert env["python"] == expected


def test_grading_env_records_the_installed_rasterio_version():
    """The package whose API drift caused the CI split is recorded by version."""
    rasterio = __import__("rasterio")
    assert grading_env()["rasterio"] == rasterio.__version__


def test_a_missing_package_is_recorded_as_none_not_omitted():
    """Absent is a fact about the environment and must be distinguishable.

    Omitting the key would make "not installed" indistinguishable from "this
    record predates the field", which is the ambiguity the record module already
    refuses elsewhere for ``preamble``.
    """
    env = grading_env(packages=["definitely_not_an_installed_package"])
    assert env["definitely_not_an_installed_package"] is None
