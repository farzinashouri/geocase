"""YAML loading utilities for catalog metadata.

Reads case and suite YAML files and converts them into typed Pydantic models.
No selection logic, no registry logic, no file-format loading — just parsing.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from geocase.catalog.models import CaseMetadata, SuiteMetadata


def load_case_metadata(path: Path) -> CaseMetadata:
    """Load a case.yaml file and return a validated CaseMetadata model.

    Args:
        path: Path to a case.yaml file.

    Returns:
        Validated CaseMetadata instance.

    Raises:
        FileNotFoundError: If the path does not exist.
        yaml.YAMLError: If the file is not valid YAML.
        pydantic.ValidationError: If the YAML does not match the schema.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Case metadata file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ValueError(f"Empty YAML file: {path}")

    return CaseMetadata.model_validate(raw)


def load_suite_metadata(path: Path) -> SuiteMetadata:
    """Load a suite YAML file and return a validated SuiteMetadata model.

    Args:
        path: Path to a suite YAML file.

    Returns:
        Validated SuiteMetadata instance.

    Raises:
        FileNotFoundError: If the path does not exist.
        yaml.YAMLError: If the file is not valid YAML.
        pydantic.ValidationError: If the YAML does not match the schema.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Suite metadata file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ValueError(f"Empty YAML file: {path}")

    return SuiteMetadata.model_validate(raw)


def load_case_index(path: Path) -> list[str]:
    """Load case-index.yaml and return a list of relative case paths.

    Args:
        path: Path to case-index.yaml.

    Returns:
        List of relative paths to case.yaml files.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Case index file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if raw is None or "cases" not in raw:
        return []

    return [entry["path"] for entry in raw["cases"]]


def load_suite_index(path: Path) -> list[str]:
    """Load suite-index.yaml and return a list of relative suite paths.

    Args:
        path: Path to suite-index.yaml.

    Returns:
        List of relative paths to suite YAML files.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Suite index file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if raw is None or "suites" not in raw:
        return []

    return [entry["path"] for entry in raw["suites"]]
