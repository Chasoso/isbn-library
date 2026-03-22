from __future__ import annotations

import math
from typing import Any

Point = tuple[float, float]
Polygon = list[Point]

SEMICIRCLE_RADIUS = 100.0
SEMICIRCLE_SEGMENTS = 120
MIN_WEIGHT = 0.1
EPSILON = 1e-9
MAX_ITERATIONS = 96
CONVERGENCE_THRESHOLD = 0.15
WEIGHT_GAIN = 0.012
CENTROID_STEP = 0.18
RADIAL_GAIN = 0.09
MAX_ACCEPTABLE_ERROR = 0.28

VORONOI_HEADERS = [
    "polygonId",
    "categoryId",
    "categoryName",
    "color",
    "sortOrder",
    "bookCount",
    "weight",
    "targetArea",
    "actualArea",
    "areaError",
    "relativeError",
    "path",
    "x",
    "y",
    "partIndex",
    "centroidX",
    "centroidY",
    "iterationCount",
]


def build_category_book_counts(
    category_items: list[dict[str, Any]],
    book_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in book_items:
        category_id = str(item.get("categoryId", "")).strip()
        if category_id:
            counts[category_id] = counts.get(category_id, 0) + 1

    sorted_categories = sorted(
        category_items,
        key=lambda item: (int(item.get("sortOrder", 9999)), item.get("categoryId", "")),
    )

    categories: list[dict[str, Any]] = []
    for item in sorted_categories:
        category_id = str(item.get("categoryId", ""))
        book_count = counts.get(category_id, 0)
        categories.append(
            {
                "categoryId": category_id,
                "categoryName": str(item.get("name", "")),
                "color": str(item.get("color", "")),
                "sortOrder": int(item.get("sortOrder", 9999)),
                "bookCount": book_count,
                "weight": build_effective_weight(book_count),
            }
        )

    return categories


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


def initialize_seed_points(
    categories: list[dict[str, Any]],
    radius: float = SEMICIRCLE_RADIUS,
) -> list[Point]:
    count = len(categories)
    if count == 0:
        return []
    if count == 1:
        return [(0.0, radius * 0.42)]

    usable_radius = radius * 0.76
    max_weight = max(category["weight"] for category in categories) or 1.0
    seeds: list[Point] = []

    for index, category in enumerate(categories):
        angle = math.pi - ((index + 1) * math.pi / (count + 1))
        base_ratio = 0.64 - ((category["weight"] / max_weight) * 0.18)
        stagger = 0.04 if index % 2 == 0 else -0.03
        radial_ratio = min(max(base_ratio + stagger, 0.38), 0.78)
        x = usable_radius * radial_ratio * math.cos(angle)
        y = usable_radius * radial_ratio * math.sin(angle) + radius * 0.16
        seeds.append(project_point_to_semicircle((x, y), radius * 0.94))

    return seeds


def build_target_areas(
    categories: list[dict[str, Any]],
    radius: float = SEMICIRCLE_RADIUS,
) -> list[float]:
    semicircle_area = 0.5 * math.pi * radius * radius
    total_weight = sum(category["weight"] for category in categories) or 1.0
    return [
        semicircle_area * (category["weight"] / total_weight)
        for category in categories
    ]


def build_category_voronoi_rows(
    category_items: list[dict[str, Any]],
    book_items: list[dict[str, Any]],
) -> list[list[Any]]:
    rows: list[list[Any]] = [VORONOI_HEADERS]
    categories = build_category_book_counts(category_items, book_items)
    if not categories:
        return rows

    parent_polygon = make_semicircle_polygon()
    target_areas = build_target_areas(categories)

    try:
        polygons, metrics, iteration_count = generate_weighted_semicircle_voronoi(
            categories,
            parent_polygon,
            target_areas,
        )
        if max(metric["relativeError"] for metric in metrics) > MAX_ACCEPTABLE_ERROR:
            raise ValueError("weighted_voronoi_not_close_enough")
    except Exception:
        polygons, metrics, iteration_count = build_fallback_radial_area_rows(
            categories,
            target_areas,
        )

    for category, polygon, metric in zip(categories, polygons, metrics, strict=False):
        rows.extend(
            polygon_to_rows(
                polygon_id=f"category-{category['categoryId']}",
                polygon=polygon,
                category=category,
                metrics=metric,
                iteration_count=iteration_count,
            )
        )

    return rows


def generate_weighted_semicircle_voronoi(
    categories: list[dict[str, Any]],
    parent_polygon: Polygon,
    target_areas: list[float],
) -> tuple[list[Polygon], list[dict[str, float]], int]:
    if len(categories) == 1:
        metrics = compute_cell_metrics(categories, [parent_polygon], target_areas)
        return [parent_polygon], metrics, 0

    seeds = initialize_seed_points(categories)
    power_weights = [
        target_area / (math.pi * SEMICIRCLE_RADIUS)
        for target_area in target_areas
    ]
    best_polygons: list[Polygon] = []
    best_metrics: list[dict[str, float]] = []
    best_error = float("inf")

    for iteration in range(1, MAX_ITERATIONS + 1):
        polygons = build_power_cells(seeds, power_weights, parent_polygon)
        if any(len(polygon) < 3 for polygon in polygons):
            raise ValueError("invalid_power_cells")

        metrics = compute_cell_metrics(categories, polygons, target_areas)
        max_relative_error = max(metric["relativeError"] for metric in metrics)
        mean_relative_error = sum(metric["relativeError"] for metric in metrics) / len(metrics)

        if max_relative_error < best_error:
            best_error = max_relative_error
            best_polygons = [polygon[:] for polygon in polygons]
            best_metrics = [metric.copy() for metric in metrics]

        if max_relative_error < CONVERGENCE_THRESHOLD:
            return polygons, metrics, iteration

        if iteration > 12 and abs(best_error - mean_relative_error) < 0.0005:
            break

        relax_cells_to_target_areas(
            seeds,
            power_weights,
            polygons,
            metrics,
        )

    if not best_polygons:
        raise ValueError("weighted_voronoi_failed")

    return best_polygons, best_metrics, MAX_ITERATIONS


def compute_cell_metrics(
    categories: list[dict[str, Any]],
    polygons: list[Polygon],
    target_areas: list[float],
) -> list[dict[str, float]]:
    metrics: list[dict[str, float]] = []
    for category, polygon, target_area in zip(categories, polygons, target_areas, strict=False):
        actual_area = polygon_area(polygon)
        centroid_x, centroid_y = polygon_centroid(polygon)
        area_error = actual_area - target_area
        relative_error = abs(area_error) / max(target_area, EPSILON)
        metrics.append(
            {
                "weight": category["weight"],
                "targetArea": round(target_area, 6),
                "actualArea": round(actual_area, 6),
                "areaError": round(area_error, 6),
                "relativeError": round(relative_error, 6),
                "centroidX": round(centroid_x, 6),
                "centroidY": round(centroid_y, 6),
            }
        )
    return metrics


def relax_cells_to_target_areas(
    seeds: list[Point],
    power_weights: list[float],
    polygons: list[Polygon],
    metrics: list[dict[str, float]],
) -> None:
    for index, (seed, polygon, metric) in enumerate(zip(seeds, polygons, metrics, strict=False)):
        target_area = metric["targetArea"]
        actual_area = metric["actualArea"]
        error_delta = target_area - actual_area
        relative_delta = error_delta / max(target_area, EPSILON)

        power_weights[index] = max(
            0.0,
            power_weights[index] + (error_delta * WEIGHT_GAIN),
        )

        centroid = polygon_centroid(polygon)
        moved = (
            seed[0] * (1 - CENTROID_STEP) + centroid[0] * CENTROID_STEP,
            seed[1] * (1 - CENTROID_STEP) + centroid[1] * CENTROID_STEP,
        )

        distance = math.hypot(moved[0], moved[1]) or 1.0
        radial_factor = 1 - (relative_delta * RADIAL_GAIN)
        adjusted = (
            moved[0] * radial_factor,
            moved[1] * radial_factor,
        )

        if distance <= EPSILON:
            adjusted = centroid

        seeds[index] = project_point_to_semicircle(adjusted, SEMICIRCLE_RADIUS * 0.95)


def polygon_to_rows(
    polygon_id: str,
    polygon: Polygon,
    category: dict[str, Any],
    metrics: dict[str, float],
    iteration_count: int,
    part_index: int = 0,
) -> list[list[Any]]:
    if len(polygon) < 3:
        return []

    closed_polygon = close_polygon(polygon)
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
                metrics["weight"],
                metrics["targetArea"],
                metrics["actualArea"],
                metrics["areaError"],
                metrics["relativeError"],
                path,
                round(x, 6),
                round(y, 6),
                part_index,
                metrics["centroidX"],
                metrics["centroidY"],
                iteration_count,
            ]
        )

    return rows


