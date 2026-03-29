"""Vector case — wraps a vector dataset for geopandas-based loading."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from geocase.cases.base import BaseCase
from geocase.catalog.models import CaseMetadata

if TYPE_CHECKING:
    import geopandas as gpd  # noqa: F811


class VectorCase(BaseCase):
    """A test case backed by a vector file (GeoJSON, GPKG, Shapefile, …).

    Usage::

        case = VectorCase(metadata, root_dir)
        gdf = case.load()
        assert gdf.crs is not None
    """

    def __init__(self, metadata: CaseMetadata, root_dir: Path) -> None:
        if metadata.category != "vector":
            raise ValueError(
                f"VectorCase requires category='vector', "
                f"got '{metadata.category}' for case '{metadata.id}'"
            )
        super().__init__(metadata, root_dir)

    def load(self, **kwargs: object) -> gpd.GeoDataFrame:
        """Load the primary vector file into a GeoDataFrame.

        Any extra *kwargs* are forwarded to
        :func:`geopandas.read_file`.

        Returns:
            A :class:`~geopandas.GeoDataFrame`.

        Raises:
            FileNotFoundError: If the primary file does not exist.
            ImportError: If geopandas is not installed.
        """
        import geopandas  # lazy import — keeps import time low

        path = self.primary_path
        if not path.is_file():
            raise FileNotFoundError(
                f"Primary data file not found: {path}"
            )

        return geopandas.read_file(path, **kwargs)
