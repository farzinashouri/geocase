from __future__ import annotations

import math
from typing import Any

from osgeo import gdal, ogr, osr
from pyproj import CRS, Geod, Transformer
from shapely import wkt
from shapely.geometry import GeometryCollection, MultiPolygon, Point, Polygon
from shapely.ops import transform, unary_union


# =========================================================
# 1. Reproject a point
# =========================================================

def reproject_point(x: float, y: float, src_epsg: int, dst_epsg: int) -> tuple[float, float]:
    transformer = Transformer.from_crs(
        f"EPSG:{src_epsg}",
        f"EPSG:{dst_epsg}",
        always_xy=True,
    )
    return transformer.transform(x, y)


def reproject_point_perfect(x: float, y: float, src_epsg: int, dst_epsg: int) -> tuple[float, float]:
    src_crs = CRS.from_epsg(src_epsg)
    dst_crs = CRS.from_epsg(dst_epsg)
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    out_x, out_y = transformer.transform(x, y)

    if dst_crs.is_geographic:
        out_x = ((out_x + 180.0) % 360.0) - 180.0

    return float(out_x), float(out_y)


# =========================================================
# 2. Check whether a point lies inside a polygon
# =========================================================

def point_in_polygon(point_wkt: str, polygon_wkt: str) -> bool:
    point = wkt.loads(point_wkt)
    polygon = wkt.loads(polygon_wkt)

    if not isinstance(point, Point):
        raise TypeError("point_wkt must represent a Point.")
    if not isinstance(polygon, (Polygon, MultiPolygon)):
        raise TypeError("polygon_wkt must represent a Polygon or MultiPolygon.")

    # covers includes boundary points; use contains for strict interior only
    return polygon.covers(point)


def point_in_polygon_perfect(point_wkt: str, polygon_wkt: str) -> bool:
    point = wkt.loads(point_wkt)
    polygon = wkt.loads(polygon_wkt)

    if not isinstance(point, Point):
        raise TypeError("point_wkt must represent a Point.")
    if not isinstance(polygon, (Polygon, MultiPolygon)):
        raise TypeError("polygon_wkt must represent a Polygon or MultiPolygon.")

    return polygon.contains(point)


# =========================================================
# 3. Compute the bounding box of a geometry
# =========================================================

def get_bbox(geom) -> tuple[float, float, float, float]:
    return geom.bounds


def get_bbox_perfect(geom) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = geom.bounds
    if (maxx - minx) <= 180.0:
        return minx, miny, maxx, maxy

    shifted_lons = []
    for x, _ in geom.exterior.coords:
        shifted_lons.append(x if x >= 0.0 else x + 360.0)

    for ring in getattr(geom, "interiors", []):
        for x, _ in ring.coords:
            shifted_lons.append(x if x >= 0.0 else x + 360.0)

    if isinstance(geom, MultiPolygon):
        shifted_lons = []
        for polygon in geom.geoms:
            for x, _ in polygon.exterior.coords:
                shifted_lons.append(x if x >= 0.0 else x + 360.0)
            for ring in polygon.interiors:
                for x, _ in ring.coords:
                    shifted_lons.append(x if x >= 0.0 else x + 360.0)

    return min(shifted_lons), miny, max(shifted_lons), maxy


# =========================================================
# 4. Buffer a geometry in metres
# =========================================================

def buffer_in_meters(geom, distance_m: float):
    if geom.is_empty:
        return geom

    centroid = geom.centroid
    metric_crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={centroid.y} +lon_0={centroid.x} +datum=WGS84 +units=m +no_defs"
    )
    to_metric = Transformer.from_crs("EPSG:4326", metric_crs, always_xy=True)
    to_wgs84 = Transformer.from_crs(metric_crs, "EPSG:4326", always_xy=True)

    geom_m = transform(to_metric.transform, geom)
    buffered_m = geom_m.buffer(distance_m)
    return transform(to_wgs84.transform, buffered_m)