def build_fallback_radial_area_rows(
    categories: list[dict[str, Any]],
    target_areas: list[float],
) -> tuple[list[Polygon], list[dict[str, float]], int]:
    if len(categories) == 1:
        polygon = make_semicircle_polygon()
        metrics = compute_cell_metrics(categories, [polygon], target_areas)
        return [polygon], metrics, 0

    semicircle_area = 0.5 * math.pi * SEMICIRCLE_RADIUS * SEMICIRCLE_RADIUS
    start_angle = math.pi
    polygons: list[Polygon] = []

    for target_area in target_areas:
        sweep = math.pi * (target_area / semicircle_area)
        end_angle = max(0.0, start_angle - sweep)
        polygons.append(make_sector_polygon(start_angle, end_angle))
        start_angle = end_angle

    if polygons:
        consumed = sum(
            math.pi * (target_area / semicircle_area)
            for target_area in target_areas[:-1]
        )
        polygons[-1] = make_sector_polygon(math.pi - consumed, 0.0)

    metrics = compute_cell_metrics(categories, polygons, target_areas)
    return polygons, metrics, 0


def build_power_cells(
    seeds: list[Point],
    power_weights: list[float],
    parent_polygon: Polygon,
) -> list[Polygon]:
    cells: list[Polygon] = []

    for index, seed in enumerate(seeds):
        cell = parent_polygon[:]
        for other_index, other_seed in enumerate(seeds):
            if index == other_index:
                continue
            cell = clip_polygon_to_weighted_halfplane(
                cell,
                seed,
                power_weights[index],
                other_seed,
                power_weights[other_index],
            )
            if len(cell) < 3:
                break
        cells.append(cell if len(cell) >= 3 else [])

    return cells


