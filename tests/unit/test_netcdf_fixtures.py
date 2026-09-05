"""Gates for the generated NetCDF fixtures and their content check.

``latlon_sample.nc`` was for most of this repository's life the only fixture
that could not be regenerated: it arrived in a single "Analyse structure"
commit carrying unseeded random temperatures, and 400 seed/distribution
combinations failed to recover them. Every other NetCDF gap was blocked behind
that, because a catalog cannot gate a file it cannot rebuild.

So determinism is the property under test here, exactly as in
``test_generated_geometry.py`` -- and for the same reason: the fixture tree is
compared against a fresh regeneration in CI, and a generator that wandered by
one float would fail the build with no way to tell drift from noise.

``--check`` is semantic rather than byte-for-byte. HDF5 stamps a library
version string into the file and orders chunks by build, so a byte gate would
go red on a dependency bump that changed no data. ``generate_vector_fixtures``
makes the same argument for GPKG and Parquet.

See docs/plans/34-close-reviewed-catalog-gaps.md, Phase 1.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
NETCDF_ROOT = REPO_ROOT / "src" / "geocase" / "data" / "core" / "netcdf"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

pytest.importorskip("xarray")
pytest.importorskip("netCDF4")

from generate_netcdf_fixtures import (  # type: ignore[import-not-found] # noqa: E402
    _semantic_signature,
    _spec_by_id,
    _specs,
    _write_netcdf,
)

from geocase.catalog.content import check_case_content  # noqa: E402
from geocase.catalog.registry import get_registry  # noqa: E402


def _metadata(case_id: str):  # type: ignore[no-untyped-def]
    return get_registry().get(case_id)


def _case_dir(case_id: str) -> Path:
    return NETCDF_ROOT / case_id


# --- the generator reproduces what is committed ---------------------------


def test_generator_output_matches_the_shipped_fixture(tmp_path: Path) -> None:
    """The standing ``--check`` gate, in unit-test form.

    Red until the replacement fixture lands, green afterwards, and the thing
    that keeps ``latlon_sample.nc`` regenerable from here on.
    """
    spec = _spec_by_id("latlon_small")
    produced = tmp_path / spec.primary
    _write_netcdf(spec, produced)

    committed = _case_dir("latlon_small") / spec.primary
    assert _semantic_signature(produced) == _semantic_signature(committed)


def test_latlon_small_keeps_its_declared_shape() -> None:
    """Pin the properties the replacement promised to preserve.

    The case's ``case.yaml`` was written against the original binary. If a
    later regeneration drifts the shape, dtype or fill positions, the case
    would quietly stop matching its own declarations -- so they are asserted
    against the bytes rather than trusted.
    """
    import numpy as np
    import xarray as xr

    path = _case_dir("latlon_small") / "latlon_sample.nc"
    with xr.open_dataset(path) as ds:
        assert ds.sizes["latitude"] == 5
        assert ds.sizes["longitude"] == 8
        assert ds["temperature"].dtype == np.float64
        assert ds["temperature"].encoding["_FillValue"] == -9999.0
        # Exactly two fill cells, at the documented positions.
        missing = np.isnan(ds["temperature"].values)
        assert missing.sum() == 2
        assert missing[0, 0]
        assert missing[3, 5]


def test_netcdf_generator_is_deterministic(tmp_path: Path) -> None:
    """Two builds, one answer -- and no PRNG or clock anywhere in the module."""
    spec = _spec_by_id("latlon_small")
    first = tmp_path / "first.nc"
    second = tmp_path / "second.nc"
    _write_netcdf(spec, first)
    _write_netcdf(spec, second)

    assert _semantic_signature(first) == _semantic_signature(second)

    # Structural, not observational: a seeded PRNG is reproducible only as long
    # as CPython's stream is, and this repo gates on regenerated output.
    source = (SCRIPTS / "generate_netcdf_fixtures.py").read_text(encoding="utf-8")
    for banned in ("import random", "import time", "import uuid", "datetime.now"):
        assert banned not in source, f"{banned} breaks reproducible regeneration"


def test_every_spec_has_a_case_directory() -> None:
    """A spec with no case is a fixture nothing describes."""
    for spec in _specs():
        assert (_case_dir(spec.case_id) / "case.yaml").is_file()


# --- the content check ----------------------------------------------------


def test_check_case_content_validates_netcdf_dimensions() -> None:
    """The declared dimension order is checked against the real file.

    Order is the point: ``expected_dimensions`` is what makes a dimension-order
    claim checkable at all, so the wrong order has to be a finding.
    """
    metadata = _metadata("latlon_small")
    case_dir = _case_dir("latlon_small")

    assert check_case_content(case_dir, metadata) == []

    wrong = metadata.model_copy(deep=True)
    wrong.params["expected_dimensions"] = ["time", "x"]
    errors = check_case_content(case_dir, wrong)
    assert len(errors) == 1
    assert "expected_dimensions" in errors[0]


def test_check_case_content_validates_netcdf_variables() -> None:
    metadata = _metadata("latlon_small")
    wrong = metadata.model_copy(deep=True)
    wrong.params["expected_variables"] = ["not_a_variable"]

    errors = check_case_content(_case_dir("latlon_small"), wrong)
    assert len(errors) == 1
    assert "expected_variables" in errors[0]


# --- packing, CF time and dimension order --------------------------------


def test_packed_variable_unpacks_to_physical_units() -> None:
    """The pair of reads is the test.

    Raw, the variable is plausible int16 -- which is the failure mode: a
    consumer that skips ``scale_factor`` sees numbers that look like data and
    are off by four orders of magnitude. Decoded, it is NDVI in [-1, 1].
    """
    import numpy as np
    import xarray as xr

    path = _case_dir("ndvi_packed_netcdf") / "ndvi_packed.nc"

    with xr.open_dataset(path, mask_and_scale=False) as raw:
        assert raw["ndvi"].dtype == np.int16
        assert raw["ndvi"].attrs["scale_factor"] == 0.0001
        assert int(raw["ndvi"].max()) > 100  # plausible-looking, and wrong

    with xr.open_dataset(path) as decoded:
        assert decoded["ndvi"].dtype.kind == "f"
        values = decoded["ndvi"].values
        finite = values[np.isfinite(values)]
        assert finite.min() >= -1.0
        assert finite.max() <= 1.0


def test_cf_time_decodes_to_the_expected_calendar() -> None:
    import xarray as xr

    path = _case_dir("cf_time_ordering_netcdf") / "cf_time_ordering.nc"
    with xr.open_dataset(path) as ds:
        times = ds["time"].values
        assert str(times[0]).startswith("2020-01-01")
        assert str(times[1]).startswith("2020-01-02")


def test_cf_time_undecoded_is_raw_numbers() -> None:
    """Same differential shape as the packing pair: without decoding, the
    time axis is three small integers that mean nothing on their own."""
    import xarray as xr

    path = _case_dir("cf_time_ordering_netcdf") / "cf_time_ordering.nc"
    with xr.open_dataset(path, decode_times=False) as ds:
        assert list(ds["time"].values) == [0, 24, 48]
        assert ds["time"].attrs["units"] == "hours since 2020-01-01 00:00:00"


def test_dimension_order_is_non_conventional() -> None:
    """x before y, time last -- the opposite of what most code assumes."""
    import xarray as xr

    path = _case_dir("cf_time_ordering_netcdf") / "cf_time_ordering.nc"
    with xr.open_dataset(path) as ds:
        assert list(ds["t2m"].dims) == ["longitude", "latitude", "time"]


def test_dimension_order_declaration_is_enforced() -> None:
    """Reordering the declaration to the conventional order must fail."""
    metadata = _metadata("cf_time_ordering_netcdf")
    case_dir = _case_dir("cf_time_ordering_netcdf")
    assert check_case_content(case_dir, metadata) == []

    wrong = metadata.model_copy(deep=True)
    wrong.params["expected_dimensions"] = ["latitude", "longitude", "time"]
    errors = check_case_content(case_dir, wrong)
    assert len(errors) == 1
    assert "expected_dimensions" in errors[0]


def test_packed_case_scale_factor_is_enforced() -> None:
    metadata = _metadata("ndvi_packed_netcdf")
    case_dir = _case_dir("ndvi_packed_netcdf")
    assert check_case_content(case_dir, metadata) == []

    wrong = metadata.model_copy(deep=True)
    wrong.assertions.expected_scale_factor = 0.5
    errors = check_case_content(case_dir, wrong)
    assert len(errors) == 1
    assert "expected_scale_factor" in errors[0]


def test_cross_container_pair_is_linked_in_both_directions() -> None:
    """The packed netcdf case and its GeoTIFF analogue point at each other.

    One failure mode, two containers: a reader that handles packing in one and
    not the other is a real and common gap, and the link is what makes the pair
    findable rather than coincidental.
    """
    netcdf = _metadata("ndvi_packed_netcdf")
    raster = _metadata("ndvi_scaled_int16_small")

    assert netcdf.params["analogous_case_id"] == "ndvi_scaled_int16_small"
    assert raster.params["analogous_case_id"] == "ndvi_packed_netcdf"


def test_latlon_small_no_longer_claims_undemonstrable_risks() -> None:
    """Regression guard on the subtraction.

    ``coordinate_order`` and ``dimension_mismatch`` were labelled on
    conventional (latitude, longitude) rectilinear data that exercises
    neither, and ``expect_crs`` was declared on a file with no grid_mapping
    and no crs variable. A case returning green for a property it cannot test
    terminates the user's search.
    """
    metadata = _metadata("latlon_small")

    assert "crs/axis_order" not in metadata.risk_types
    assert "band/dimension_mismatch" not in metadata.risk_types
    assert metadata.assertions.expect_crs is None
    assert metadata.assertions.expected_epsg is None

    # What it does still claim is real, and checked.
    assert "nodata/ignored" in metadata.risk_types
    assert metadata.assertions.expect_nodata is True


def test_netcdf_content_check_is_skipped_without_xarray(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A missing optional reader is not a finding.

    The catalog job installs xarray, but ``check_case_content`` is public and
    users run it wherever they like. Absent the reader it must return no
    findings rather than raising -- otherwise every netcdf case reads as broken
    on a machine that simply never installed the extra.
    """
    import builtins

    real_import = builtins.__import__

    def _no_xarray(name: str, *args: object, **kwargs: object) -> object:
        if name == "xarray":
            raise ImportError("no xarray")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", _no_xarray)

    metadata = _metadata("latlon_small")
    assert check_case_content(_case_dir("latlon_small"), metadata) == []
