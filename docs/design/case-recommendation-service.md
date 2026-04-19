# Case Recommendation Service

This document describes a proposed web service where a user submits a geospatial function (plus optional explanation), and the service recommends GeoCase cases where that function is most likely to fail.

## Why this service

See also:

- [Case Recommendation User Flow](case-recommendation-user-flow.md)
- [Case Recommendation API Specification](case-recommendation-api-spec.md)

Many users do not know which case IDs to test first.

This service reduces that friction by translating function intent and implementation signals into GeoCase selectors and ranked case recommendations.

## Problem statement

Given:

- function code (or function reference),
- optional natural-language explanation,
- optional constraints (category, format, geometry type),

return:

- top matching GeoCase cases,
- why each case is risky for that function,
- ready-to-use selector/test snippets.

## Desired outcome

- Users test edge cases without manually browsing catalog IDs.
- Teams get consistent, explainable recommendations.
- GeoCase metadata (`tags`, `risk_types`, `category`, `geometry_type`, `format`) is used as the core matching layer.

---

## High-level architecture

1. **API Layer**
   - Receives recommendation requests.
   - Validates schema and auth.

2. **Analyzer Layer**
   - Extracts signals from function code and optional explanation.
   - Produces inferred risk hints (e.g., CRS mismatch, coordinate wrapping, nodata handling).

3. **Selector + Ranking Layer**
   - Applies hard selector constraints first.
   - Ranks candidate cases using metadata match quality and risk relevance.

4. **Response Composer**
   - Returns ranked cases with explanation (`matched_on`, `reason`, confidence score).

5. **Telemetry + Feedback**
   - Captures outcomes (accepted/rejected recommendations) for iterative tuning.

---

## Request and response model

For the concrete API contract, see [Case Recommendation API Specification](case-recommendation-api-spec.md).

## Request

- `function.language`: e.g., `python`
- `function.name`: optional identifier
- `function.source_code`: function implementation text
- `explanation`: optional user intent/problem statement
- `selector_constraints`: optional explicit filters
  - `category`, `geometry_type`, `format`, `tags_any`, `risk_types_any`, etc.
- `top_k`: optional max recommendations

## Response

- `request_id`
- `resolved_selectors`
- `recommendations[]`
  - `case_id`
  - `score`
  - `matched_on`
  - `reason`
- optional `pytest_template` snippet
- optional `notes` (fallback behavior, confidence caveats)

---

## Recommendation logic

## Step 1: Hard filters

Apply explicit constraints first:

- `category`
- `geometry_type`
- `format`
- `storage_class` / `test_tier` (if provided)

This guarantees recommendations stay within user scope.

## Step 2: Signal extraction

Infer risk signals from:

- keywords in explanation (e.g., “dateline”, “nodata”, “reproject”),
- code patterns (CRS transform calls, raster masks, geometry validity fixes),
- function I/O assumptions (vector/raster/netcdf).

## Step 3: Scoring

Score candidates by weighted match:

- `risk_types_any` match,
- `tags_any` / `tags_all` overlap,
- `category` / `geometry_type` / `format` compatibility,
- optional historical success/failure feedback.

## Step 4: Explainability

For each recommendation, return:

- what matched,
- why it may fail,
- confidence score relative to this request.

---

## Operational rollout plan

## Phase 0 (Design)

1. Define API schema and response contract.
2. Freeze selector field compatibility with current GeoCase metadata.
3. Define quality metrics (precision@k, recommendation acceptance rate).

## Phase 1 (MVP)

1. Implement `POST /v1/recommendations`.
2. Use deterministic, rule-based scoring from metadata.
3. Return top-N recommendations with reasons.
4. Add minimal logs (no raw source code by default).

## Phase 2 (Quality + Staging)

1. Build offline benchmark from existing known edge-case examples.
2. Compare recommendation quality across versions.
3. Add auth, rate limits, and request tracing.
4. Introduce fallback rules if filters yield zero matches.

## Phase 3 (Production)

1. Add caching by function fingerprint + selector tuple.
2. Set SLOs (latency and recommendation stability).
3. Add dashboards for case distribution and drift.
4. Add controlled feedback loop for score tuning.

## Phase 4 (Advanced)

1. Optional LLM-assisted risk inference.
2. Optional sandbox execution against recommended cases.
3. Automated generation of `pytest` scaffold from recommendations.

---

## Example response behavior

User function says: “Clip polygons and reproject to EPSG:3857; issues near antimeridian.”

Service should prioritize cases such as:

- `dateline_crossing_polygon` (coordinate wrapping risk),
- `polygon_with_hole` (topology/ring preservation risk),
- other vector polygon cases with matching tags and risk types.

And return a ready-to-copy test skeleton using:

- `@pytest.mark.geocase_select(...)` when IDs are not required,
- `@pytest.mark.geocase_case(...)` for explicit focused checks.

---

## Key risks and mitigations

- **Low precision recommendations**: maintain benchmark suite and gate releases by precision@k.
- **No matches due to strict constraints**: implement progressive relaxation with explicit notes.
- **Sensitive code handling**: default to no code retention, encrypted transport/storage, redacted logs.
- **Metadata drift**: version schema and validate selector compatibility during deployment.
- **Latency spikes**: request timeouts, caching, and queue-based fallback mode.

---

## Implementation checklist

1. Add API spec and request validation models.
2. Implement metadata index for selector fields.
3. Build rule-based analyzer and scorer.
4. Add explainability payload (`matched_on`, `reason`).
5. Add recommendation benchmark tests.
6. Add observability (metrics, tracing, error taxonomy).
7. Add deployment and rollback runbook.

This creates a practical path from idea to a production-grade recommendation service built on GeoCase metadata primitives.
