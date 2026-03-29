"""Cases module — runtime wrappers around geospatial test data."""

from geocase.cases.base import BaseCase
from geocase.cases.factory import create_case
from geocase.cases.netcdf import NetCDFCase
from geocase.cases.raster import RasterCase
from geocase.cases.vector import VectorCase

__all__ = [
    "BaseCase",
    "VectorCase",
    "RasterCase",
    "NetCDFCase",
    "create_case",
]
