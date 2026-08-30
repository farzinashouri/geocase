"""Reproducible generator for the bundled NetCDF fixtures.

Until Plan 34 this file did not exist, and ``latlon_sample.nc`` was the only
fixture in the repository that could not be rebuilt. It arrived in a single
"Analyse structure" commit whose temperature values were unseeded random
floats; 400 seed and distribution combinations were searched without a match.
Every other NetCDF gap was blocked behind that, because a catalog cannot gate
the contents of a file it cannot regenerate.

Usage::

    python scripts/generate_netcdf_fixtures.py            # write all fixtures
    python scripts/generate_netcdf_fixtures.py --check    # verify up to date

As with the raster and vector generators, only the primary data files are
written here; ``case.yaml`` and ``notes.md`` are authored alongside and indexed
via ``scripts/build_case_index.py``.

Why ``--check`` compares *semantics* and not bytes
--------------------------------------------------
``scripts/generate_raster_fixtures.py`` can byte-compare a regenerated GeoTIFF
against the committed one. NetCDF cannot be held to that standard: the files
are HDF5 underneath, and HDF5 stamps the writing library's version string into
the superblock and orders chunks by build configuration. A byte gate would
therefore go red on a dependency bump that changed no data at all -- reporting
drift where there is none, which is the failure mode that trains people to
ignore a gate.

``scripts/generate_vector_fixtures.py`` already makes exactly this argument for
GPKG, SpatiaLite and Parquet, and resolves it the same way: compare what a
consumer can actually observe. Here that is
:func:`_semantic_signature` -- dimensions and their sizes, variable names with
dtypes and packing attributes, coordinate values to 9 decimal places, and the
global attributes.

The engine is pinned explicitly. Letting xarray auto-select would make the
committed bytes depend on which of netCDF4 and h5netcdf happens to be
installed, which defeats the reproducibility this module exists to buy.

See docs/plans/34-close-reviewed-catalog-gaps.md, Phase 1.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
NETCDF_ROOT = REPO_ROOT / "src" / "geocase" / "data" / "core" / "netcdf"

#: The write engine, pinned rather than auto-selected -- see the module
#: docstring. netCDF4 is what both the conda environment and the catalog CI job
#: install, and it resolves against the job's ``numpy<2`` pin.
_ENGINE = "netcdf4"

#: Decimal places for coordinate comparison in :func:`_semantic_signature`.
#: Matches ``_PROCEDURAL_PRECISION`` in the vector generator and ``PRECISION``
#: in ``catalog_extent.py`` so the three gates agree on what "same" means.
_PRECISION = 9


@dataclass
class NetCDFSpec:
    """One bundled NetCDF fixture, built from deterministic arrays."""

    #: Case id, and by default the directory under ``NETCDF_ROOT``.
    case_id: str
    #: File name of the primary, as named in ``case.yaml``.
    primary: str
    #: Coordinate variables, in the order they should appear.
    coords: dict[str, np.ndarray]
    #: Data variables as ``name -> (dimension names, values)``. The dimension
    #: tuple is load-bearing: it is what a dimension-ordering case asserts.
    variables: dict[str, tuple[tuple[str, ...], np.ndarray]]
    #: Per-variable attributes (``units``, ``long_name``, ...).
    var_attrs: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: Per-variable encoding (``_FillValue``, ``scale_factor``, ``dtype``, ...).
    #: Set explicitly for packed variables: left to xarray, packing is
    #: re-derived on write and the fixture's whole point becomes an artefact of
    #: the library version.
    encoding: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: Dataset-level attributes.
    global_attrs: dict[str, Any] = field(default_factory=dict)


def _latlon_small_spec() -> NetCDFSpec:
    """The replacement for the unreproducible original.

    Shape, dtype, ``_FillValue`` and both fill positions are preserved exactly,
    so every assertion the case already declared still holds. Only the
    temperature values change -- from unrecoverable noise to a deterministic
    ramp. See Plan 34 section 1.4 for why replacement was chosen over leaving
    the binary in place.
    """
    latitude = np.linspace(40.0, 50.0, 5)
    longitude = np.linspace(10.0, 20.0, 8)

    # A separable ramp: increases with both latitude and longitude, so a
    # transposed or flipped read is visible in the values rather than only in
    # the shape. Range stays inside the original's plausible [10, 35] degrees.
    lat_term = np.linspace(0.0, 10.0, 5)[:, None]
    lon_term = np.linspace(0.0, 12.0, 8)[None, :]
    temperature = 12.0 + lat_term + lon_term

    # The two fill cells the original carried, at the same positions.
    temperature[0, 0] = np.nan
    temperature[3, 5] = np.nan

    return NetCDFSpec(
        case_id="latlon_small",
        primary="latlon_sample.nc",
        coords={"latitude": latitude, "longitude": longitude},
        variables={"temperature": (("latitude", "longitude"), temperature)},
        var_attrs={
            "temperature": {
                "units": "degC",
                "long_name": "Near-surface air temperature",
            },
            "latitude": {"units": "degrees_north", "standard_name": "latitude"},
            "longitude": {"units": "degrees_east", "standard_name": "longitude"},
        },
        encoding={"temperature": {"_FillValue": -9999.0, "dtype": "float64"}},
        global_attrs={
            "Conventions": "CF-1.8",
            "title": "GeoCase test: lat/lon small",
        },
    )


def _ndvi_packed_spec() -> NetCDFSpec:
    """Packed int16 NDVI — the same failure mode as the GeoTIFF analogue.

    Stored as ``int16`` scaled by 1e-4, so a consumer that ignores
    ``scale_factor`` reads plausible-looking integers in the thousands instead
    of NDVI in [-1, 1]. Nothing errors; the numbers are simply wrong by four
    orders of magnitude.

    Deliberately mirrors the raster case ``ndvi_scaled_int16_small``, giving
    the catalog a cross-container pair for one failure mode. The encoding is
    set explicitly: left to xarray it is re-derived on write, and the fixture's
    whole point becomes an artefact of the library version.
    """
    latitude = np.linspace(45.0, 50.0, 6)
    longitude = np.linspace(5.0, 14.0, 10)

    # *Physical* values, in NDVI's natural [-1, 1]. xarray applies the encoding
    # below on write, so the file holds int16 storage values spanning
    # [-10000, 10000]. Handing it pre-packed integers instead makes it try to
    # pack them a second time and fail on the dtype cast -- the values here are
    # what a user means, not what the file stores.
    physical = np.linspace(-1.0, 1.0, 60).reshape(6, 10)
    physical[0, 0] = np.nan  # becomes the _FillValue on write

    return NetCDFSpec(
        case_id="ndvi_packed_netcdf",
        primary="ndvi_packed.nc",
        coords={"latitude": latitude, "longitude": longitude},
        variables={"ndvi": (("latitude", "longitude"), physical)},
        var_attrs={
            "ndvi": {"long_name": "Normalised difference vegetation index"},
            "latitude": {"units": "degrees_north", "standard_name": "latitude"},
            "longitude": {"units": "degrees_east", "standard_name": "longitude"},
        },
        encoding={
            "ndvi": {
                "dtype": "int16",
                "scale_factor": 0.0001,
                "add_offset": 0.0,
                "_FillValue": -32768,
            }
        },
        global_attrs={
            "Conventions": "CF-1.8",
            "title": "GeoCase test: packed int16 NDVI",
        },
    )


def _cf_time_ordering_spec() -> NetCDFSpec:
    """CF time units and a non-conventional dimension order, in one file.

    Combining the two is deliberate. A ``time`` dimension has to go *somewhere*
    in the ordering, so any CF-time fixture is already making a dimension-order
    statement whether it declares one or not. Two separate cases would each
    carry both properties while declaring only one — which is precisely the
    defect the ``latlon_small`` subtraction fixes.

    Dimensions are ``(longitude, latitude, time)``: x before y, time last. Most
    code assumes the reverse.
    """
    longitude = np.linspace(0.0, 7.0, 8)
    latitude = np.linspace(50.0, 54.0, 5)
    time = np.array([0, 24, 48], dtype="int32")

    # A separable ramp again, so a transposed read is visible in the values.
    values = (
        longitude[:, None, None]
        + latitude[None, :, None] * 0.1
        + time[None, None, :] * 0.01
    ).astype("float32")

    return NetCDFSpec(
        case_id="cf_time_ordering_netcdf",
        primary="cf_time_ordering.nc",
        coords={"longitude": longitude, "latitude": latitude, "time": time},
        variables={"t2m": (("longitude", "latitude", "time"), values)},
        var_attrs={
            "t2m": {"units": "K", "long_name": "2 metre temperature"},
            "latitude": {"units": "degrees_north", "standard_name": "latitude"},
            "longitude": {"units": "degrees_east", "standard_name": "longitude"},
            # CF time units belong in *attrs*, not encoding: the coordinate
            # holds raw integers rather than datetimes, so there is nothing for
            # xarray to encode. The netCDF4 backend rejects "units"/"calendar"
            # as encoding parameters outright. Written this way they land on
            # disk verbatim and decode on read, which is the whole point.
            "time": {
                "units": "hours since 2020-01-01 00:00:00",
                "calendar": "gregorian",
                "standard_name": "time",
            },
        },
        encoding={"t2m": {"dtype": "float32"}, "time": {"dtype": "int32"}},
        global_attrs={
            "Conventions": "CF-1.8",
            "title": "GeoCase test: CF time and dimension ordering",
        },
    )


def _specs() -> list[NetCDFSpec]:
    """Every bundled NetCDF fixture."""
    return [
        _latlon_small_spec(),
        _ndvi_packed_spec(),
        _cf_time_ordering_spec(),
    ]


def _spec_by_id(case_id: str) -> NetCDFSpec:
    """Look one spec up by case id, for tests and targeted regeneration."""
    for spec in _specs():
        if spec.case_id == case_id:
            return spec
    raise KeyError(f"No NetCDF spec for case id {case_id!r}")


def _write_netcdf(spec: NetCDFSpec, dest: Path) -> Path:
    """Build *spec* into an xarray Dataset and write it to *dest*."""
    import xarray as xr

    data_vars = {
        name: (dims, values) for name, (dims, values) in spec.variables.items()
    }
    dataset = xr.Dataset(
        data_vars=data_vars,
        coords={name: values for name, values in spec.coords.items()},
        attrs=dict(spec.global_attrs),
    )
    for name, attrs in spec.var_attrs.items():
        dataset[name].attrs.update(attrs)

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    dataset.to_netcdf(dest, engine=_ENGINE, encoding=dict(spec.encoding))
    dataset.close()
    return dest


def _semantic_signature(path: Path) -> dict[str, Any]:
    """What a consumer can observe about *path*, ignoring HDF5 bookkeeping.

    Deliberately excludes the library-version string and chunk layout HDF5
    writes into every file, which vary by build and would otherwise report
    drift on a dependency bump. See the module docstring.
    """
    import xarray as xr

    # decode_cf=False so packing attributes are observable as attributes rather
    # than silently applied -- a packed fixture whose scale_factor drifted
    # would otherwise still decode to the same physical values on one side and
    # compare equal.
    with xr.open_dataset(path, decode_cf=False) as ds:
        dims = sorted((str(name), int(size)) for name, size in ds.sizes.items())

        variables: list[tuple[Any, ...]] = []
        for name in sorted(ds.variables):
            var = ds[name]
            packing = tuple(
                (key, _round(var.attrs.get(key)))
                for key in ("_FillValue", "scale_factor", "add_offset", "units")
                if key in var.attrs
            )
            variables.append(
                (str(name), str(var.dtype), tuple(str(d) for d in var.dims), packing)
            )

        coords = {
            str(name): [_round(value) for value in np.asarray(ds[name].values).ravel()]
            for name in sorted(ds.coords)
        }
        global_attrs = {str(k): _round(v) for k, v in sorted(ds.attrs.items())}

    return {
        "dims": dims,
        "variables": variables,
        "coords": coords,
        "global_attrs": global_attrs,
    }


def _round(value: Any) -> Any:
    """Round floats for comparison; pass everything else through unchanged.

    NaN is mapped to a sentinel string rather than left as a float. xarray
    gives unpacked coordinate variables a ``_FillValue`` of NaN, and
    ``nan != nan``, so a signature carrying a raw NaN can never compare equal
    to itself -- the gate would report every fixture as stale, forever.
    """
    if isinstance(value, (float, np.floating)):
        if np.isnan(value):
            return "nan"
        return round(float(value), _PRECISION)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, np.ndarray):
        return [_round(item) for item in value.ravel()]
    return value


def _dest_for(spec: NetCDFSpec, netcdf_root: Path) -> Path:
    """Resolve a spec's on-disk primary path."""
    return netcdf_root / spec.case_id / spec.primary


