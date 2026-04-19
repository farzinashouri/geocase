"""Diagnostic helpers for GeoCase pytest suites."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

import pytest

_DEFAULT_EXCLUDED_TAGS = {"vector", "raster", "polygon", "point", "geotiff", "crs"}
_DEFAULT_HIGHLIGHT_KEYS = (
    "crosses_dateline",
    "expected_utm_epsg",
    "expected_west_utm_epsg",
    "expected_east_utm_epsg",
    "expected_cluster_count",
    "expected_cluster_sizes",
    "max_distance_m",
)


def describe_case_data(
    data: Any,
    *,
    highlight_keys: Iterable[str] = _DEFAULT_HIGHLIGHT_KEYS,
) -> str:
    """Describe a case or metadata object without relying on fixture ids."""
    meta = getattr(data, "metadata", data)
    params = getattr(meta, "params", None)
    if params is None:
        params = getattr(data, "params", {})

    tags = sorted(getattr(meta, "tags", []) or [])
    risk_types = sorted(getattr(meta, "risk_types", []) or [])
    highlights = {key: params[key] for key in highlight_keys if key in params}

    parts = [
        f"category={getattr(meta, 'category', None)}",
        f"geometry_type={getattr(meta, 'geometry_type', None)}",
        f"crs={getattr(meta, 'crs', None)}",
        f"tags={tags}",
        f"risk_types={risk_types}",
    ]
    if highlights:
        parts.append(f"params={highlights}")
    return ", ".join(parts)


def failure_context(data: Any, message: str) -> str:
    """Attach a case description to a failure message."""
    return f"{message} [{describe_case_data(data)}]"


def case_label(
    data: Any,
    *,
    excluded_tags: set[str] | None = None,
) -> str:
    """Build a compact pytest parameter label from metadata fields."""
    meta = getattr(data, "metadata", data)
    filtered_tags = [
        tag
        for tag in sorted(getattr(meta, "tags", []) or [])
        if tag not in (excluded_tags or _DEFAULT_EXCLUDED_TAGS)
    ]
    base_parts = [
        str(getattr(meta, "category", "data")),
        str(getattr(meta, "geometry_type", "dataset") or "dataset").lower(),
    ]
    if getattr(meta, "crs", None):
        base_parts.append(str(meta.crs).replace("EPSG:", "epsg"))
    base_parts.extend(filtered_tags[:3] or ["default"])
    return "-".join(part.replace("_", "-") for part in base_parts)


def build_case_params(
    metadata: Iterable[Any],
    *,
    load_case: Callable[[str], Any],
    excluded_tags: set[str] | None = None,
) -> list[Any]:
    """Create pytest params with metadata-based labels instead of fixture ids."""
    labels_seen: dict[str, int] = {}
    params = []
    for meta in metadata:
        label = case_label(meta, excluded_tags=excluded_tags)
        labels_seen[label] = labels_seen.get(label, 0) + 1
        if labels_seen[label] > 1:
            label = f"{label}-{labels_seen[label]}"
        params.append(pytest.param(load_case(meta.id), id=label))
    return params
