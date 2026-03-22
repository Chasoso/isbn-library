from __future__ import annotations

import math
from typing import Any

Point = tuple[float, float]
Polygon = list[Point]

SEMICIRCLE_RADIUS = 100.0
SEMICIRCLE_SEGMENTS = 120
MIN_WEIGHT = 0.2
EPSILON = 1e-9


def build_category_book_counts(
    category_items: list[dict[str, Any]],
    book_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in book_items:
        category_id = str(item.get("categoryId", "")).strip()
        if not category_id:
            continue
        counts[category_id] = counts.get(category_id, 0) + 1

    sorted_categories = sorted(
        category_items,
        key=lambda item: (int(item.get("sortOrder", 9999)), item.get("categoryId", "")),
    )

    return [
        {
            "categoryId": str(item.get("categoryId", "")),
            "categoryName": str(item.get("name", "")),
            "color": str(item.get("color", "")),
            "sortOrder": int(item.get("sortOrder", 9999)),
            "bookCount": counts.get(str(item.get("categoryId", "")), 0),
        }
        for item in sorted_categories
    ]


def make_semicircle_polygon(
    radius: float = SEMICIRCLE_RADIUS,
    segments: int = SEMICIRCLE_SEGMENTS,
) -> Polygon:
    return [
        (
            round(radius * math.cos(math.pi - (math.pi * index / segments)), 6),
            round(radius * math.sin(math.pi - (math.pi * index / segments)), 6),
        )
        for index in range(segments + 1)
    ]


def generate_semicircle_seed_points(
    categories: list[dict[str, Any]],
    radius: float = SEMICIRCLE_RADIUS,
) -> list[Point]:
    count = len(categories)
    if count == 0:
        return []
    if count == 1:
        return [(0.0, radius * 0.45)]

    max_book_count = max(category["bookCount"] for category in categories) or 1
    usable_radius = radius * 0.74
    seeds: list[Point] = []

    for index, category in enumerate(categories):
        weight_share = category["bookCount"] / max_book_count
        radial_ratio = 0.72 - (weight_share * 0.22)
        radial_ratio += 0.05 if index % 2 == 0 else -0.03
        radial_ratio = min(max(radial_ratio, 0.38), 0.78)

        angle = math.pi - ((index + 1) * math.pi / (count + 1))
        x = usable_radius * radial_ratio * math.cos(angle)
        y = usable_radius * radial_ratio * math.sin(angle) + radius * 0.18
        seeds.append((round(x, 6), round(max(y, radius * 0.18), 6)))

    return seeds


def build_category_voronoi_rows(
    category_items: list[dict[str, Any]],
    book_items: list[dict[str, Any]],
) -> list[list[Any]]:
    rows: list[list[Any]] = [[
        "polygonId",
        "categoryId",
        "categoryName",
        "color",
        "sortOrder",
        "bookCount",
        "weight",
        "path",
        "x",
        "y",
        "partIndex",
        "centroidX",
        "centroidY",
    ]]

    categories = build_category_book_counts(category_items, book_items)
    if not categories:
        return rows

    parent_polygon = make_semicircle_polygon()

    try:
        polygons = build_weighted_cells(categories, parent_polygon)
    except Exception:
        polygons = build_fallback_fan_polygons(categories, parent_polygon)

    if not polygons:
        polygons = build_fallback_fan_polygons(categories, parent_polygon)

    for category, polygon in zip(categories, polygons, strict=False):
        rows.extend(
            polygon_to_rows(
                polygon_id=f"category-{category['categoryId']}",
                polygon=polygon,
                category=category,
            )
        )

    return rows


def polygon_to_rows(
    polygon_id: str,
    polygon: Polygon,
    category: dict[str, Any],
    part_index: int = 0,
) -> list[list[Any]]:
    if len(polygon) < 3:
        return []

    closed_polygon = close_polygon(polygon)
    centroid_x, centroid_y = polygon_centroid(polygon)
    rows: list[list[Any]] = []

    for path, (x, y) in enumerate(closed_polygon):
        rows.append(
            [
                polygon_id,
                category["categoryId"],
                category["categoryName"],
                category["color"],
                category["sortOrder"],
                category["bookCount"],
                build_weight_value(category["bookCount"]),
                path,
                round(x, 6),
                round(y, 6),
                part_index,
                round(centroid_x, 6),
                round(centroid_y, 6),
            ]
        )

    return rows


def build_weighted_cells(
    categories: list[dict[str, Any]],
    parent_polygon: Polygon,
) -> list[Polygon]:
    if len(categories) == 1:
        return [parent_polygon]

    seeds = generate_semicircle_seed_points(categories)
    weights = [build_weight_value(category["bookCount"]) for category in categories]
    cells: list[Polygon] = []

    for index, seed in enumerate(seeds):
        cell = parent_polygon[:]
        for other_index, other_seed in enumerate(seeds):
            if index == other_index:
                continue
            cell = clip_polygon_to_weighted_halfplane(
                cell,
                seed,
                weights[index],
                other_seed,
                weights[other_index],
            )
            if len(cell) < 3:
                break

        cells.append(cell if len(cell) >= 3 else [])

    if any(len(cell) < 3 for cell in cells):
        return build_fallback_fan_polygons(categories, parent_polygon)

    return cells


def build_fallback_fan_polygons(
    categories: list[dict[str, Any]],
    parent_polygon: Polygon,
) -> list[Polygon]:
    if not categories:
        return []
    if len(categories) == 1:
        return [parent_polygon]

    total_weight = sum(build_weight_value(category["bookCount"]) for category in categories)
    start_angle = math.pi
    polygons: list[Polygon] = []

    for category in categories:
        sweep = math.pi * build_weight_value(category["bookCount"]) / total_weight
        end_angle = start_angle - sweep
        polygons.append(make_sector_polygon(start_angle, end_angle))
        start_angle = end_angle

    if polygons:
        polygons[-1] = make_sector_polygon(
            math.pi - sum(
                math.pi * build_weight_value(category["bookCount"]) / total_weight
                for category in categories[:-1]
            ),
            0.0,
        )

    return polygons


def make_sector_polygon(
    start_angle: float,
    end_angle: float,
    radius: float = SEMICIRCLE_RADIUS,
    segments: int = 24,
) -> Polygon:
    points: Polygon = [(0.0, 0.0)]
    for index in range(segments + 1):
        ratio = index / segments
        angle = start_angle + (end_angle - start_angle) * ratio
        points.append(
            (
                round(radius * math.cos(angle), 6),
                round(radius * math.sin(angle), 6),
            )
        )
    return points


def build_weight_value(book_count: int) -> float:
    return round(max(float(book_count), MIN_WEIGHT), 6)


def clip_polygon_to_weighted_halfplane(
    polygon: Polygon,
    seed: Point,
    weight: float,
    other_seed: Point,
    other_weight: float,
) -> Polygon:
    ax = 2 * (other_seed[0] - seed[0])
    ay = 2 * (other_seed[1] - seed[1])
    limit = (
        (other_seed[0] ** 2 + other_seed[1] ** 2 - other_weight)
        - (seed[0] ** 2 + seed[1] ** 2 - weight)
    )
    return clip_polygon(polygon, ax, ay, limit)


def clip_polygon(polygon: Polygon, ax: float, ay: float, limit: float) -> Polygon:
    if not polygon:
        return []

    output: Polygon = []
    previous = polygon[-1]
    previous_value = limit - (ax * previous[0] + ay * previous[1])

    for current in polygon:
        current_value = limit - (ax * current[0] + ay * current[1])
        previous_inside = previous_value >= -EPSILON
        current_inside = current_value >= -EPSILON

        if current_inside:
            if not previous_inside:
                output.append(intersection_point(previous, current, previous_value, current_value))
            output.append(current)
        elif previous_inside:
            output.append(intersection_point(previous, current, previous_value, current_value))

        previous = current
        previous_value = current_value

    return dedupe_polygon(output)


def intersection_point(
    start: Point,
    end: Point,
    start_value: float,
    end_value: float,
) -> Point:
    denominator = start_value - end_value
    if abs(denominator) <= EPSILON:
        return end

    ratio = start_value / denominator
    return (
        round(start[0] + ((end[0] - start[0]) * ratio), 6),
        round(start[1] + ((end[1] - start[1]) * ratio), 6),
    )


def dedupe_polygon(polygon: Polygon) -> Polygon:
    deduped: Polygon = []
    for point in polygon:
        if not deduped or not points_close(deduped[-1], point):
            deduped.append(point)
    if len(deduped) > 1 and points_close(deduped[0], deduped[-1]):
        deduped.pop()
    return deduped


def close_polygon(polygon: Polygon) -> Polygon:
    if not polygon:
        return []
    if points_close(polygon[0], polygon[-1]):
        return polygon
    return [*polygon, polygon[0]]


def points_close(left: Point, right: Point) -> bool:
    return abs(left[0] - right[0]) <= EPSILON and abs(left[1] - right[1]) <= EPSILON


def polygon_centroid(polygon: Polygon) -> Point:
    area = 0.0
    cx = 0.0
    cy = 0.0
    closed = close_polygon(polygon)

    for index in range(len(closed) - 1):
        x1, y1 = closed[index]
        x2, y2 = closed[index + 1]
        cross = x1 * y2 - x2 * y1
        area += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross

    if abs(area) <= EPSILON:
        average_x = sum(point[0] for point in polygon) / len(polygon)
        average_y = sum(point[1] for point in polygon) / len(polygon)
        return average_x, average_y

    area *= 0.5
    factor = 1 / (6 * area)
    return cx * factor, cy * factor
