# Antimeridian Crossing LineString

## Purpose
Tests handling of lines that cross the 180° longitude line (antimeridian/International Date Line).

## The Problem
A line from (179.5°, 20°) to (-179.5°, 20°) should travel **1 degree east** across the Pacific.

However, naive implementations that simply interpolate between coordinates will draw a line
**359 degrees west** around the entire globe, passing through the Atlantic, Africa, and Asia.

## Expected Behavior
- **Geodesic calculations**: Should compute the short (~111 km) distance across the Pacific
- **Rendering**: Should draw the short path, not wrap around the globe
- **Bounding box**: Should recognize the span crosses the antimeridian

## Detection
A line crosses the antimeridian if:
1. Adjacent coordinates have longitude signs that differ (one positive, one negative)
2. The absolute difference in longitude > 180°

## Real-World Occurrence
- Flight paths across the Pacific (Tokyo → Los Angeles)
- Shipping routes
- Satellite ground tracks
- Any global dataset that doesn't stop at the dateline
