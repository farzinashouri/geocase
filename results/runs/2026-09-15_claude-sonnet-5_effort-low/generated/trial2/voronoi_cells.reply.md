```python
from shapely.geometry import Polygon, box


def voronoi_cells(points, bounds):
    from shapely.ops import unary_union

    n = len(points)
    minx, miny, maxx, maxy = bounds
    width = maxx - minx
    height = maxy - miny
    diag = (width ** 2 + height ** 2) ** 0.5
    big = diag * 10 + 1.0

    clip = box(minx, miny, maxx, maxy)

    cells = []
    for i in range(n):
        px, py = points[i]
        cell = box(minx - big, miny - big, maxx + big, maxy + big)
        for j in range(n):
            if i == j:
                continue
            qx, qy = points[j]
            mx = (px + qx) / 2.0
            my = (py + qy) / 2.0
            dx = qx - px
            dy = qy - py

            tx = -dy
            ty = dx
            tlen = (tx ** 2 + ty ** 2) ** 0.5
            ux = tx / tlen
            uy = ty / tlen

            p1 = (mx + ux * big, my + uy * big)
            p2 = (mx - ux * big, my - uy * big)

            nx, ny = dx, dy
            nlen = (nx ** 2 + ny ** 2) ** 0.5
            nnx, nny = nx / nlen, ny / nlen

            p3 = (p2[0] - nnx * 2 * big, p2[1] - nny * 2 * big)
            p4 = (p1[0] - nnx * 2 * big, p1[1] - nny * 2 * big)

            half_plane = Polygon([p1, p2, p3, p4])
            cell = cell.intersection(half_plane)

        cell = cell.intersection(clip)
        cells.append(cell)

    return cells
```