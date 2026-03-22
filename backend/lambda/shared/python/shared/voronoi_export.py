from __future__ import annotations

import math
from statistics import mean
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
CENTROID_STEP = 0.2
RADIAL_GAIN = 0.075
SEED_REPULSION_DISTANCE = 18.0
SEED_REPULSION_STEP = 0.12
MAX_CENTER_SHARED_POLYGONS = 1
CENTER_SHARE_RADIUS = 6.0
MIN_VERTEX_COUNT = 4
MAX_ACCEPTABLE_ERROR = 0.32
INITIALIZATION_VARIANTS = 6
CORNER_ROUND_BASE_RADIUS = 2.5
CORNER_ROUND_RATIO = 0.12

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
    variant: int = 0,
    radius: float = SEMICIRCLE_RADIUS,
) -> list[Point]:
    count = len(categories)
    if count == 0:
        return []
    if count == 1:
        return [(0.0, radius * 0.42)]

    ring_patterns = [
        [0.82, 0.58, 0.38],
        [0.74, 0.5, 0.66],
        [0.68, 0.84, 0.48],
        [0.78, 0.62, 0.44],
    ]
    ring_pattern = ring_patterns[variant % len(ring_patterns)]
    max_weight = max(category["weight"] for category in categories) or 1.0
    seeds: list[Point] = []

    for index, category in enumerate(categories):
        ring_index = (index + variant) % len(ring_pattern)
        base_ratio = ring_pattern[ring_index]
        weight_offset = (0.5 - (category["weight"] / max_weight)) * 0.08
        ratio = min(max(base_ratio + weight_offset, 0.34), 0.86)
        angle_step = math.pi / (count + 1)
        angle_offset = ((variant % 3) - 1) * angle_step * 0.18
        angle = math.pi - ((index + 1) * angle_step) + angle_offset
        x = radius * ratio * math.cos(angle)
        y = radius * ratio * math.sin(angle)
        seeds.append(project_point_to_semicircle((x, y), radius * 0.94))

    spread_seeds(seeds)
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

    polygons: list[Polygon]
    metrics: list[dict[str, float]]
    iteration_count: int

    candidates: list[tuple[list[Polygon], list[dict[str, float]], int]] = []

    try:
        candidates.append(
            generate_weighted_semicircle_voronoi(
                categories,
                parent_polygon,
                target_areas,
            )
        )
    except Exception:
        pass

    try:
        candidates.append(
            build_irregular_voronoi_fallback(
                categories,
                parent_polygon,
                target_areas,
            )
        )
    except Exception:
        pass

    chosen_candidate = choose_best_voronoi_candidate(candidates)
    if chosen_candidate is None:
        polygons, metrics, iteration_count = build_fallback_radial_area_rows(
            categories,
            target_areas,
        )
    else:
        polygons, metrics, iteration_count = chosen_candidate

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
    if len(categories) == 2:
        return build_two_category_weighted_split(categories, parent_polygon, target_areas)

    best_candidate: tuple[list[Polygon], list[dict[str, float]], int] | None = None
    best_score = float("inf")

    for variant in range(INITIALIZATION_VARIANTS):
        candidate = relax_cells_to_target_areas(
            categories,
            parent_polygon,
            target_areas,
            initialize_seed_points(categories, variant=variant),
        )
        score = candidate_score(*candidate[:2])
        if score < best_score:
            best_candidate = candidate
            best_score = score
        if is_quality_acceptable(candidate[0], candidate[1]):
            return candidate

    if best_candidate is None:
        raise ValueError("no_weighted_candidate")

    return best_candidate


def build_two_category_weighted_split(
    categories: list[dict[str, Any]],
    parent_polygon: Polygon,
    target_areas: list[float],
) -> tuple[list[Polygon], list[dict[str, float]], int]:
    seed_left, seed_right = initialize_seed_points(categories, variant=2)
    ax = seed_right[0] - seed_left[0]
    ay = seed_right[1] - seed_left[1]
    target_area = target_areas[0]
    best_candidate: tuple[list[Polygon], list[dict[str, float]], int] | None = None
    best_error = float("inf")

    projection_values = [(ax * point[0]) + (ay * point[1]) for point in parent_polygon]
    low = min(projection_values) - 20.0
    high = max(projection_values) + 20.0

    for iteration in range(1, 65):
        limit = (low + high) / 2
        left_polygon = clip_polygon(parent_polygon, ax, ay, limit)
        right_polygon = clip_polygon(parent_polygon, -ax, -ay, -limit)
        if len(left_polygon) < 3 or len(right_polygon) < 3:
            break

        polygons = [left_polygon, right_polygon]
        metrics = compute_cell_metrics(categories, polygons, target_areas)
        area_error = abs(metrics[0]["actualArea"] - target_area)
        if area_error < best_error:
            best_candidate = ([polygon[:] for polygon in polygons], [metric.copy() for metric in metrics], iteration)
            best_error = area_error

        if metrics[0]["actualArea"] < target_area:
            low = limit
        else:
            high = limit

    if best_candidate is None:
        raise ValueError("two_category_split_failed")

    return best_candidate


