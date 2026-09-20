from shapely.geometry import Polygon, box


def voronoi_cells(points, bounds):
    n = len(points)
    minx, miny, maxx, maxy = bounds
    clip = box(minx, miny, maxx, maxy)

    dx = maxx - minx
    dy = maxy - miny
    diag = (dx ** 2 + dy ** 2) ** 0.5
    big = max(diag, 1.0) * 1000.0

    cells = []
    for i in range(n):
        xi, yi = points[i]
        cell = clip
        for j in range(n):
            if i == j:
                continue
            xj, yj = points[j]

            mx = (xi + xj) / 2.0
            my = (yi + yj) / 2.0
            dirx = xj - xi
            diry = yj - yi
            norm = (dirx ** 2 + diry ** 2) ** 0.5
            ux, uy = dirx / norm, diry / norm
            # perpendicular direction to the bisector line
            px, py = -uy, ux

            p1 = (mx + px * big, my + py * big)
            p2 = (mx - px * big, my - py * big)

            # half-plane on the side of point i: a large quad extending
            # away from j past i
            back_x, back_y = mx - ux * big, my - uy * big
            half_plane = Polygon([
                p1,
                p2,
                (p2[0] - ux * big, p2[1] - uy * big),
                (p1[0] - ux * big, p1[1] - uy * big),
            ])

            cell = cell.intersection(half_plane)

        cells.append(cell)

    return cells