def buffer_in_meters_perfect(geom: Any, distance_m: float) -> Any:
    if geom is None:
        raise TypeError("geom must not be None.")
    if geom.is_empty:
        return geom
    if distance_m < 0:
        raise ValueError("distance_m must be non-negative.")

    sample_points = []
    if isinstance(geom, Polygon):
        sample_points.extend(list(geom.exterior.coords))
        for ring in geom.interiors:
            sample_points.extend(list(ring.coords))
    elif isinstance(geom, MultiPolygon):
        for polygon in geom.geoms:
            sample_points.extend(list(polygon.exterior.coords))
            for ring in polygon.interiors:
                sample_points.extend(list(ring.coords))
    else:
        raise TypeError("geom must be a Polygon or MultiPolygon.")

    centroid = geom.centroid
    center_lon = ((centroid.x + 180.0) % 360.0) - 180.0

    def unwrap_lon(lon: float) -> float:
        return float(center_lon + (((lon - center_lon) + 180.0) % 360.0) - 180.0)

    unwrapped_points = [(unwrap_lon(x), y) for x, y in sample_points]
    unwrapped_centroid_x = sum(x for x, _ in unwrapped_points) / len(unwrapped_points)
    unwrapped_centroid_y = sum(y for _, y in unwrapped_points) / len(unwrapped_points)

    def unwrap_geometry(
        x: float, y: float, z: float | None = None
    ) -> tuple[float, float]:
        del z
        return unwrap_lon(x), y

    def wrap_geometry(
        x: float, y: float, z: float | None = None
    ) -> tuple[float, float]:
        del z
        wrapped_x = ((x + 180.0) % 360.0) - 180.0
        return wrapped_x, y

    unwrapped_geom = transform(unwrap_geometry, geom)
    metric_crs = CRS.from_proj4(
        "+proj=aeqd "
        f"+lat_0={unwrapped_centroid_y} "
        f"+lon_0={unwrapped_centroid_x} "
        "+datum=WGS84 +units=m +no_defs"
    )
    to_metric = Transformer.from_crs("EPSG:4326", metric_crs, always_xy=True)
    to_wgs84 = Transformer.from_crs(metric_crs, "EPSG:4326", always_xy=True)

    geom_m = transform(to_metric.transform, unwrapped_geom)
    buffered_m = geom_m.buffer(distance_m)
    buffered = transform(to_wgs84.transform, buffered_m)
    wrapped = transform(wrap_geometry, buffered)

    if not wrapped.is_valid:
        wrapped = wrapped.buffer(0)
    if wrapped.is_empty or not wrapped.is_valid:
        raise ValueError("Buffered geometry is invalid after reprojection.")

    return wrapped


# =========================================================
# 5. Find the UTM EPSG code from longitude/latitude
# =========================================================