def _missing_dependency() -> str | None:
    """Return a message if the readers this generator needs are absent."""
    try:
        import xarray  # noqa: F401
    except ImportError:
        return "xarray is required (pip install 'geocase[netcdf]')"
    try:
        import netCDF4  # noqa: F401
    except ImportError:
        return "netCDF4 is required (pip install 'geocase[netcdf]')"
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed fixtures match a fresh regeneration",
    )
    parser.add_argument(
        "--netcdf-root",
        type=Path,
        default=NETCDF_ROOT,
        help="root of the bundled netcdf case tree",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()

    problem = _missing_dependency()
    if problem is not None:
        # Exit 2, not 1: "cannot verify" is a different failure from "fixtures
        # have drifted" and needs a different fix. Matches the vector script.
        print(f"ERROR: {problem}", file=sys.stderr)
        return 2

    specs = _specs()

    if args.check:
        import tempfile

        stale: list[str] = []
        for spec in specs:
            dest = _dest_for(spec, args.netcdf_root)
            if not dest.exists():
                stale.append(f"{spec.case_id} (missing)")
                continue
            with tempfile.TemporaryDirectory() as tmp:
                candidate = _write_netcdf(spec, Path(tmp) / spec.primary)
                if _semantic_signature(candidate) != _semantic_signature(dest):
                    stale.append(spec.case_id)
        if stale:
            print(f"NetCDF fixtures out of date: {', '.join(stale)}")
            return 1
        print(f"All NetCDF fixtures up to date ({len(specs)} fixtures)")
        return 0

    for spec in specs:
        produced = _write_netcdf(spec, _dest_for(spec, args.netcdf_root))
        print(f"Wrote {produced.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
