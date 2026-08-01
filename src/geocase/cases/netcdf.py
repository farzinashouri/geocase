"""NetCDF case — wraps a CF-compliant NetCDF dataset for xarray loading."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from geocase.cases.base import BaseCase
from geocase.catalog.models import CaseMetadata

if TYPE_CHECKING:
    import xarray as xr


class NetCDFCase(BaseCase):
    """A test case backed by a NetCDF file.

    Usage::

        case = NetCDFCase(metadata, root_dir)
        ds = case.load()
        assert "temperature" in ds.data_vars
    """

    def __init__(self, metadata: CaseMetadata, root_dir: Path) -> None:
        if metadata.category != "netcdf":
            raise ValueError(
                f"NetCDFCase requires category='netcdf', "
                f"got '{metadata.category}' for case '{metadata.id}'"
            )
        super().__init__(metadata, root_dir)

    def load(self, **kwargs: Any) -> xr.Dataset:
        """Load the primary NetCDF file into an xarray Dataset.

        Any extra *kwargs* are forwarded to
        :func:`xarray.open_dataset`.

        Returns:
            An :class:`xarray.Dataset`.

        Raises:
            FileNotFoundError: If the primary file does not exist.
            ImportError: If xarray is not installed.
        """
        import xarray  # lazy import

        path = self.primary_path
        if not path.is_file():
            raise FileNotFoundError(f"Primary data file not found: {path}")

        return xarray.open_dataset(path, **kwargs)