def get_utm_epsg(lon: float, lat: float) -> int:
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError("Invalid longitude/latitude.")

    zone = int((lon + 180) // 6) + 1
    zone = max(1, min(zone, 60))

    if lat >= 0:
        return int(f"326{zone:02d}")  # WGS84 / UTM north
    return int(f"327{zone:02d}")      # WGS84 / UTM south


def get_utm_epsg_perfect(lon: float, lat: float) -> int:
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError("Invalid longitude/latitude.")

    if 56 <= lat < 64 and 3 <= lon < 12:
        zone = 32
    elif 72 <= lat < 84:
        if 0 <= lon < 9:
            zone = 31
        elif 9 <= lon < 21:
            zone = 33
        elif 21 <= lon < 33:
            zone = 35
        elif 33 <= lon < 42:
            zone = 37
        else:
            zone = int((lon + 180) // 6) + 1
    else:
        zone = int((lon + 180) // 6) + 1

    zone = max(1, min(zone, 60))

    if lat >= 0:
        return int(f"326{zone:02d}")
    return int(f"327{zone:02d}")


# =========================================================
# 6. Calculate polygon area in square metres
# =========================================================

def area_m2(geom) -> float:
    if geom.is_empty:
        return 0.0
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError("geom must be a Polygon or MultiPolygon.")

    centroid = geom.centroid
    area_crs = CRS.from_proj4(
        f"+proj=laea +lat_0={centroid.y} +lon_0={centroid.x} +datum=WGS84 +units=m +no_defs"
    )
    transformer = Transformer.from_crs("EPSG:4326", area_crs, always_xy=True)

    geom_m = transform(transformer.transform, geom)
    return float(geom_m.area)


def area_m2_perfect(geom) -> float:
    if geom is None:
        raise TypeError("geom must not be None.")
    if geom.is_empty:
        return 0.0
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError("geom must be a Polygon or MultiPolygon.")
    if not geom.is_valid:
        raise ValueError("geom must be a valid Polygon or MultiPolygon.")

    centroid = geom.centroid
    area_crs = CRS.from_proj4(
        f"+proj=laea +lat_0={centroid.y} +lon_0={centroid.x} +datum=WGS84 +units=m +no_defs"
    )
    transformer = Transformer.from_crs("EPSG:4326", area_crs, always_xy=True)

    geom_m = transform(transformer.transform, geom)
    return float(geom_m.area)


# =========================================================
# 7. Merge overlapping polygons
# =========================================================

def dissolve_polygons(polygons: list):
    merged = unary_union(polygons)

    if isinstance(merged, Polygon):
        return [merged]
    if isinstance(merged, MultiPolygon):
        return list(merged.geoms)
    if isinstance(merged, GeometryCollection):
        parts = []
        for part in merged.geoms:
            if isinstance(part, Polygon):
                parts.append(part)
            elif isinstance(part, MultiPolygon):
                parts.extend(list(part.geoms))
        return parts
    return []


def dissolve_polygons_perfect(polygons: list) -> list:
    repaired_polygons = []

    for geom in polygons:
        if geom is None or geom.is_empty:
            continue

        candidate = geom
        if not candidate.is_valid:
            candidate = fix_geometry_perfect(candidate)

        if candidate is None or candidate.is_empty or not candidate.is_valid:
            continue

        if isinstance(candidate, Polygon):
            repaired_polygons.append(candidate)
        elif isinstance(candidate, MultiPolygon):
            repaired_polygons.extend(list(candidate.geoms))

    if not repaired_polygons:
        return []

    merged = unary_union(repaired_polygons)

    if isinstance(merged, Polygon):
        return [merged]
    if isinstance(merged, MultiPolygon):
        return sorted(list(merged.geoms), key=lambda geom: geom.area, reverse=True)
    if isinstance(merged, GeometryCollection):
        polygon_parts = []
        for part in merged.geoms:
            if isinstance(part, Polygon):
                polygon_parts.append(part)
            elif isinstance(part, MultiPolygon):
                polygon_parts.extend(list(part.geoms))
        return sorted(polygon_parts, key=lambda geom: geom.area, reverse=True)
    return []


# =========================================================
# 8. Clip a raster by a bounding box
# =========================================================

def clip_raster(input_path: str, output_path: str, bbox: tuple[float, float, float, float]) -> None:
    minx, miny, maxx, maxy = bbox

    ds = gdal.Open(input_path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {input_path}")

    result = gdal.Translate(
        output_path,
        ds,
        projWin=[minx, maxy, maxx, miny],  # ulx, uly, lrx, lry
    )
    ds = None

    if result is None:
        raise RuntimeError("GDAL Translate failed.")
    result = None


def clip_raster_perfect(
    input_path: str,
    output_path: str,
    bbox: tuple[float, float, float, float],
    bbox_epsg: int | None = None,
) -> None:
    minx, miny, maxx, maxy = bbox

    ds = gdal.Open(input_path)
    if ds is None:
        raise FileNotFoundError(f"Could not open raster: {input_path}")

    proj = ds.GetProjection()
    if not proj:
        raise ValueError("Raster has no CRS/projection.")

    raster_crs = CRS.from_wkt(proj)
    if bbox_epsg is not None and raster_crs != CRS.from_epsg(bbox_epsg):
        transformer = Transformer.from_crs(
            f"EPSG:{bbox_epsg}",
            raster_crs,
            always_xy=True,
        )
        corners = [
            transformer.transform(minx, miny),
            transformer.transform(minx, maxy),
            transformer.transform(maxx, miny),
            transformer.transform(maxx, maxy),
        ]
        xs = [coord[0] for coord in corners]
        ys = [coord[1] for coord in corners]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)

    result = gdal.Translate(
        output_path,
        ds,
        projWin=[minx, maxy, maxx, miny],
    )
    ds = None

    if result is None:
        raise RuntimeError("GDAL Translate failed.")
    result = None


# =========================================================
# 9. Convert raster pixel coordinates to geographic coordinates
# =========================================================

def pixel_to_world(dataset, row: int, col: int) -> tuple[float, float]:
    gt = dataset.GetGeoTransform()
    x = gt[0] + col * gt[1] + row * gt[2]
    y = gt[3] + col * gt[4] + row * gt[5]
    return x, y


def pixel_to_world_perfect(dataset: Any, row: int, col: int) -> tuple[float, float]:
    if dataset is None:
        raise TypeError("dataset must not be None.")
    if row < 0 or col < 0:
        raise ValueError("row and col must be non-negative.")
    if row >= dataset.RasterYSize or col >= dataset.RasterXSize:
        raise ValueError("row and col must lie inside the raster extent.")

    gt = dataset.GetGeoTransform(can_return_null=True)
    if gt is None:
        raise ValueError("dataset has no geotransform.")

    pixel_col = col + 0.5
    pixel_row = row + 0.5
    x = gt[0] + pixel_col * gt[1] + pixel_row * gt[2]
    y = gt[3] + pixel_col * gt[4] + pixel_row * gt[5]
    return x, y


# =========================================================
# 10. Detect whether two rasters are aligned
# =========================================================

def rasters_aligned(ds1, ds2, tol: float = 1e-9) -> bool:
    def dataset_srs(ds):
        proj = ds.GetProjection()
        if not proj:
            return None
        return CRS.from_wkt(proj)

    def pixel_to_world_from_gt(
        gt: tuple[float, float, float, float, float, float], row: int, col: int
    ) -> tuple[float, float]:
        x = gt[0] + col * gt[1] + row * gt[2]
        y = gt[3] + col * gt[4] + row * gt[5]
        return x, y

    def raster_extent(ds) -> tuple[float, float, float, float]:
        gt = ds.GetGeoTransform()
        width = ds.RasterXSize
        height = ds.RasterYSize
        corners = [
            pixel_to_world_from_gt(gt, 0, 0),
            pixel_to_world_from_gt(gt, 0, width),
            pixel_to_world_from_gt(gt, height, 0),
            pixel_to_world_from_gt(gt, height, width),
        ]
        xs = [coord[0] for coord in corners]
        ys = [coord[1] for coord in corners]
        return min(xs), min(ys), max(xs), max(ys)

    if ds1.RasterXSize != ds2.RasterXSize or ds1.RasterYSize != ds2.RasterYSize:
        return False

    srs1 = dataset_srs(ds1)
    srs2 = dataset_srs(ds2)
    if (srs1 is None) != (srs2 is None):
        return False
    if srs1 is not None and srs2 is not None and srs1 != srs2:
        return False

    gt1 = ds1.GetGeoTransform()
    gt2 = ds2.GetGeoTransform()
    if any(abs(a - b) > tol for a, b in zip(gt1, gt2)):
        return False

    ext1 = raster_extent(ds1)
    ext2 = raster_extent(ds2)
    if any(abs(a - b) > tol for a, b in zip(ext1, ext2)):
        return False

    return True


def rasters_aligned_perfect(ds1: Any, ds2: Any, tol: float = 1e-9) -> bool:
    if ds1 is None or ds2 is None:
        raise TypeError("Both datasets must be provided.")
    if tol < 0:
        raise ValueError("tol must be non-negative.")

    proj1 = ds1.GetProjection()
    proj2 = ds2.GetProjection()
    if bool(proj1) != bool(proj2):
        return False
    if proj1 and proj2:
        if CRS.from_wkt(proj1) != CRS.from_wkt(proj2):
            return False

    if ds1.RasterXSize != ds2.RasterXSize or ds1.RasterYSize != ds2.RasterYSize:
        return False
    if ds1.RasterCount != ds2.RasterCount:
        return False

    gt1 = ds1.GetGeoTransform(can_return_null=True)
    gt2 = ds2.GetGeoTransform(can_return_null=True)
    if gt1 is None or gt2 is None:
        return False

    same_transform = all(abs(a - b) <= tol for a, b in zip(gt1, gt2))
    if same_transform:
        return True

    same_resolution = abs(gt1[1] - gt2[1]) <= tol and abs(gt1[5] - gt2[5]) <= tol
    same_rotation = abs(gt1[2] - gt2[2]) <= tol and abs(gt1[4] - gt2[4]) <= tol
    if not (same_resolution and same_rotation):
        return False

    pixel_dx = abs(gt1[0] - gt2[0]) / max(abs(gt1[1]), tol)
    pixel_dy = abs(gt1[3] - gt2[3]) / max(abs(gt1[5]), tol)

    return bool(
        abs(pixel_dx - round(pixel_dx)) <= tol and abs(pixel_dy - round(pixel_dy)) <= tol
    )


# =========================================================
# 11. Reproject a geometry
# =========================================================

def reproject_geometry(geom, src_epsg: int, dst_epsg: int):
    transformer = Transformer.from_crs(
        f"EPSG:{src_epsg}",
        f"EPSG:{dst_epsg}",
        always_xy=True,
    )
    return transform(transformer.transform, geom)


def reproject_geometry_perfect(geom: Any, src_epsg: int, dst_epsg: int) -> Any:
    if geom is None:
        raise TypeError("geom must not be None.")
    if geom.is_empty:
        return geom

    src_crs = CRS.from_epsg(src_epsg)
    dst_crs = CRS.from_epsg(dst_epsg)
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    projected = transform(transformer.transform, geom)

    if dst_crs.is_geographic:
        def normalize_lon(x: float, y: float, z: float | None = None) -> tuple[float, float]:
            del z
            return ((x + 180.0) % 360.0) - 180.0, y

        projected = transform(normalize_lon, projected)

    if not projected.is_valid:
        repaired = fix_geometry_perfect(projected)
        if repaired is not None and not repaired.is_empty and repaired.is_valid:
            return repaired

    return projected


# =========================================================
# 12. Find intersections between input polygons and AOIs
# =========================================================

def find_intersections(candidates: list, aois: list) -> list[dict]:
    results = []

    for i, candidate in enumerate(candidates):
        for j, aoi in enumerate(aois):
            if candidate.intersects(aoi):
                inter = candidate.intersection(aoi)
                if not inter.is_empty:
                    results.append(
                        {
                            "candidate_index": i,
                            "aoi_index": j,
                            "intersection_geom": inter,
                            "intersection_area": inter.area,
                        }
                    )

    return results


def find_intersections_perfect(
    candidates: list,
    aois: list,
    geom_epsg: int = 4326,
) -> list[dict]:
    results = []

    for i, candidate in enumerate(candidates):
        for j, aoi in enumerate(aois):
            if not candidate.intersects(aoi):
                continue

            inter = candidate.intersection(aoi)
            if inter.is_empty:
                continue

            if isinstance(inter, (Polygon, MultiPolygon)):
                if geom_epsg == 4326:
                    intersection_area = area_m2_perfect(inter)
                else:
                    projected = reproject_geometry(inter, geom_epsg, 4326)
                    intersection_area = area_m2_perfect(projected)
            else:
                intersection_area = 0.0

            results.append(
                {
                    "candidate_index": i,
                    "aoi_index": j,
                    "intersection_geom": inter,
                    "intersection_area": intersection_area,
                }
            )

    return results


# =========================================================
# 13. Validate a geometry before DB insertion
# =========================================================

def validate_polygon_geometry(geom, min_area_m2: float) -> tuple[bool, list[str]]:
    errors = []

    if geom is None:
        return False, ["Geometry is None."]
    if geom.is_empty:
        errors.append("Geometry is empty.")
    if not isinstance(geom, (Polygon, MultiPolygon)):
        errors.append("Geometry must be Polygon or MultiPolygon.")
    if hasattr(geom, "is_valid") and not geom.is_valid:
        errors.append("Geometry is invalid.")

    if not errors:
        try:
            centroid = geom.centroid
            area_crs = CRS.from_proj4(
                f"+proj=laea +lat_0={centroid.y} +lon_0={centroid.x} +datum=WGS84 +units=m +no_defs"
            )
            transformer = Transformer.from_crs("EPSG:4326", area_crs, always_xy=True)
            geom_area_m2 = float(transform(transformer.transform, geom).area)
            if geom_area_m2 < min_area_m2:
                errors.append(
                    f"Geometry area {geom_area_m2:.2f} m² is below minimum {min_area_m2:.2f} m²."
                )
        except Exception as exc:
            errors.append(f"Failed to compute area in m²: {exc}")

    return len(errors) == 0, errors


def validate_polygon_geometry_perfect(
    geom: Any, min_area_m2: float
) -> tuple[bool, list[str]]:
    if geom is None:
        return False, ["Geometry is None."]
    if geom.is_empty:
        return False, ["Geometry is empty."]
    if not isinstance(geom, (Polygon, MultiPolygon)):
        return False, ["Geometry must be Polygon or MultiPolygon."]
    if min_area_m2 < 0:
        return False, ["Minimum area must be non-negative."]

    candidate = geom
    if not candidate.is_valid:
        try:
            from shapely.validation import make_valid

            repaired = make_valid(candidate)
        except Exception:
            repaired = candidate.buffer(0)

        if repaired is None or repaired.is_empty or not repaired.is_valid:
            return False, ["Geometry is invalid and could not be repaired."]

        if isinstance(repaired, Polygon):
            candidate = repaired
        elif isinstance(repaired, MultiPolygon):
            candidate = repaired
        elif isinstance(repaired, GeometryCollection):
            polygon_parts = []
            for part in repaired.geoms:
                if isinstance(part, Polygon):
                    polygon_parts.append(part)
                elif isinstance(part, MultiPolygon):
                    polygon_parts.extend(list(part.geoms))

            if not polygon_parts:
                return False, ["Geometry repair produced no polygonal geometry."]

            candidate = MultiPolygon(polygon_parts) if len(polygon_parts) > 1 else polygon_parts[0]
        else:
            return False, ["Geometry repair produced no polygonal geometry."]

        if candidate.is_empty or not candidate.is_valid:
            return False, ["Geometry is invalid and could not be repaired."]

    try:
        geom_area_m2 = area_m2_perfect(candidate)
    except Exception as exc:
        return False, [f"Failed to compute area in m²: {exc}"]

    if geom_area_m2 < min_area_m2:
        return False, [
            f"Geometry area {geom_area_m2:.2f} m² is below minimum {min_area_m2:.2f} m²."
        ]

    return True, []


# =========================================================
# 14. Extract raster value at a geographic point
# =========================================================

def sample_raster_at_lonlat(dataset, lon: float, lat: float):
    proj = dataset.GetProjection()
    srs = CRS.from_wkt(proj) if proj else None
    if srs is None:
        raise ValueError("Raster has no CRS/projection.")

    if srs.to_epsg() == 4326:
        x, y = lon, lat
    else:
        transformer = Transformer.from_crs("EPSG:4326", srs, always_xy=True)
        x, y = transformer.transform(lon, lat)

    gt = dataset.GetGeoTransform()
    a = gt[1]
    b = gt[2]
    d = gt[4]
    e = gt[5]
    det = a * e - b * d
    if det == 0:
        raise ValueError("Non-invertible geotransform.")

    dx = x - gt[0]
    dy = y - gt[3]

    col = int(math.floor((e * dx - b * dy) / det))
    row = int(math.floor((-d * dx + a * dy) / det))

    if not (0 <= col < dataset.RasterXSize and 0 <= row < dataset.RasterYSize):
        raise ValueError("Point lies outside raster extent.")

    band = dataset.GetRasterBand(1)
    arr = band.ReadAsArray(col, row, 1, 1)
    if arr is None:
        raise RuntimeError("Failed to read raster value.")

    return arr[0, 0].item()


def sample_raster_at_lonlat_perfect(dataset, lon: float, lat: float):
    proj = dataset.GetProjection()
    srs = CRS.from_wkt(proj) if proj else None
    if srs is None:
        raise ValueError("Raster has no CRS/projection.")

    if srs.to_epsg() == 4326:
        x, y = lon, lat
    else:
        transformer = Transformer.from_crs("EPSG:4326", srs, always_xy=True)
        x, y = transformer.transform(lon, lat)

    gt = dataset.GetGeoTransform()
    a = gt[1]
    b = gt[2]
    d = gt[4]
    e = gt[5]
    det = a * e - b * d
    if det == 0:
        raise ValueError("Non-invertible geotransform.")

    dx = x - gt[0]
    dy = y - gt[3]

    col = int(math.floor((e * dx - b * dy) / det))
    row = int(math.floor((-d * dx + a * dy) / det))

    if not (0 <= col < dataset.RasterXSize and 0 <= row < dataset.RasterYSize):
        raise ValueError("Point lies outside raster extent.")

    band = dataset.GetRasterBand(1)
    arr = band.ReadAsArray(col, row, 1, 1)
    if arr is None:
        raise RuntimeError("Failed to read raster value.")

    value = arr[0, 0].item()
    nodata = band.GetNoDataValue()
    if nodata is not None and value == nodata:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


# =========================================================
# 15. Group nearby points into clusters
# =========================================================

def cluster_points(points: list, max_distance_m: float) -> list[list]:
    if not points:
        return []
    if not all(isinstance(p, Point) for p in points):
        raise TypeError("All inputs must be shapely Point objects.")

    avg_lon = sum(p.x for p in points) / len(points)
    avg_lat = sum(p.y for p in points) / len(points)
    metric_crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={avg_lat} +lon_0={avg_lon} +datum=WGS84 +units=m +no_defs"
    )
    transformer = Transformer.from_crs("EPSG:4326", metric_crs, always_xy=True)

    projected_points = [transform(transformer.transform, point) for point in points]

    visited = set()
    clusters = []

    for i in range(len(projected_points)):
        if i in visited:
            continue

        stack = [i]
        component = []

        while stack:
            idx = stack.pop()
            if idx in visited:
                continue

            visited.add(idx)
            component.append(idx)

            for j in range(len(projected_points)):
                if j not in visited:
                    if projected_points[idx].distance(projected_points[j]) <= max_distance_m:
                        stack.append(j)

        clusters.append([points[idx] for idx in component])

    return clusters


def cluster_points_perfect(points: list, max_distance_m: float) -> list[list]:
    if not points:
        return []
    if not all(isinstance(point, Point) for point in points):
        raise TypeError("All inputs must be shapely Point objects.")

    geod = Geod(ellps="WGS84")
    visited = set()
    clusters = []

    for start_idx in range(len(points)):
        if start_idx in visited:
            continue

        stack = [start_idx]
        component = []

        while stack:
            idx = stack.pop()
            if idx in visited:
                continue

            visited.add(idx)
            component.append(idx)

            for neighbor_idx in range(len(points)):
                if neighbor_idx in visited:
                    continue
                _, _, distance_m = geod.inv(
                    points[idx].x,
                    points[idx].y,
                    points[neighbor_idx].x,
                    points[neighbor_idx].y,
                )
                if distance_m <= max_distance_m:
                    stack.append(neighbor_idx)

        clusters.append([points[idx] for idx in component])

    return clusters


# =========================================================
# 16. Repair invalid polygons where possible
# =========================================================

def fix_geometry(geom):
    if geom is None or geom.is_empty:
        return geom
    if geom.is_valid:
        return geom

    # Try make_valid if available
    try:
        from shapely.validation import make_valid
        fixed = make_valid(geom)
        if fixed is not None and not fixed.is_empty and fixed.is_valid:
            return fixed
    except Exception:
        pass

    # Fallback
    fixed = geom.buffer(0)
    if fixed is not None and not fixed.is_empty and fixed.is_valid:
        return fixed

    return geom


def fix_geometry_perfect(geom: Any) -> Any:
    if geom is None or geom.is_empty:
        return geom
    if isinstance(geom, (Polygon, MultiPolygon)) and geom.is_valid:
        return geom

    repaired = None
    try:
        from shapely.validation import make_valid

        repaired = make_valid(geom)
    except Exception:
        repaired = None

    if repaired is None or repaired.is_empty or not repaired.is_valid:
        repaired = geom.buffer(0)

    if repaired is None or repaired.is_empty or not repaired.is_valid:
        return geom

    if isinstance(repaired, Polygon):
        return repaired
    if isinstance(repaired, MultiPolygon):
        return repaired
    if isinstance(repaired, GeometryCollection):
        polygon_parts = []
        for part in repaired.geoms:
            if isinstance(part, Polygon):
                polygon_parts.append(part)
            elif isinstance(part, MultiPolygon):
                polygon_parts.extend(list(part.geoms))

        if not polygon_parts:
            return geom

        if len(polygon_parts) == 1:
            return polygon_parts[0]
        return MultiPolygon(polygon_parts)

    return geom


# =========================================================
# 17. Rasterize vector geometries onto a reference raster grid
# =========================================================

def rasterize_geometries(geometries: list, reference_raster_path: str, output_path: str) -> None:
    ref_ds = gdal.Open(reference_raster_path)
    if ref_ds is None:
        raise FileNotFoundError(f"Could not open reference raster: {reference_raster_path}")

    xsize = ref_ds.RasterXSize
    ysize = ref_ds.RasterYSize
    gt = ref_ds.GetGeoTransform()
    proj = ref_ds.GetProjection()

    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(output_path, xsize, ysize, 1, gdal.GDT_Byte)
    if out_ds is None:
        raise RuntimeError("Could not create output raster.")

    out_ds.SetGeoTransform(gt)
    out_ds.SetProjection(proj)

    band = out_ds.GetRasterBand(1)
    band.Fill(0)
    band.SetNoDataValue(0)

    mem_driver = ogr.GetDriverByName("Memory")
    vec_ds = mem_driver.CreateDataSource("mem")
    layer = vec_ds.CreateLayer("shapes", srs=None, geom_type=ogr.wkbPolygon)

    defn = layer.GetLayerDefn()

    for geom in geometries:
        feat = ogr.Feature(defn)
        ogr_geom = ogr.CreateGeometryFromWkb(geom.wkb)
        feat.SetGeometry(ogr_geom)
        layer.CreateFeature(feat)
        feat = None

    err = gdal.RasterizeLayer(out_ds, [1], layer, burn_values=[1])
    if err != 0:
        raise RuntimeError("RasterizeLayer failed.")

    band.FlushCache()
    out_ds = None
    vec_ds = None
    ref_ds = None


def rasterize_geometries_perfect(
    geometries: list,
    reference_raster_path: str,
    output_path: str,
    src_epsg: int = 4326,
) -> None:
    ref_ds = gdal.Open(reference_raster_path)
    if ref_ds is None:
        raise FileNotFoundError(f"Could not open reference raster: {reference_raster_path}")

    xsize = ref_ds.RasterXSize
    ysize = ref_ds.RasterYSize
    gt = ref_ds.GetGeoTransform()
    proj = ref_ds.GetProjection()
    if not proj:
        raise ValueError("Reference raster has no CRS/projection.")

    target_crs = CRS.from_wkt(proj)
    target_srs = osr.SpatialReference()
    target_srs.ImportFromWkt(proj)

    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(output_path, xsize, ysize, 1, gdal.GDT_Byte)
    if out_ds is None:
        raise RuntimeError("Could not create output raster.")

    out_ds.SetGeoTransform(gt)
    out_ds.SetProjection(proj)

    band = out_ds.GetRasterBand(1)
    band.Fill(0)
    band.SetNoDataValue(0)

    mem_driver = ogr.GetDriverByName("MEM") or ogr.GetDriverByName("Memory")
    if mem_driver is None:
        raise RuntimeError("Could not create in-memory vector datasource.")

    vec_ds = mem_driver.CreateDataSource("mem")
    layer = vec_ds.CreateLayer("shapes", srs=target_srs, geom_type=ogr.wkbUnknown)
    defn = layer.GetLayerDefn()

    src_crs = CRS.from_epsg(src_epsg)
    if src_crs == target_crs:
        transformer = None
    else:
        transformer = Transformer.from_crs(src_crs, target_crs, always_xy=True)

    for geom in geometries:
        geom_to_write = geom if transformer is None else transform(transformer.transform, geom)
        feat = ogr.Feature(defn)
        ogr_geom = ogr.CreateGeometryFromWkb(geom_to_write.wkb)
        feat.SetGeometry(ogr_geom)
        layer.CreateFeature(feat)
        feat = None

    err = gdal.RasterizeLayer(out_ds, [1], layer, burn_values=[1])
    if err != 0:
        raise RuntimeError("RasterizeLayer failed.")

    band.FlushCache()
    out_ds = None
    vec_ds = None
    ref_ds = None


# =========================================================
# 18. Determine whether a polygon crosses the antimeridian
# =========================================================

def crosses_antimeridian(geom) -> bool:
    # Heuristic solution assuming EPSG:4326 and longitudes in [-180, 180].
    # For polygons spanning the dateline, consecutive vertices often show
    # longitude jumps greater than 180 degrees.

    def ring_crosses(coords) -> bool:
        lons = [x for x, y in coords]
        for i in range(1, len(lons)):
            if abs(lons[i] - lons[i - 1]) > 180:
                return True
        return False

    if isinstance(geom, Polygon):
        if ring_crosses(list(geom.exterior.coords)):
            return True
        return any(ring_crosses(list(r.coords)) for r in geom.interiors)

    if isinstance(geom, MultiPolygon):
        return any(crosses_antimeridian(g) for g in geom.geoms)

    return False


def crosses_antimeridian_perfect(geom) -> bool:
    def normalize_lon(lon: float) -> float:
        return ((lon + 180.0) % 360.0) - 180.0

    def ring_crosses(coords) -> bool:
        raw_lons = [x for x, _ in coords]
        normalized_lons = [normalize_lon(lon) for lon in raw_lons]

        for i in range(1, len(raw_lons)):
            if abs(raw_lons[i] - raw_lons[i - 1]) > 180.0:
                return True
            if abs(normalized_lons[i] - normalized_lons[i - 1]) > 180.0:
                return True

        if any(lon < -180.0 or lon > 180.0 for lon in raw_lons):
            normalized_span = max(normalized_lons) - min(normalized_lons)
            if normalized_span > 180.0:
                return True

        return False

    if isinstance(geom, Polygon):
        if ring_crosses(list(geom.exterior.coords)):
            return True
        return any(ring_crosses(list(ring.coords)) for ring in geom.interiors)

    if isinstance(geom, MultiPolygon):
        return any(crosses_antimeridian_perfect(part) for part in geom.geoms)

    return False