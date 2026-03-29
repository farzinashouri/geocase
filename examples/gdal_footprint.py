"""Generate a GeoJSON footprint polygon from a GeoTIFF using GDAL."""

from __future__ import annotations

import json
from pathlib import Path

from osgeo import gdal

gdal.UseExceptions()


def geotiff_footprint_to_geojson(
    geotiff_path: str | Path,
    output_geojson_path: str | Path,
) -> Path:
    """Calculate a GeoTIFF footprint and save it as a GeoJSON polygon.

    Args:
        geotiff_path: Path to input GeoTIFF.
        output_geojson_path: Path where GeoJSON footprint will be written.

    Returns:
        Path to the created GeoJSON file.

    Raises:
        FileNotFoundError: If input GeoTIFF does not exist.
        ValueError: If GDAL cannot open the dataset or input is not raster.
    """
    input_path = Path(geotiff_path)
    output_path = Path(output_geojson_path)

    if not input_path.exists():
        raise FileNotFoundError(f"GeoTIFF not found: {input_path}")

    try:
        dataset = gdal.Open(str(input_path), gdal.GA_ReadOnly)
    except RuntimeError as exc:
        raise ValueError(
            f"Unable to open raster dataset with GDAL: {input_path}"
        ) from exc

    if dataset is None:
        raise ValueError(
            f"Unable to open raster dataset with GDAL: {input_path}"
        )

    if dataset.RasterCount < 1:
        raise ValueError(
            f"Input dataset has no raster bands: {input_path}"
        )

    band1 = dataset.GetRasterBand(1)
    src_nodata = band1.GetNoDataValue() if band1 is not None else None

    output_path.parent.mkdir(parents=True, exist_ok=True)

    footprint_kwargs = {
        "format": "GeoJSON",
        "convexHull": True,
    }
    if src_nodata is not None:
        footprint_kwargs["srcNodata"] = src_nodata

    gdal.Footprint(str(output_path), dataset, **footprint_kwargs)

    if not output_path.exists():
        raise RuntimeError(f"GDAL Footprint did not create output: {output_path}")

    parsed = json.loads(output_path.read_text(encoding="utf-8"))
    output_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Create a GeoJSON footprint from a GeoTIFF using GDAL.",
    )
    parser.add_argument("input_tif", help="Path to input GeoTIFF")
    parser.add_argument("output_geojson", help="Path to output GeoJSON")
    args = parser.parse_args()

    created = geotiff_footprint_to_geojson(args.input_tif, args.output_geojson)
    print(f"Wrote footprint: {created}")
