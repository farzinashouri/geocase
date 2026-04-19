"""Vector case — wraps a vector dataset for geopandas-based loading."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

from geocase.cases.base import BaseCase
from geocase.catalog.models import CaseMetadata

if TYPE_CHECKING:
    import geopandas as gpd  # noqa: F811


class VectorCase(BaseCase):
    """A test case backed by a vector file (GeoJSON, GPKG, Shapefile, CSV_WKT, …).

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
        from shapely import wkt

        path = self.primary_path
        if not path.is_file():
            raise FileNotFoundError(
                f"Primary data file not found: {path}"
            )

        if self.metadata.format == "CSV_WKT":
            with path.open(newline="") as handle:
                csv_reader = csv.DictReader(handle)
                rows = list(csv_reader)

            if not rows:
                return geopandas.GeoDataFrame(geometry=[], crs=self.metadata.crs)

            columns = rows[0].keys()
            wkt_column = next(
                (candidate for candidate in ("wkt", "geometry_wkt", "geometry") if candidate in columns),
                None,
            )
            if wkt_column is None:
                raise ValueError(
                    f"CSV_WKT case '{self.id}' requires a WKT column named one of "
                    "'wkt', 'geometry_wkt', or 'geometry'"
                )

            attributes = []
            geometries = []
            for row in rows:
                geometry_wkt = row[wkt_column]
                geometries.append(wkt.loads(geometry_wkt))
                attributes.append({key: value for key, value in row.items() if key != wkt_column})

            return geopandas.GeoDataFrame(attributes, geometry=geometries, crs=self.metadata.crs)

        if self.metadata.format == "WKT":
            geometry = wkt.loads(path.read_text().strip())
            return geopandas.GeoDataFrame([{"name": self.id}], geometry=[geometry], crs=self.metadata.crs)

        if self.metadata.format == "WKB":
            from shapely import wkb

            raw = path.read_bytes()
            try:
                geometry = wkb.loads(raw)
            except Exception:
                geometry = wkb.loads(bytes.fromhex(raw.decode("ascii").strip()))
            return geopandas.GeoDataFrame([{"name": self.id}], geometry=[geometry], crs=self.metadata.crs)

        if self.metadata.format == "Parquet":
            return geopandas.read_parquet(path)

        if self.metadata.format == "Feather":
            return geopandas.read_feather(path)

        if self.metadata.format in {"Arrow", "GeoArrow"}:
            import pyarrow.ipc as ipc

            with ipc.open_file(str(path)) as arrow_reader:
                table = arrow_reader.read_all()
            return geopandas.GeoDataFrame.from_arrow(table)

        return geopandas.read_file(path, **kwargs)