def build_irregular_voronoi_fallback(
    categories: list[dict[str, Any]],
    parent_polygon: Polygon,
    target_areas: list[float],
) -> tuple[list[Polygon], list[dict[str, float]], int]:
    best_candidate: tuple[list[Polygon], list[dict[str, float]], int] | None = None
    best_score = float("inf")

    for variant in range(INITIALIZATION_VARIANTS, INITIALIZATION_VARIANTS + 5):
        seeds = initialize_seed_points(categories, variant=variant)
        power_weights = [target_area / (math.pi * SEMICIRCLE_RADIUS) for target_area in target_areas]
        polygons = build_power_cells(seeds, power_weights, parent_polygon)
        if any(len(polygon) < 3 for polygon in polygons):
            continue
        metrics = compute_cell_metrics(categories, polygons, target_areas)
        candidate = (polygons, metrics, 0)
        score = candidate_score(polygons, metrics)
        if score < best_score:
            best_candidate = candidate
            best_score = score
        if is_quality_acceptable(polygons, metrics, relaxed=True):
            return candidate

    if best_candidate is not None:
        return best_candidate

    raise ValueError("no_irregular_candidate")


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
    categories: list[dict[str, Any]],
    parent_polygon: Polygon,
    target_areas: list[float],
    seeds: list[Point],
) -> tuple[list[Polygon], list[dict[str, float]], int]:
    power_weights = [
        target_area / (math.pi * SEMICIRCLE_RADIUS)
        for target_area in target_areas
    ]
    best_candidate: tuple[list[Polygon], list[dict[str, float]], int] | None = None
    best_score = float("inf")

    for iteration in range(1, MAX_ITERATIONS + 1):
        polygons = build_power_cells(seeds, power_weights, parent_polygon)
        if any(len(polygon) < 3 for polygon in polygons):
            break

        metrics = compute_cell_metrics(categories, polygons, target_areas)
        score = candidate_score(polygons, metrics)
        if score < best_score:
            best_candidate = ([polygon[:] for polygon in polygons], [metric.copy() for metric in metrics], iteration)
            best_score = score

        if max(metric["relativeError"] for metric in metrics) < CONVERGENCE_THRESHOLD:
            return polygons, metrics, iteration

        update_seed_and_weight_parameters(seeds, power_weights, polygons, metrics)

    if best_candidate is None:
        raise ValueError("relaxation_failed")

    return best_candidate


