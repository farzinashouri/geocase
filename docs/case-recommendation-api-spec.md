# Case Recommendation API Specification

This document defines the API contract for the GeoCase case recommendation service.

## Endpoint

- **Method**: `POST`
- **Path**: `/v1/recommendations`
- **Purpose**: Recommend GeoCase cases that are likely to fail for a submitted geospatial function.

## Authentication

MVP options:

- internal deployments: trusted network only,
- external deployments: `Authorization: Bearer <token>`.

## Request content type

- `Content-Type: application/json`

---

## Request schema

```json
{
  "function": {
    "language": "python",
    "name": "clip_and_reproject",
    "source_code": "def clip_and_reproject(gdf, bbox, epsg): ...",
    "entrypoint": "clip_and_reproject"
  },
  "explanation": "Fails near dateline and sometimes drops holes after reprojection.",
  "selector_constraints": {
    "category": "vector",
    "geometry_type": "Polygon",
    "format": "GeoJSON",
    "test_tier": "unit",
    "storage_class": "bundled",
    "size_class": "tiny",
    "tags_any": ["polygon", "hole"],
    "tags_all": ["vector"],
    "risk_types_any": ["coordinate_wrapping"],
    "include_case_ids": [],
    "exclude_case_ids": []
  },
  "top_k": 5,
  "include_pytest_template": true,
  "trace": {
    "client_request_id": "abc-123"
  }
}
```

### Required fields

- `function.language`
- `function.source_code`

### Optional fields

- `function.name`
- `function.entrypoint`
- `explanation`
- `selector_constraints`
- `top_k` (default: `10`, max: `50`)
- `include_pytest_template` (default: `true`)
- `trace.client_request_id`

### `selector_constraints` field compatibility

Selector fields map to GeoCase metadata fields:

- `category`
- `geometry_type`
- `format`
- `test_tier`
- `storage_class`
- `size_class`
- `tags_any`, `tags_all`
- `risk_types_any`
- `include_case_ids`, `exclude_case_ids`

If constraints are too strict and produce zero candidates, the service may apply a controlled fallback relaxation and report it in `notes`.

---

## Success response (`200 OK`)

```json
{
  "request_id": "rec_01JQYV0Q46S0A8J5HZXK6X8V2F",
  "version": "2026-03-29",
  "resolved_selectors": {
    "category": "vector",
    "geometry_type": "Polygon",
    "format": "GeoJSON",
    "tags_any": ["polygon", "hole"],
    "risk_types_any": ["coordinate_wrapping"]
  },
  "recommendations": [
    {
      "case_id": "dateline_crossing_polygon",
      "score": 0.94,
      "matched_on": ["category", "geometry_type", "risk_types_any"],
      "reason": "Detected dateline/antimeridian risk for polygon reprojection.",
      "metadata": {
        "category": "vector",
        "geometry_type": "Polygon",
        "format": "GeoJSON",
        "risk_types": ["coordinate_wrapping", "bbox_misinterpretation"]
      }
    },
    {
      "case_id": "polygon_with_hole",
      "score": 0.88,
      "matched_on": ["category", "geometry_type", "tags_any"],
      "reason": "Potential ring-preservation/topology risk after clipping/reprojection.",
      "metadata": {
        "category": "vector",
        "geometry_type": "Polygon",
        "format": "GeoJSON",
        "risk_types": ["incorrect_area", "ring_ordering"]
      }
    }
  ],
  "pytest_template": "@pytest.mark.geocase_case(\"dateline_crossing_polygon\", \"polygon_with_hole\")\ndef test_recommended_cases(geocase):\n    ...",
  "notes": [
    "Scores are relative to this request.",
    "Hard selector constraints were applied before ranking."
  ],
  "timing_ms": {
    "analysis": 21,
    "selection": 7,
    "ranking": 5,
    "total": 37
  }
}
```

### Response field definitions

- `request_id`: server-generated unique ID for tracing.
- `version`: recommendation ruleset/model version.
- `resolved_selectors`: effective selectors after validation/defaulting.
- `recommendations`: ranked list (highest score first).
- `recommendations[].matched_on`: which metadata dimensions contributed materially.
- `pytest_template`: optional scaffold to accelerate test creation.
- `notes`: caveats, fallback behavior, confidence qualifiers.
- `timing_ms`: optional latency breakdown.

---

## Error model

All errors return JSON:

```json
{
  "request_id": "rec_01JQ...",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "selector_constraints.format must be one of GeoJSON, GPKG, Shapefile, GeoTIFF, NetCDF, Parquet, Other",
    "details": {
      "field": "selector_constraints.format"
    }
  }
}
```

### Error codes

- `VALIDATION_ERROR` (`400`)
- `UNAUTHORIZED` (`401`)
- `FORBIDDEN` (`403`)
- `PAYLOAD_TOO_LARGE` (`413`)
- `RATE_LIMITED` (`429`)
- `INTERNAL_ERROR` (`500`)
- `SERVICE_UNAVAILABLE` (`503`)

---

## Validation rules

- `function.source_code` must be non-empty UTF-8 text.
- `top_k` must be integer in `[1, 50]`.
- `tags_any`, `tags_all`, `risk_types_any` must be string arrays.
- `include_case_ids` and `exclude_case_ids` must not overlap.
- If provided, enum fields must match GeoCase allowed values.

---

## Deterministic behavior requirements

To keep outputs stable and explainable:

1. Apply hard constraints before ranking.
2. Use deterministic tie-breaking (e.g., `score desc`, then `case_id asc`).
3. Return the exact `resolved_selectors` used.
4. If fallback relaxation is used, include explicit note in `notes`.

---

## Operational recommendations

- Do not store raw `source_code` by default.
- Store only fingerprints/hashes for cache keys.
- Emit structured logs with `request_id`, latency, and selected case IDs.
- Version rule sets and include version in response.
- Add benchmark-based quality gates before deployment.

---

## Example curl request

```bash
curl -X POST "https://api.example.com/v1/recommendations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "function": {
      "language": "python",
      "source_code": "def clip_and_reproject(gdf, bbox, epsg): ..."
    },
    "explanation": "Issues near antimeridian.",
    "selector_constraints": {
      "category": "vector",
      "geometry_type": "Polygon"
    },
    "top_k": 5
  }'
```

This specification is intended as the implementation contract for service and client teams.
