```python
"""Bounded Voronoi diagram construction using shapely."""

from shapely.geometry import Polygon, box
from shapely.ops import unary_union


def voronoi_cells(points, bounds):
    minx, miny, maxx, maxy = bounds
    rect = box(minx, miny, maxx, maxy)

    diag = ((maxx - minx) ** 2 + (maxy - miny) ** 2) ** 0.5
    big = diag * 1000.0 + 1.0

    cells = []
    for i, (xi, yi) in enumerate(points):
        cell = rect
        for j, (xj, yj) in enumerate(points):
            if i == j:
                continue
            mx = (xi + xj) / 2.0
            my = (yi + yj) / 2.0
            dx = xj - xi
            dy = yj - yi
            # Direction along the bisector (perpendicular to (dx, dy)),
            # pointing to the left of the vector from j to i (i.e. towards i's side).
            ux = -dy
            uy = dx
            length = (ux ** 2 + uy ** 2) ** 0.5
            ux /= length
            uy /= length

            p1 = (mx + ux * big, my + uy * big)
            p2 = (mx - ux * big, my - uy * big)

            # Push a point far towards i to build a half-plane polygon
            # containing i, bounded by the perpendicular bisector.
            nx = -dx
            ny = -dy
            nlen = (nx ** 2 + ny ** 2) ** 0.5
            nx = nx / nlen * big
            ny = ny / nlen * big

            half_plane = Polygon([
                p1,
                p2,
                (p2[0] + nx, p2[1] + ny),
                (p1[0] + nx, p1[1] + ny),
            ])

            cell = cell.intersection(half_plane)

        cells.append(cell)

    return cells
```