def update_seed_and_weight_parameters(
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

        power_weights[index] = max(0.0, power_weights[index] + (error_delta * WEIGHT_GAIN))

        centroid = polygon_centroid(polygon)
        moved = (
            seed[0] * (1 - CENTROID_STEP) + centroid[0] * CENTROID_STEP,
            seed[1] * (1 - CENTROID_STEP) + centroid[1] * CENTROID_STEP,
        )

        radial_distance = math.hypot(moved[0], moved[1]) or 1.0
        outward_scale = 1 - (relative_delta * RADIAL_GAIN)
        adjusted = (
            moved[0] * outward_scale,
            moved[1] * outward_scale,
        )

        if radial_distance <= EPSILON:
            adjusted = centroid

        seeds[index] = project_point_to_semicircle(adjusted, SEMICIRCLE_RADIUS * 0.95)

    spread_seeds(seeds)


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

    rounded_polygon = round_polygon_corners(polygon)
    closed_polygon = close_polygon(rounded_polygon)
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


def round_polygon_corners(polygon: Polygon) -> Polygon:
    deduped = dedupe_polygon(polygon)
    if len(deduped) < 3:
        return deduped

    rounded: Polygon = []
    point_count = len(deduped)

    for index, current in enumerate(deduped):
        previous = deduped[index - 1]
        following = deduped[(index + 1) % point_count]

        previous_length = math.hypot(current[0] - previous[0], current[1] - previous[1])
        next_length = math.hypot(following[0] - current[0], following[1] - current[1])
        corner_radius = min(
            CORNER_ROUND_BASE_RADIUS,
            previous_length * CORNER_ROUND_RATIO,
            next_length * CORNER_ROUND_RATIO,
        )

        if corner_radius <= EPSILON:
            rounded.append(current)
            continue

        start = move_towards(current, previous, corner_radius)
        end = move_towards(current, following, corner_radius)

        if min(
            math.hypot(current[0], current[1]),
            math.hypot(start[0], start[1]),
            math.hypot(end[0], end[1]),
        ) <= (CENTER_SHARE_RADIUS * 1.15):
            rounded.append(current)
            continue

        if not rounded or not points_close(rounded[-1], start):
            rounded.append(start)
        if not points_close(start, end):
            rounded.append(end)

    return dedupe_polygon(rounded)


def move_towards(origin: Point, target: Point, distance: float) -> Point:
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    length = math.hypot(dx, dy)
    if length <= EPSILON:
        return origin
    scale = distance / length
    return (
        round(origin[0] + (dx * scale), 6),
        round(origin[1] + (dy * scale), 6),
    )


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


def choose_best_voronoi_candidate(
    candidates: list[tuple[list[Polygon], list[dict[str, float]], int]],
) -> tuple[list[Polygon], list[dict[str, float]], int] | None:
    if not candidates:
        return None

    acceptable = [
        candidate
        for candidate in candidates
        if is_quality_acceptable(candidate[0], candidate[1])
    ]
    if acceptable:
        return min(acceptable, key=lambda candidate: candidate_score(candidate[0], candidate[1]))

    structurally_valid = [
        candidate
        for candidate in candidates
        if is_structurally_voronoi_like(candidate[0])
    ]
    if structurally_valid:
        return min(structurally_valid, key=lambda candidate: candidate_score(candidate[0], candidate[1]))

    relaxed = [
        candidate
        for candidate in candidates
        if is_quality_acceptable(candidate[0], candidate[1], relaxed=True)
    ]
    if relaxed:
        return min(relaxed, key=lambda candidate: candidate_score(candidate[0], candidate[1]))

    return min(candidates, key=lambda candidate: candidate_score(candidate[0], candidate[1]))


def is_quality_acceptable(
    polygons: list[Polygon],
    metrics: list[dict[str, float]],
    relaxed: bool = False,
) -> bool:
    if not polygons or any(len(polygon) < 3 for polygon in polygons):
        return False

    center_shared_count = count_center_shared_polygons(polygons)
    low_vertex_count = sum(1 for polygon in polygons if unique_vertex_count(polygon) < MIN_VERTEX_COUNT)
    max_relative_error = max(metric["relativeError"] for metric in metrics)

    if center_shared_count > (MAX_CENTER_SHARED_POLYGONS + (1 if relaxed else 0)):
        return False
    if low_vertex_count > (1 if relaxed else 0):
        return False
    if max_relative_error > (MAX_ACCEPTABLE_ERROR + (0.08 if relaxed else 0)):
        return False

    return True


def is_structurally_voronoi_like(polygons: list[Polygon]) -> bool:
    if not polygons or any(len(polygon) < 3 for polygon in polygons):
        return False

    if count_center_shared_polygons(polygons) > 0:
        return False

    polygons_with_many_vertices = sum(
        1 for polygon in polygons if unique_vertex_count(polygon) >= MIN_VERTEX_COUNT
    )
    if polygons_with_many_vertices < max(1, len(polygons) - 1):
        return False

    return True


def candidate_score(polygons: list[Polygon], metrics: list[dict[str, float]]) -> float:
    max_relative_error = max(metric["relativeError"] for metric in metrics)
    mean_relative_error = mean(metric["relativeError"] for metric in metrics)
    center_penalty = count_center_shared_polygons(polygons) * 0.45
    low_vertex_penalty = sum(
        1 for polygon in polygons if unique_vertex_count(polygon) < MIN_VERTEX_COUNT
    ) * 0.28
    sliver_penalty = sum(1 for polygon in polygons if polygon_sliver_ratio(polygon) < 0.015) * 0.2
    return max_relative_error + mean_relative_error + center_penalty + low_vertex_penalty + sliver_penalty


def count_center_shared_polygons(polygons: list[Polygon]) -> int:
    return sum(
        1
        for polygon in polygons
        if any(math.hypot(point[0], point[1]) <= CENTER_SHARE_RADIUS for point in polygon)
    )


def unique_vertex_count(polygon: Polygon) -> int:
    return len(dedupe_polygon(polygon))


def polygon_sliver_ratio(polygon: Polygon) -> float:
    xs = [point[0] for point in polygon]
    ys = [point[1] for point in polygon]
    width = max(xs) - min(xs) if xs else 0.0
    height = max(ys) - min(ys) if ys else 0.0
    box_area = max(width * height, EPSILON)
    return polygon_area(polygon) / box_area


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
    if math.hypot(x, y) < CENTER_SHARE_RADIUS * 2:
        angle = math.atan2(max(y, EPSILON), x if abs(x) > EPSILON else EPSILON)
        x = math.cos(angle) * CENTER_SHARE_RADIUS * 2.2
        y = math.sin(angle) * CENTER_SHARE_RADIUS * 2.2
    return round(x, 6), round(y, 6)


def spread_seeds(seeds: list[Point]) -> None:
    for _ in range(3):
        moved = False
        for left_index in range(len(seeds)):
            for right_index in range(left_index + 1, len(seeds)):
                left = seeds[left_index]
                right = seeds[right_index]
                dx = right[0] - left[0]
                dy = right[1] - left[1]
                distance = math.hypot(dx, dy)
                if distance < SEED_REPULSION_DISTANCE and distance > EPSILON:
                    push = (SEED_REPULSION_DISTANCE - distance) * SEED_REPULSION_STEP
                    ux = dx / distance
                    uy = dy / distance
                    seeds[left_index] = project_point_to_semicircle(
                        (left[0] - ux * push, left[1] - uy * push),
                        SEMICIRCLE_RADIUS * 0.95,
                    )
                    seeds[right_index] = project_point_to_semicircle(
                        (right[0] + ux * push, right[1] + uy * push),
                        SEMICIRCLE_RADIUS * 0.95,
                    )
                    moved = True
        if not moved:
            break


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