def make_sector_polygon(
    start_angle: float,
    end_angle: float,
    radius: float = SEMICIRCLE_RADIUS,
    segments: int = 36,
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


def build_effective_weight(book_count: int) -> float:
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


def project_point_to_semicircle(point: Point, max_radius: float) -> Point:
    x, y = point
    y = max(y, 0.0)
    distance = math.hypot(x, y)
    if distance > max_radius and distance > EPSILON:
        scale = max_radius / distance
        x *= scale
        y *= scale
    return round(x, 6), round(y, 6)


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


def polygon_area(polygon: Polygon) -> float:
    if len(polygon) < 3:
        return 0.0
    area = 0.0
    closed = close_polygon(polygon)
    for index in range(len(closed) - 1):
        x1, y1 = closed[index]
        x2, y2 = closed[index + 1]
        area += x1 * y2 - x2 * y1
    return abs(area) * 0.5


def polygon_centroid(polygon: Polygon) -> Point:
    area_accumulator = 0.0
    cx = 0.0
    cy = 0.0
    closed = close_polygon(polygon)

    for index in range(len(closed) - 1):
        x1, y1 = closed[index]
        x2, y2 = closed[index + 1]
        cross = x1 * y2 - x2 * y1
        area_accumulator += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross

    if abs(area_accumulator) <= EPSILON:
        average_x = sum(point[0] for point in polygon) / len(polygon)
        average_y = sum(point[1] for point in polygon) / len(polygon)
        return average_x, average_y

    area_accumulator *= 0.5
    factor = 1 / (6 * area_accumulator)
    return cx * factor, cy * factor
