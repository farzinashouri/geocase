"""Deduplicate shapely geometries by geometric equality."""

from shapely.geometry.base import BaseGeometry
from shapely import normalize


def dedupe_geoms(geoms: list[BaseGeometry]) -> list[BaseGeometry]:
    result = []
    for geom in geoms:
        normalized = normalize(geom)
        if not any(normalized.equals_exact(normalize(existing), tolerance=1e-9) for existing in result):
            result.append(geom)
    return result