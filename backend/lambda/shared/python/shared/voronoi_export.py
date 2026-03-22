from __future__ import annotations

import math
from statistics import mean
from typing import Any

Point = tuple[float, float]
Polygon = list[Point]
Rect = tuple[float, float, float, float]


class PartitionFailure(ValueError):
    def __init__(self, message: str, stats: dict[str, int] | None = None) -> None:
        super().__init__(message)
        self.stats = stats or {}

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
AREA_PARTITION_MAX_ERROR = 0.12
MIN_COMPACTNESS = 0.08
MAX_ASPECT_RATIO = 6.5
MIN_THICKNESS = 6.0
EDGE_CROWDING_RADIUS = 88.0
LOCAL_SPLIT_ANGLE_OFFSETS = (-0.45, -0.22, 0.0, 0.22, 0.45)
LOCAL_SPLIT_ANGLE_OFFSETS_V2 = (-1.15, -0.82, -0.58, -0.32, -0.12, 0.0, 0.12, 0.32, 0.58, 0.82, 1.15)
MIN_LABEL_WIDTH = 10.0
MIN_LABEL_HEIGHT = 9.0
MIN_LABEL_AREA = 180.0
HARD_MIN_WIDTH = 11.5
HARD_MAX_ASPECT_RATIO = 6.0
HARD_MIN_COMPACTNESS = 0.1
HARD_MIN_AREA_PER_PERIMETER = 3.2

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
    "compactness",
    "bboxWidth",
    "bboxHeight",
    "aspectRatio",
    "qualityScore",
    "path",
    "x",
    "y",
    "partIndex",
    "centroidX",
    "centroidY",
    "iterationCount",
    "minimumWidth",
    "layoutStrategy",
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
        [0.68, 0.54, 0.42, 0.6],
        [0.62, 0.48, 0.7, 0.56],
        [0.58, 0.72, 0.46, 0.64],
        [0.66, 0.5, 0.74, 0.44],
    ]
    ring_pattern = ring_patterns[variant % len(ring_patterns)]
    placement_order = build_seed_placement_order(categories)
    placement_rank = {
        category["categoryId"]: rank
        for rank, category in enumerate(placement_order)
    }
    seeds: list[Point] = []

    for index, category in enumerate(categories):
        rank = placement_rank[category["categoryId"]]
        ring_index = (rank + variant) % len(ring_pattern)
        base_ratio = ring_pattern[ring_index]
        ring_jitter = (((rank + variant) % 5) - 2) * 0.015
        ratio = min(max(base_ratio + ring_jitter, 0.4), 0.78)
        angle_step = math.pi / (count + 1)
        angle_offset = ((variant % 3) - 1) * angle_step * 0.18
        angle = math.pi - ((rank + 1) * angle_step) + angle_offset
        x = radius * ratio * math.cos(angle)
        y = radius * ratio * math.sin(angle)
        seeds.append(project_point_to_semicircle((x, y), radius * 0.84))

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
    categories = [
        category
        for category in build_category_book_counts(category_items, book_items)
        if category["bookCount"] > 0
    ]
    if not categories:
        return rows

    polygons, metrics, iteration_count = build_recursive_binary_partition_layout(categories)

    for category, polygon, metric in zip(categories, polygons, metrics, strict=False):
        rows.extend(
            polygon_to_rows(
                polygon_id=f"category-{category['categoryId']}",
                polygon=polygon,
                category=category,
                metrics=metric,
                iteration_count=iteration_count,
                layout_strategy="recursive_binary_partition",
            )
        )

    return rows


def build_current_strategy_layout(
    categories: list[dict[str, Any]],
) -> tuple[list[Polygon], list[dict[str, float]], int]:
    parent_polygon = make_semicircle_polygon()
    target_areas = build_target_areas(categories)
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
    if chosen_candidate is not None and max(metric["relativeError"] for metric in chosen_candidate[1]) > AREA_PARTITION_MAX_ERROR:
        try:
            candidates.append(
                build_irregular_area_partition(
                    categories,
                    parent_polygon,
                    target_areas,
                )
            )
            chosen_candidate = choose_best_voronoi_candidate(candidates)
        except Exception:
            pass

    if chosen_candidate is not None:
        return chosen_candidate

    return build_fallback_radial_area_rows(categories, target_areas)


def build_new_strategy_layout(
    categories: list[dict[str, Any]],
) -> tuple[list[Polygon], list[dict[str, float]], int]:
    return build_recursive_binary_partition_layout(categories)


def build_recursive_binary_partition_layout(
    categories: list[dict[str, Any]],
) -> tuple[list[Polygon], list[dict[str, float]], int]:
    polygons, metrics, iteration_count, _ = build_recursive_binary_partition_details(categories)
    return polygons, metrics, iteration_count


def build_recursive_binary_partition_details(
    categories: list[dict[str, Any]],
) -> tuple[list[Polygon], list[dict[str, float]], int, dict[str, int | bool]]:
    target_areas = build_target_areas(categories)
    if len(categories) == 1:
        polygon = make_semicircle_polygon()
        metrics = compute_cell_metrics(categories, [polygon], target_areas)
        return [polygon], metrics, 0, build_recursive_layout_stats(accepted=True)

    items = [
        {
            "category": category,
            "targetArea": target_area,
            "weight": category["weight"],
        }
        for category, target_area in zip(categories, target_areas, strict=False)
    ]
    items = build_partition_items(categories, target_areas)
    parent_polygon = make_semicircle_polygon()
    polygon_map: dict[str, Polygon] = {}
    stats = build_recursive_layout_stats()
    recursive_binary_partition_layout(parent_polygon, items, polygon_map, 0, stats)
    polygons = [polygon_map[category["categoryId"]] for category in categories]
    metrics = compute_cell_metrics(categories, polygons, target_areas)
    stats["accepted"] = True
    return polygons, metrics, max(0, len(categories) - 1), stats


def build_previous_stable_layout(
    categories: list[dict[str, Any]],
) -> tuple[list[Polygon], list[dict[str, float]], int]:
    polygons, metrics, iteration_count, _ = build_strategy_layout_details(
        categories,
        strategy="v1",
        enforce_constraints=False,
    )
    return polygons, metrics, iteration_count


def build_new_strategy_v2_layout(
    categories: list[dict[str, Any]],
) -> tuple[list[Polygon], list[dict[str, float]], int]:
    polygons, metrics, iteration_count, _ = build_strategy_layout_details(
        categories,
        strategy="v2",
        enforce_constraints=False,
    )
    return polygons, metrics, iteration_count


def build_next_candidate_layout(
    categories: list[dict[str, Any]],
) -> tuple[list[Polygon], list[dict[str, float]], int, dict[str, int | bool]]:
    return build_next_candidate_retry_layout(categories)


def build_hard_constraint_failed_layout(
    categories: list[dict[str, Any]],
) -> tuple[list[Polygon], list[dict[str, float]], int, dict[str, int | bool]]:
    try:
        polygons, metrics, iteration_count, stats = build_strategy_layout_details(
            categories,
            strategy="v1",
            enforce_constraints=True,
            expand_search=False,
            retry_small_leaf=False,
        )
        stats["accepted"] = True
        return polygons, metrics, iteration_count, stats
    except PartitionFailure as error:
        polygons, metrics, iteration_count, _ = build_strategy_layout_details(
            categories,
            strategy="v1",
            enforce_constraints=False,
        )
        return polygons, metrics, iteration_count, {
            "rejected_candidates": int(error.stats.get("rejected_candidates", 0)),
            "accepted": False,
            "failed_leaf_group_count": int(error.stats.get("failed_leaf_group_count", 0)),
            "fallback_used_count": int(error.stats.get("fallback_used_count", 0)),
        }


def build_next_candidate_retry_layout(
    categories: list[dict[str, Any]],
) -> tuple[list[Polygon], list[dict[str, float]], int, dict[str, int | bool]]:
    try:
        polygons, metrics, iteration_count, stats = build_strategy_layout_details(
            categories,
            strategy="v1",
            enforce_constraints=True,
            expand_search=True,
            retry_small_leaf=True,
        )
        stats["accepted"] = True
        return polygons, metrics, iteration_count, stats
    except PartitionFailure as error:
        polygons, metrics, iteration_count, _ = build_strategy_layout_details(
            categories,
            strategy="v1",
            enforce_constraints=False,
            expand_search=False,
            retry_small_leaf=False,
        )
        return polygons, metrics, iteration_count, {
            "rejected_candidates": int(error.stats.get("rejected_candidates", 0)),
            "accepted": False,
            "failed_leaf_group_count": int(error.stats.get("failed_leaf_group_count", 0)),
            "fallback_used_count": int(error.stats.get("fallback_used_count", 0)),
        }


def build_bsp_strategy_layout(
    categories: list[dict[str, Any]],
    strategy: str,
) -> tuple[list[Polygon], list[dict[str, float]], int]:
    target_areas = build_target_areas(categories)
    if len(categories) == 1:
        polygon = make_semicircle_polygon()
        metrics = compute_cell_metrics(categories, [polygon], target_areas)
        return [polygon], metrics, 0

    parent_polygon = make_semicircle_polygon()
    if strategy == "v2":
        items = build_partition_items_v2(categories, target_areas)
    else:
        items = build_partition_items(categories, target_areas)
    polygon_map: dict[str, Polygon] = {}
    partition_items_into_polygon(items, parent_polygon, polygon_map, 0, strategy, None)
    polygons = [polygon_map[category["categoryId"]] for category in categories]
    metrics = compute_cell_metrics(categories, polygons, target_areas)
    return polygons, metrics, max(0, len(categories) - 1)


def build_strategy_layout_details(
    categories: list[dict[str, Any]],
    strategy: str,
    enforce_constraints: bool,
    expand_search: bool = False,
    retry_small_leaf: bool = False,
) -> tuple[list[Polygon], list[dict[str, float]], int, dict[str, int]]:
    target_areas = build_target_areas(categories)
    if len(categories) == 1:
        polygon = make_semicircle_polygon()
        metrics = compute_cell_metrics(categories, [polygon], target_areas)
        return [polygon], metrics, 0, {"rejected_candidates": 0, "failed_leaf_group_count": 0, "fallback_used_count": 0}

    parent_polygon = make_semicircle_polygon()
    if strategy == "v2":
        items = build_partition_items_v2(categories, target_areas)
    else:
        items = build_partition_items(categories, target_areas)
    polygon_map: dict[str, Polygon] = {}
    stats = {"rejected_candidates": 0, "failed_leaf_group_count": 0, "fallback_used_count": 0}
    partition_items_into_polygon(
        items,
        parent_polygon,
        polygon_map,
        0,
        strategy=strategy,
        previous_angle=None,
        enforce_constraints=enforce_constraints,
        stats=stats,
        expand_search=expand_search,
        retry_small_leaf=retry_small_leaf,
    )
    polygons = [polygon_map[category["categoryId"]] for category in categories]
    metrics = compute_cell_metrics(categories, polygons, target_areas)
    return polygons, metrics, max(0, len(categories) - 1), stats


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


def build_irregular_area_partition(
    categories: list[dict[str, Any]],
    parent_polygon: Polygon,
    target_areas: list[float],
) -> tuple[list[Polygon], list[dict[str, float]], int]:
    if len(categories) == 1:
        metrics = compute_cell_metrics(categories, [parent_polygon], target_areas)
        return [parent_polygon], metrics, 0

    seeds = initialize_seed_points(categories, variant=4)
    working_items = [
        {
            "category": category,
            "targetArea": target_area,
            "seed": seed,
        }
        for category, target_area, seed in zip(categories, target_areas, seeds, strict=False)
    ]
    working_items.sort(
        key=lambda item: (
            math.atan2(item["seed"][1], item["seed"][0]),
            math.hypot(item["seed"][0], item["seed"][1]),
            item["category"]["sortOrder"],
            item["category"]["categoryId"],
        )
    )

    polygon_map: dict[str, Polygon] = {}
    partition_items_into_polygon(working_items, parent_polygon, polygon_map, 0)
    polygons = [polygon_map[category["categoryId"]] for category in categories]
    metrics = compute_cell_metrics(categories, polygons, target_areas)
    return polygons, metrics, 0


def build_partition_items(
    categories: list[dict[str, Any]],
    target_areas: list[float],
) -> list[dict[str, Any]]:
    weighted_categories = sorted(
        zip(categories, target_areas, strict=False),
        key=lambda item: (-item[0]["weight"], item[0]["sortOrder"], item[0]["categoryId"]),
    )
    left_lane: list[tuple[dict[str, Any], float]] = []
    right_lane: list[tuple[dict[str, Any], float]] = []
    for index, pair in enumerate(weighted_categories):
        if index % 2 == 0:
            left_lane.append(pair)
        else:
            right_lane.append(pair)

    ordered_pairs = left_lane + list(reversed(right_lane))
    return [
        {
            "category": category,
            "targetArea": target_area,
        }
        for category, target_area in ordered_pairs
    ]


def build_partition_items_v2(
    categories: list[dict[str, Any]],
    target_areas: list[float],
) -> list[dict[str, Any]]:
    weighted_pairs = sorted(
        zip(categories, target_areas, strict=False),
        key=lambda item: (-item[0]["weight"], item[0]["sortOrder"], item[0]["categoryId"]),
    )
    slot_order = build_slot_fill_order(len(weighted_pairs))
    slotted: list[tuple[dict[str, Any], float] | None] = [None] * len(weighted_pairs)
    for pair, slot_index in zip(weighted_pairs, slot_order, strict=False):
        slotted[slot_index] = pair

    return [
        {
            "category": category,
            "targetArea": target_area,
        }
        for pair in slotted
        if pair is not None
        for category, target_area in [pair]
    ]


def build_slot_fill_order(count: int) -> list[int]:
    if count <= 2:
        return list(range(count))

    center_left = (count - 1) // 2
    center_right = count // 2
    order: list[int] = []
    if center_left == center_right:
        order.append(center_left)
    else:
        order.extend([center_left, center_right])

    left = 0
    right = count - 1
    while len(order) < count:
        if left not in order:
            order.append(left)
        if right not in order and len(order) < count:
            order.append(right)
        left += 1
        right -= 1

    return order[:count]


def build_recursive_layout_stats(accepted: bool = False) -> dict[str, int | bool]:
    return {
        "grouping_candidate_count": 0,
        "split_candidate_count": 0,
        "feasible_candidate_count": 0,
        "rejected_candidate_count": 0,
        "rejected_candidates": 0,
        "fallback_used_count": 0,
        "fallback_leaf_sliver_count": 0,
        "recursion_depth_max": 0,
        "accepted": accepted,
    }


def recursive_binary_partition_layout(
    parent_polygon: Polygon,
    items: list[dict[str, Any]],
    polygon_map: dict[str, Polygon],
    depth: int,
    stats: dict[str, int | bool],
    previous_angle: float | None = None,
) -> None:
    stats["recursion_depth_max"] = max(int(stats["recursion_depth_max"]), depth)
    if len(items) == 1:
        polygon_map[items[0]["category"]["categoryId"]] = parent_polygon
        return

    best_candidate = choose_recursive_partition_candidate(parent_polygon, items, stats, hard_constraints=True, previous_angle=previous_angle)
    if best_candidate is None:
        if len(items) <= 3:
            best_candidate = build_small_leaf_group_layout(parent_polygon, items, stats)
        if best_candidate is None:
            best_candidate = choose_recursive_partition_candidate(parent_polygon, items, stats, hard_constraints=False, previous_angle=previous_angle)
            if best_candidate is not None:
                stats["fallback_used_count"] = int(stats["fallback_used_count"]) + 1
        if best_candidate is None:
            raise PartitionFailure("recursive_binary_partition_failed", stats.copy())

    group_a, group_b, child_a, child_b = best_candidate
    left_centroid = polygon_centroid(child_a)
    right_centroid = polygon_centroid(child_b)
    split_angle = math.atan2(right_centroid[1] - left_centroid[1], right_centroid[0] - left_centroid[0])
    recursive_binary_partition_layout(child_a, group_a, polygon_map, depth + 1, stats, split_angle)
    recursive_binary_partition_layout(child_b, group_b, polygon_map, depth + 1, stats, split_angle)


def choose_recursive_partition_candidate(
    parent_polygon: Polygon,
    items: list[dict[str, Any]],
    stats: dict[str, int | bool],
    hard_constraints: bool,
    previous_angle: float | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Polygon, Polygon] | None:
    best_candidate: tuple[list[dict[str, Any]], list[dict[str, Any]], Polygon, Polygon] | None = None
    best_key: tuple[float, float, float, float, float] | None = None

    for group_a, group_b in generate_grouping_candidates(items):
        stats["grouping_candidate_count"] = int(stats["grouping_candidate_count"]) + 1
        for angle, child_a, child_b in generate_split_candidates(parent_polygon, group_a, group_b, stats):
            evaluation = evaluate_partition_candidate(
                parent_polygon,
                child_a,
                child_b,
                group_a,
                group_b,
                hard_constraints=hard_constraints,
            )
            if evaluation is None:
                stats["rejected_candidate_count"] = int(stats["rejected_candidate_count"]) + 1
                continue

            stats["feasible_candidate_count"] = int(stats["feasible_candidate_count"]) + 1
            future_risk = estimate_descendant_partition_risk(
                [(child_a, group_a), (child_b, group_b)],
                "v1",
            )
            local_score = local_partition_score(
                child_a,
                child_b,
                group_a,
                group_b,
                angle,
                previous_angle,
                "v1",
            )
            candidate_key = (
                local_score,
                -evaluation["minimumWidth"],
                future_risk,
                evaluation["descendantRisk"],
                evaluation["narrownessScore"],
                -evaluation["convexityRatio"],
                -evaluation["compactness"],
                -evaluation["labelFitness"],
                evaluation["areaError"],
            )
            if best_key is None or candidate_key < best_key:
                best_key = candidate_key
                best_candidate = (group_a, group_b, child_a, child_b)

    return best_candidate


def generate_grouping_candidates(
    items: list[dict[str, Any]],
) -> list[tuple[list[dict[str, Any]], list[dict[str, Any]]]]:
    candidates: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []
    seen: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()

    def add_candidate(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> None:
        if not left or not right:
            return
        left_ids = tuple(sorted(item["category"]["categoryId"] for item in left))
        right_ids = tuple(sorted(item["category"]["categoryId"] for item in right))
        key = (left_ids, right_ids) if left_ids <= right_ids else (right_ids, left_ids)
        if key in seen:
            return
        seen.add(key)
        candidates.append((left, right))

    current_order_split = find_balanced_split_index(items)
    add_candidate(items[:current_order_split], items[current_order_split:])

    ordered = sorted(
        items,
        key=lambda item: (item["category"]["sortOrder"], item["category"]["categoryId"]),
    )
    descending = sorted(
        items,
        key=lambda item: (-item["targetArea"], item["category"]["sortOrder"], item["category"]["categoryId"]),
    )
    ascending = list(reversed(descending))

    for source in (ordered, descending, ascending):
        split_index = find_balanced_split_index(source)
        add_candidate(source[:split_index], source[split_index:])

    alternating: list[dict[str, Any]] = []
    left_index = 0
    right_index = len(descending) - 1
    while left_index <= right_index:
        alternating.append(descending[left_index])
        left_index += 1
        if left_index <= right_index:
            alternating.append(descending[right_index])
            right_index -= 1
    split_index = max(1, min(len(alternating) - 1, len(alternating) // 2))
    add_candidate(alternating[:split_index], alternating[split_index:])

    bucket_a: list[dict[str, Any]] = []
    bucket_b: list[dict[str, Any]] = []
    weight_a = 0.0
    weight_b = 0.0
    for item in descending:
        if (weight_a, len(bucket_a)) <= (weight_b, len(bucket_b)):
            bucket_a.append(item)
            weight_a += item["targetArea"]
        else:
            bucket_b.append(item)
            weight_b += item["targetArea"]
    add_candidate(bucket_a, bucket_b)

    interleaved = ordered[::2] + ordered[1::2]
    split_index = find_balanced_split_index(interleaved)
    add_candidate(interleaved[:split_index], interleaved[split_index:])

    variance_balanced_a: list[dict[str, Any]] = []
    variance_balanced_b: list[dict[str, Any]] = []
    area_a = 0.0
    area_b = 0.0
    count_a = 0
    count_b = 0
    for item in descending:
        future_a = (area_a + item["targetArea"]) / max(count_a + 1, 1)
        future_b = (area_b + item["targetArea"]) / max(count_b + 1, 1)
        score_a = abs(future_a - ((area_b / max(count_b, 1)) if count_b else future_a))
        score_b = abs(future_b - ((area_a / max(count_a, 1)) if count_a else future_b))
        if score_a <= score_b:
            variance_balanced_a.append(item)
            area_a += item["targetArea"]
            count_a += 1
        else:
            variance_balanced_b.append(item)
            area_b += item["targetArea"]
            count_b += 1
    add_candidate(variance_balanced_a, variance_balanced_b)

    small_heavy_mix_a: list[dict[str, Any]] = []
    small_heavy_mix_b: list[dict[str, Any]] = []
    for index, item in enumerate(descending):
        target_bucket = small_heavy_mix_a if index % 3 in (0, 2) else small_heavy_mix_b
        target_bucket.append(item)
    add_candidate(small_heavy_mix_a, small_heavy_mix_b)

    edge_balanced_a: list[dict[str, Any]] = []
    edge_balanced_b: list[dict[str, Any]] = []
    for index, item in enumerate(ordered):
        if index % 4 in (0, 3):
            edge_balanced_a.append(item)
        else:
            edge_balanced_b.append(item)
    add_candidate(edge_balanced_a, edge_balanced_b)

    compact_mix_a: list[dict[str, Any]] = []
    compact_mix_b: list[dict[str, Any]] = []
    for index, item in enumerate(alternating):
        if index % 2 == 0:
            compact_mix_a.append(item)
        else:
            compact_mix_b.append(item)
    add_candidate(compact_mix_a, compact_mix_b)

    candidates.sort(key=lambda pair: grouping_candidate_score(pair[0], pair[1]))
    return candidates[:14]


def grouping_candidate_score(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
) -> tuple[float, float, float, float, float]:
    total_left = sum(item["targetArea"] for item in left)
    total_right = sum(item["targetArea"] for item in right)
    area_gap = abs(total_left - total_right) / max(total_left + total_right, EPSILON)
    count_gap = abs(len(left) - len(right))
    left_small = sum(1 for item in left if item["targetArea"] <= 220.0)
    right_small = sum(1 for item in right if item["targetArea"] <= 220.0)
    small_gap = abs(left_small - right_small)
    left_mean = total_left / max(len(left), 1)
    right_mean = total_right / max(len(right), 1)
    variance_gap = abs(left_mean - right_mean) / max(max(left_mean, right_mean), EPSILON)
    singleton_penalty = float((len(left) == 1) != (len(right) == 1))
    return (
        area_gap,
        count_gap * 0.12,
        small_gap * 0.18,
        variance_gap * 0.4,
        singleton_penalty,
    )


def generate_split_candidates(
    parent_polygon: Polygon,
    group_a: list[dict[str, Any]],
    group_b: list[dict[str, Any]],
    stats: dict[str, int | bool],
) -> list[tuple[float, Polygon, Polygon]]:
    total_area = sum(item["targetArea"] for item in group_a + group_b) or 1.0
    target_ratio = sum(item["targetArea"] for item in group_a) / total_area
    width, height = polygon_bbox_dimensions(parent_polygon)
    base_axis = 0.0 if width >= height else math.pi / 2
    candidate_angles = [
        0.0,
        math.pi / 2,
        math.pi / 6,
        -math.pi / 6,
        math.pi / 4,
        -math.pi / 4,
        math.pi / 3,
        -math.pi / 3,
        base_axis,
        base_axis + (math.pi / 8),
        base_axis - (math.pi / 8),
    ]

    candidates: list[tuple[float, Polygon, Polygon]] = []
    seen_angles: set[float] = set()
    for angle in candidate_angles:
        normalized = round(normalize_angle(angle), 6)
        if normalized in seen_angles:
            continue
        seen_angles.add(normalized)
        stats["split_candidate_count"] = int(stats["split_candidate_count"]) + 1
        partition = partition_polygon_by_line_and_ratio(parent_polygon, angle, target_ratio)
        if partition is None:
            continue
        child_a, child_b = partition
        candidates.append((angle, child_a, child_b))

    return candidates


def partition_polygon_by_line_and_ratio(
    parent_polygon: Polygon,
    angle: float,
    target_ratio: float,
) -> tuple[Polygon, Polygon] | None:
    normal = (math.cos(angle), math.sin(angle))
    try:
        child_a, child_b = split_polygon_by_area(parent_polygon, normal, target_ratio)
    except ValueError:
        return None
    if len(child_a) < 3 or len(child_b) < 3:
        return None
    return child_a, child_b


def evaluate_partition_candidate(
    parent_polygon: Polygon,
    child_a: Polygon,
    child_b: Polygon,
    group_a: list[dict[str, Any]],
    group_b: list[dict[str, Any]],
    hard_constraints: bool = True,
) -> dict[str, float] | None:
    del parent_polygon
    polygons = [child_a, child_b]
    groups = [group_a, group_b]
    compactness_values = [polygon_compactness(polygon) for polygon in polygons]
    aspect_values = [polygon_aspect_ratio(polygon) for polygon in polygons]
    minimum_widths = [polygon_true_minimum_width(polygon) for polygon in polygons]
    edge_values = [edge_crowding_value(polygon) for polygon in polygons]
    label_fitness_values = [label_fitness_value(polygon) for polygon in polygons]
    narrowness_values = [polygon_narrowness_score(polygon) for polygon in polygons]
    convexity_values = [polygon_convexity_ratio(polygon) for polygon in polygons]
    descendant_risk = compute_descendant_risk_score(polygons, groups)

    for polygon, group, compactness, aspect_ratio, minimum_width, narrowness, convexity in zip(
        polygons,
        groups,
        compactness_values,
        aspect_values,
        minimum_widths,
        narrowness_values,
        convexity_values,
        strict=False,
    ):
        if hard_constraints and unique_vertex_count(polygon) <= 3 and len(group) <= 1:
            return None
        if hard_constraints:
            if minimum_width < required_width_for_recursive_group(group):
                return None
            if aspect_ratio > HARD_MAX_ASPECT_RATIO:
                return None
            if compactness < HARD_MIN_COMPACTNESS:
                return None
            if polygon_area(polygon) / max(polygon_perimeter(polygon), EPSILON) < HARD_MIN_AREA_PER_PERIMETER:
                return None
            if narrowness > 4.8:
                return None
            if convexity < 0.58:
                return None

    target_ratio = sum(item["targetArea"] for item in group_a) / max(
        sum(item["targetArea"] for item in group_a + group_b),
        EPSILON,
    )
    actual_ratio = polygon_area(child_a) / max(polygon_area(child_a) + polygon_area(child_b), EPSILON)
    return {
        "areaError": abs(actual_ratio - target_ratio),
        "compactness": mean(compactness_values),
        "aspectRatio": max(aspect_values),
        "minimumWidth": min(minimum_widths),
        "labelFitness": mean(label_fitness_values),
        "edgeCrowding": mean(edge_values),
        "descendantRisk": descendant_risk,
        "narrownessScore": max(narrowness_values),
        "convexityRatio": mean(convexity_values),
    }


def build_small_leaf_group_layout(
    parent_polygon: Polygon,
    items: list[dict[str, Any]],
    stats: dict[str, int | bool],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Polygon, Polygon] | None:
    if len(items) not in (2, 3):
        return None

    if len(items) == 2:
        candidate_groups = [(items[:1], items[1:])]
    else:
        candidate_groups = [
            (items[:1], items[1:]),
            (items[:2], items[2:]),
        ]

    best_candidate: tuple[list[dict[str, Any]], list[dict[str, Any]], Polygon, Polygon] | None = None
    best_key: tuple[float, float, float, float] | None = None
    relaxed_candidate: tuple[list[dict[str, Any]], list[dict[str, Any]], Polygon, Polygon] | None = None
    relaxed_key: tuple[float, float, float, float] | None = None
    for group_a, group_b in candidate_groups:
        for angle in [index * (math.pi / 24) for index in range(24)]:
            stats["split_candidate_count"] = int(stats["split_candidate_count"]) + 1
            partition = partition_polygon_by_line_and_ratio(
                parent_polygon,
                angle,
                sum(item["targetArea"] for item in group_a) / max(sum(item["targetArea"] for item in items), EPSILON),
            )
            if partition is None:
                continue
            child_a, child_b = partition
            evaluation = evaluate_partition_candidate(parent_polygon, child_a, child_b, group_a, group_b, hard_constraints=True)
            if evaluation is None:
                stats["rejected_candidate_count"] = int(stats["rejected_candidate_count"]) + 1
                relaxed_evaluation = evaluate_partition_candidate(
                    parent_polygon,
                    child_a,
                    child_b,
                    group_a,
                    group_b,
                    hard_constraints=False,
                )
                if relaxed_evaluation is not None:
                    relaxed_score = (
                        -relaxed_evaluation["minimumWidth"],
                        relaxed_evaluation["descendantRisk"],
                        relaxed_evaluation["narrownessScore"],
                        -relaxed_evaluation["convexityRatio"],
                        -relaxed_evaluation["compactness"],
                        -relaxed_evaluation["labelFitness"],
                        relaxed_evaluation["areaError"],
                    )
                    if relaxed_key is None or relaxed_score < relaxed_key:
                        relaxed_key = relaxed_score
                        relaxed_candidate = (group_a, group_b, child_a, child_b)
                continue
            stats["feasible_candidate_count"] = int(stats["feasible_candidate_count"]) + 1
            future_risk = estimate_descendant_partition_risk(
                [(child_a, group_a), (child_b, group_b)],
                "v1",
            )
            candidate_key = (
                -evaluation["minimumWidth"],
                future_risk,
                evaluation["descendantRisk"],
                evaluation["narrownessScore"],
                -evaluation["convexityRatio"],
                -evaluation["compactness"],
                -evaluation["labelFitness"],
                evaluation["areaError"],
            )
            if best_key is None or candidate_key < best_key:
                best_key = candidate_key
                best_candidate = (group_a, group_b, child_a, child_b)
    if best_candidate is not None:
        return best_candidate
    if relaxed_candidate is not None:
        stats["fallback_used_count"] = int(stats["fallback_used_count"]) + 1
        stats["fallback_leaf_sliver_count"] = int(stats["fallback_leaf_sliver_count"]) + sum(
            1 for polygon in (relaxed_candidate[2], relaxed_candidate[3]) if polygon_is_true_sliver(polygon)
        )
        return relaxed_candidate
    return None


def required_width_for_recursive_group(items: list[dict[str, Any]]) -> float:
    if len(items) <= 1:
        return HARD_MIN_WIDTH
    return min(HARD_MIN_WIDTH, 9.2 + min(len(items), 4) * 0.65)


def label_fitness_value(polygon: Polygon) -> float:
    width, height = polygon_bbox_dimensions(polygon)
    area = polygon_area(polygon)
    width_score = min(width / max(MIN_LABEL_WIDTH, EPSILON), 2.0)
    height_score = min(height / max(MIN_LABEL_HEIGHT, EPSILON), 2.0)
    area_score = min(area / max(MIN_LABEL_AREA, EPSILON), 2.0)
    return (width_score + height_score + area_score) / 3


def compute_descendant_risk_score(
    polygons: list[Polygon],
    groups: list[list[dict[str, Any]]],
) -> float:
    risks: list[float] = []
    for polygon, group in zip(polygons, groups, strict=False):
        if len(group) <= 1:
            risks.append(0.0)
            continue
        total_area = sum(item["targetArea"] for item in group)
        small_count = sum(1 for item in group if item["targetArea"] <= 220.0)
        variance = mean(abs(item["targetArea"] - (total_area / len(group))) for item in group)
        width_pressure = max(0.0, (required_width_for_recursive_group(group) + (len(group) - 1) * 1.4) - polygon_true_minimum_width(polygon))
        edge_pressure = edge_crowding_value(polygon)
        shape_pressure = max(0.0, polygon_narrowness_score(polygon) - 3.1)
        risks.append(
            width_pressure
            + (small_count * 0.35)
            + (variance / max(total_area, EPSILON))
            + edge_pressure
            + shape_pressure * 0.4
        )
    return mean(risks) if risks else 0.0


def estimate_descendant_partition_risk(
    polygon_groups: list[tuple[Polygon, list[dict[str, Any]]]],
    strategy: str,
) -> float:
    risks: list[float] = []
    for polygon, items in polygon_groups:
        if len(items) <= 1:
            risks.append(0.0)
            continue

        width_floor = required_width_for_items(items)
        if len(items) > 4:
            total_area = sum(item["targetArea"] for item in items)
            small_count = sum(1 for item in items if item["targetArea"] <= 220.0)
            width_pressure = max(0.0, (width_floor + len(items) * 0.8) - polygon_true_minimum_width(polygon))
            shape_pressure = max(0.0, polygon_narrowness_score(polygon) - 3.1)
            edge_pressure = edge_crowding_value(polygon)
            risks.append(
                width_pressure
                + edge_pressure
                + shape_pressure * 0.35
                + (small_count / max(len(items), 1)) * 0.75
                + (len(items) / max(total_area, EPSILON)) * 40.0
            )
            continue

        candidate_indices = build_split_index_candidates(items, exhaustive=False)[:2]
        best_local_risk: float | None = None
        feasible_count = 0

        for split_index in candidate_indices:
            left_items = items[:split_index]
            right_items = items[split_index:]
            left_ratio = sum(item["targetArea"] for item in left_items) / max(
                sum(item["targetArea"] for item in items),
                EPSILON,
            )
            for _, child_a, child_b in generate_preview_split_candidates(
                polygon,
                left_items,
                right_items,
                left_ratio,
                strategy,
            ):
                if not partition_respects_constraints(child_a, child_b, left_items, right_items):
                    continue
                feasible_count += 1
                widths = [polygon_true_minimum_width(child_a), polygon_true_minimum_width(child_b)]
                narrowness = [polygon_narrowness_score(child_a), polygon_narrowness_score(child_b)]
                edge_values = [edge_crowding_value(child_a), edge_crowding_value(child_b)]
                local_risk = (
                    sum(max(0.0, width_floor - width) for width in widths) * 1.2
                    + max(narrowness) * 0.45
                    + max(edge_values) * 0.7
                )
                if best_local_risk is None or local_risk < best_local_risk:
                    best_local_risk = local_risk

        risks.append((4.0 + len(items) * 0.8) if feasible_count == 0 else (best_local_risk or 0.0))

    return mean(risks) if risks else 0.0


def generate_preview_split_candidates(
    polygon: Polygon,
    left_items: list[dict[str, Any]],
    right_items: list[dict[str, Any]],
    left_ratio: float,
    strategy: str,
) -> list[tuple[float, Polygon, Polygon]]:
    base_normal = choose_partition_normal(polygon, left_items, right_items, 0)
    base_angle = math.atan2(base_normal[1], base_normal[0])
    offsets = [-0.45, 0.0, 0.45, math.pi / 2]
    if strategy == "v2":
        offsets = [-0.58, -0.22, 0.0, 0.22, 0.58, math.pi / 2]

    candidates: list[tuple[float, Polygon, Polygon]] = []
    seen: set[float] = set()
    for offset in offsets:
        angle = base_angle + offset
        normalized = round(normalize_angle(angle), 6)
        if normalized in seen:
            continue
        seen.add(normalized)
        normal = (math.cos(angle), math.sin(angle))
        try:
            left_polygon, right_polygon = split_polygon_by_area(polygon, normal, left_ratio)
        except ValueError:
            continue
        candidates.append((angle, left_polygon, right_polygon))
    return candidates


def build_bsp_treemap_rects(
    items: list[dict[str, Any]],
    rect: Rect,
    rects: dict[str, Rect],
    depth: int,
) -> None:
    if len(items) == 1:
        rects[items[0]["category"]["categoryId"]] = rect
        return

    split_index = find_balanced_split_index(items)
    left_items = items[:split_index]
    right_items = items[split_index:]
    total_area = sum(item["targetArea"] for item in items) or 1.0
    left_ratio = sum(item["targetArea"] for item in left_items) / total_area

    x0, y0, x1, y1 = rect
    width = x1 - x0
    height = y1 - y0

    split_vertical = width >= height
    if split_vertical:
        split = x0 + (width * left_ratio)
        left_rect = (x0, y0, split, y1)
        right_rect = (split, y0, x1, y1)
    else:
        split = y0 + (height * left_ratio)
        left_rect = (x0, y0, x1, split)
        right_rect = (x0, split, x1, y1)

    if min(left_rect[2] - left_rect[0], left_rect[3] - left_rect[1]) < 0.07 or min(
        right_rect[2] - right_rect[0],
        right_rect[3] - right_rect[1],
    ) < 0.07:
        split_vertical = not split_vertical
        if split_vertical:
            split = x0 + (width * left_ratio)
            left_rect = (x0, y0, split, y1)
            right_rect = (split, y0, x1, y1)
        else:
            split = y0 + (height * left_ratio)
            left_rect = (x0, y0, x1, split)
            right_rect = (x0, split, x1, y1)

    build_bsp_treemap_rects(left_items, left_rect, rects, depth + 1)
    build_bsp_treemap_rects(right_items, right_rect, rects, depth + 1)


def rectangle_to_semicircle_polygon(rect: Rect, sort_order: int) -> Polygon:
    s0, t0, s1, t1 = rect
    horizontal_samples = max(4, int((s1 - s0) * 22))
    left_edge = [map_param_point_to_semicircle(s0, t) for t in interpolate_values(t0, t1, 2)]
    top_edge = [
        map_param_point_to_semicircle(s, t1)
        for s in interpolate_values(s0, s1, horizontal_samples)
    ]
    right_edge = [
        map_param_point_to_semicircle(s1, t)
        for t in interpolate_values(t1, t0, 2)
    ]
    bottom_edge = [
        map_param_point_to_semicircle(s, t0)
        for s in interpolate_values(s1, s0, horizontal_samples)
    ]

    polygon = dedupe_polygon(left_edge[:-1] + top_edge[:-1] + right_edge[:-1] + bottom_edge[:-1])
    return soften_polygon_edges(polygon, sort_order)


def map_param_point_to_semicircle(s: float, t: float) -> Point:
    x = invert_semicircle_area_fraction(min(max(s, 0.0), 1.0))
    height = math.sqrt(max((SEMICIRCLE_RADIUS * SEMICIRCLE_RADIUS) - (x * x), 0.0))
    y = min(max(t, 0.0), 1.0) * height
    return round(x, 6), round(y, 6)


def interpolate_values(start: float, end: float, steps: int) -> list[float]:
    if steps <= 1:
        return [start, end]
    return [start + ((end - start) * (index / steps)) for index in range(steps + 1)]


def invert_semicircle_area_fraction(fraction: float) -> float:
    target = min(max(fraction, 0.0), 1.0) * (0.5 * math.pi * SEMICIRCLE_RADIUS * SEMICIRCLE_RADIUS)
    low = -SEMICIRCLE_RADIUS
    high = SEMICIRCLE_RADIUS

    for _ in range(60):
        mid = (low + high) / 2
        if semicircle_area_to_x(mid) < target:
            low = mid
        else:
            high = mid

    return (low + high) / 2


def semicircle_area_to_x(x: float) -> float:
    radius = SEMICIRCLE_RADIUS
    x = min(max(x, -radius), radius)
    integral = 0.5 * ((x * math.sqrt(max(radius * radius - x * x, 0.0))) + (radius * radius * math.asin(x / radius)))
    return integral + ((math.pi * radius * radius) / 4)


def soften_polygon_edges(polygon: Polygon, sort_order: int) -> Polygon:
    if len(polygon) < 3:
        return polygon

    softened: Polygon = []
    for index, current in enumerate(polygon):
        previous = polygon[index - 1]
        following = polygon[(index + 1) % len(polygon)]
        if (
            abs(current[1] - previous[1]) < 0.0001
            and abs(current[1] - following[1]) < 0.0001
            and current[1] > 0
        ):
            offset = (((sort_order + index) % 5) - 2) * 0.45
            softened.append((current[0], round(max(0.0, current[1] + offset), 6)))
        else:
            softened.append(current)

    return dedupe_polygon(softened)


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
        perimeter = polygon_perimeter(polygon)
        bbox_width, bbox_height = polygon_bbox_dimensions(polygon)
        compactness = (4 * math.pi * actual_area) / max(perimeter * perimeter, EPSILON)
        aspect_ratio = max(bbox_width, bbox_height) / max(min(bbox_width, bbox_height), EPSILON)
        minimum_thickness = polygon_true_minimum_width(polygon)
        edge_crowding = edge_crowding_value(polygon)
        triangle_penalty = 1.0 if unique_vertex_count(polygon) <= 3 else 0.0
        narrowness_score = polygon_narrowness_score(polygon)
        convexity_ratio = polygon_convexity_ratio(polygon)
        quality_score = compute_quality_score(
            relative_error,
            compactness,
            aspect_ratio,
            minimum_thickness,
            edge_crowding,
            triangle_penalty,
        )
        metrics.append(
            {
                "weight": category["weight"],
                "targetArea": round(target_area, 6),
                "actualArea": round(actual_area, 6),
                "areaError": round(area_error, 6),
                "relativeError": round(relative_error, 6),
                "compactness": round(compactness, 6),
                "bboxWidth": round(bbox_width, 6),
                "bboxHeight": round(bbox_height, 6),
                "aspectRatio": round(aspect_ratio, 6),
                "minimumWidth": round(minimum_thickness, 6),
                "qualityScore": round(quality_score, 6),
                "edgeCrowding": round(edge_crowding, 6),
                "trianglePenalty": triangle_penalty,
                "narrownessScore": round(narrowness_score, 6),
                "convexityRatio": round(convexity_ratio, 6),
                "centroidX": round(centroid_x, 6),
                "centroidY": round(centroid_y, 6),
            }
        )
    return metrics


def summarize_strategy_metrics(
    categories: list[dict[str, Any]],
    polygons: list[Polygon],
    metrics: list[dict[str, float]],
) -> dict[str, float]:
    minimum_widths = [metric["minimumWidth"] for metric in metrics]
    return {
        "mean_relative_error": round(mean(metric["relativeError"] for metric in metrics), 6) if metrics else 0.0,
        "max_relative_error": round(max(metric["relativeError"] for metric in metrics), 6) if metrics else 0.0,
        "mean_compactness": round(mean(metric["compactness"] for metric in metrics), 6) if metrics else 0.0,
        "minimum_width_min": round(min(minimum_widths), 6) if minimum_widths else 0.0,
        "sliver_cell_count": float(count_sliver_cells(metrics)),
        "true_sliver_cell_count": float(sum(1 for polygon in polygons if polygon_is_true_sliver(polygon))),
        "labelable_cell_count": float(count_labelable_cells(metrics)),
        "label_overlap_count": float(compute_label_overlap_count(categories, metrics)),
        "small_cell_center_clustering_score": round(compute_small_cell_center_clustering_score(metrics), 6),
        "edge_crowding_score": round(mean(metric["edgeCrowding"] for metric in metrics), 6) if metrics else 0.0,
        "dominant_angle_repetition_score": round(compute_dominant_angle_repetition_score(polygons), 6),
        "center_shared_polygon_count": float(count_center_shared_polygons(polygons)),
        "narrowness_score_mean": round(mean(metric["narrownessScore"] for metric in metrics), 6) if metrics else 0.0,
        "narrowness_score_max": round(max(metric["narrownessScore"] for metric in metrics), 6) if metrics else 0.0,
        "convexity_ratio_mean": round(mean(metric["convexityRatio"] for metric in metrics), 6) if metrics else 0.0,
        "descendant_risk_score": round(compute_descendant_risk_from_metrics(metrics), 6),
    }


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
    layout_strategy: str = "recursive_binary_partition",
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
                metrics["compactness"],
                metrics["bboxWidth"],
                metrics["bboxHeight"],
                metrics["aspectRatio"],
                metrics["qualityScore"],
                path,
                round(x, 6),
                round(y, 6),
                part_index,
                metrics["centroidX"],
                metrics["centroidY"],
                iteration_count,
                metrics["minimumWidth"],
                layout_strategy,
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

    area_accurate_irregular = [
        candidate
        for candidate in candidates
        if max(metric["relativeError"] for metric in candidate[1]) <= AREA_PARTITION_MAX_ERROR
        and count_center_shared_polygons(candidate[0]) <= 2
        and count_low_quality_cells(candidate[1]) <= max(1, len(candidate[1]) // 6)
        and count_triangle_cells(candidate[0]) <= max(2, len(candidate[0]) // 5)
    ]
    if area_accurate_irregular:
        return min(area_accurate_irregular, key=lambda candidate: candidate_score(candidate[0], candidate[1]))

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


def split_polygon_by_area(
    polygon: Polygon,
    normal: Point,
    target_ratio: float,
) -> tuple[Polygon, Polygon]:
    projections = [(normal[0] * point[0]) + (normal[1] * point[1]) for point in polygon]
    low = min(projections) - 10.0
    high = max(projections) + 10.0
    parent_area = polygon_area(polygon)
    target_area = parent_area * min(max(target_ratio, 0.0), 1.0)
    best_left: Polygon = polygon[:]
    best_right: Polygon = []
    best_error = float("inf")

    for _ in range(60):
        limit = (low + high) / 2
        left = clip_polygon(polygon, normal[0], normal[1], limit)
        right = clip_polygon(polygon, -normal[0], -normal[1], -limit)
        if len(left) < 3 or len(right) < 3:
            break

        left_area = polygon_area(left)
        error = abs(left_area - target_area)
        if error < best_error:
            best_left = left
            best_right = right
            best_error = error

        if left_area < target_area:
            low = limit
        else:
            high = limit

    if len(best_left) < 3 or len(best_right) < 3:
        raise ValueError("area_partition_failed")

    return best_left, best_right


def partition_items_into_polygon(
    items: list[dict[str, Any]],
    polygon: Polygon,
    polygon_map: dict[str, Polygon],
    depth: int,
    strategy: str = "v1",
    previous_angle: float | None = None,
    enforce_constraints: bool = False,
    stats: dict[str, int] | None = None,
    expand_search: bool = False,
    retry_small_leaf: bool = False,
) -> None:
    if len(items) == 1:
        polygon_map[items[0]["category"]["categoryId"]] = polygon
        return

    left_items, right_items, left_polygon, right_polygon = choose_best_grouped_partition(
        items,
        polygon,
        depth,
        strategy,
        previous_angle,
        enforce_constraints,
        stats,
        expand_search,
        retry_small_leaf,
    )
    left_centroid = polygon_centroid(left_polygon)
    right_centroid = polygon_centroid(right_polygon)
    split_angle = math.atan2(right_centroid[1] - left_centroid[1], right_centroid[0] - left_centroid[0])

    partition_items_into_polygon(
        left_items,
        left_polygon,
        polygon_map,
        depth + 1,
        strategy,
        split_angle,
        enforce_constraints,
        stats,
        expand_search,
        retry_small_leaf,
    )
    partition_items_into_polygon(
        right_items,
        right_polygon,
        polygon_map,
        depth + 1,
        strategy,
        split_angle,
        enforce_constraints,
        stats,
        expand_search,
        retry_small_leaf,
    )


def choose_best_grouped_partition(
    items: list[dict[str, Any]],
    polygon: Polygon,
    depth: int,
    strategy: str,
    previous_angle: float | None,
    enforce_constraints: bool,
    stats: dict[str, int] | None,
    expand_search: bool,
    retry_small_leaf: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Polygon, Polygon]:
    candidate_indices = build_split_index_candidates(items, exhaustive=expand_search)
    best_choice: tuple[list[dict[str, Any]], list[dict[str, Any]], Polygon, Polygon, float] | None = None

    for split_index in candidate_indices:
        left_items = items[:split_index]
        right_items = items[split_index:]
        left_ratio = sum(item["targetArea"] for item in left_items) / max(
            sum(item["targetArea"] for item in items),
            EPSILON,
        )
        try:
            left_polygon, right_polygon = choose_best_partition_split(
                polygon,
                left_items,
                right_items,
                left_ratio,
                depth,
                strategy,
                previous_angle,
                enforce_constraints,
                stats,
                expand_search,
            )
        except ValueError:
            continue

        score = local_partition_score(
            left_polygon,
            right_polygon,
            left_items,
            right_items,
            0.0,
            previous_angle,
            strategy,
        )
        if best_choice is None or score < best_choice[4]:
            best_choice = (left_items, right_items, left_polygon, right_polygon, score)

    if best_choice is None:
        if retry_small_leaf and len(items) <= 3:
            retry_choice = split_small_leaf_group(
                items,
                polygon,
                depth,
                strategy,
                previous_angle,
                enforce_constraints,
                stats,
                expand_search,
            )
            if retry_choice is not None:
                if stats is not None:
                    stats["fallback_used_count"] = stats.get("fallback_used_count", 0) + 1
                return retry_choice
            if stats is not None:
                stats["failed_leaf_group_count"] = stats.get("failed_leaf_group_count", 0) + 1
        raise PartitionFailure("partition_split_failed", stats.copy() if stats is not None else None)

    return best_choice[0], best_choice[1], best_choice[2], best_choice[3]


def find_balanced_split_index(items: list[dict[str, Any]]) -> int:
    total_area = sum(item["targetArea"] for item in items)
    running_area = 0.0
    best_index = 1
    best_gap = float("inf")

    for index in range(1, len(items)):
        running_area += items[index - 1]["targetArea"]
        gap = abs((total_area / 2) - running_area)
        if gap < best_gap:
            best_gap = gap
            best_index = index

    return best_index


def build_split_index_candidates(items: list[dict[str, Any]], exhaustive: bool = False) -> list[int]:
    balanced_index = find_balanced_split_index(items)
    candidates = [balanced_index]
    deltas = [-1, 1, -2, 2]
    if exhaustive:
        for delta in range(3, len(items)):
            deltas.extend((-delta, delta))
    for delta in deltas:
        candidate = balanced_index + delta
        if 1 <= candidate < len(items) and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def choose_partition_normal(
    polygon: Polygon,
    left_items: list[dict[str, Any]],
    right_items: list[dict[str, Any]],
    depth: int,
) -> Point:
    width, height = polygon_bbox_dimensions(polygon)
    left_total = sum(item["targetArea"] for item in left_items)
    right_total = sum(item["targetArea"] for item in right_items)
    balance_bias = ((left_total - right_total) / max(left_total + right_total, EPSILON)) * 0.08

    if width >= height:
        base_angle = 0.0
        if depth % 3 == 1:
            base_angle = math.radians(24)
        elif depth % 3 == 2:
            base_angle = math.radians(-24)
    else:
        base_angle = math.pi / 2
        if depth % 3 == 1:
            base_angle += math.radians(20)
        elif depth % 3 == 2:
            base_angle += math.radians(-20)

    base_angle += balance_bias
    return (math.cos(base_angle), math.sin(base_angle))


def choose_best_partition_split(
    polygon: Polygon,
    left_items: list[dict[str, Any]],
    right_items: list[dict[str, Any]],
    left_ratio: float,
    depth: int,
    strategy: str,
    previous_angle: float | None,
    enforce_constraints: bool,
    stats: dict[str, int] | None,
    expand_search: bool,
) -> tuple[Polygon, Polygon]:
    base_normal = choose_partition_normal(polygon, left_items, right_items, depth)
    base_angle = math.atan2(base_normal[1], base_normal[0])
    best_pair: tuple[Polygon, Polygon] | None = None
    best_score = float("inf")

    if strategy == "v2":
        candidate_offsets = list(LOCAL_SPLIT_ANGLE_OFFSETS_V2)
    else:
        candidate_offsets = list(LOCAL_SPLIT_ANGLE_OFFSETS)
        candidate_offsets.extend([math.pi / 2, -math.pi / 2])
    if enforce_constraints:
        for offset in LOCAL_SPLIT_ANGLE_OFFSETS_V2:
            if offset not in candidate_offsets:
                candidate_offsets.append(offset)
    if expand_search:
        dense_offsets = [
            -1.4,
            -1.1,
            -0.9,
            -0.7,
            -0.5,
            -0.35,
            -0.18,
            0.0,
            0.18,
            0.35,
            0.5,
            0.7,
            0.9,
            1.1,
            1.4,
        ]
        for offset in dense_offsets:
            if offset not in candidate_offsets:
                candidate_offsets.append(offset)

    for offset in candidate_offsets:
        angle = base_angle + offset
        normal = (math.cos(angle), math.sin(angle))
        try:
            left_polygon, right_polygon = split_polygon_by_area(polygon, normal, left_ratio)
        except ValueError:
            continue

        if enforce_constraints and not partition_respects_constraints(
            left_polygon,
            right_polygon,
            left_items,
            right_items,
        ):
            if stats is not None:
                stats["rejected_candidates"] = stats.get("rejected_candidates", 0) + 1
            continue

        score = local_partition_score(
            left_polygon,
            right_polygon,
            left_items,
            right_items,
            angle,
            previous_angle,
            strategy,
        )
        if score < best_score:
            best_pair = (left_polygon, right_polygon)
            best_score = score

    if best_pair is None:
        raise ValueError("partition_split_failed")

    return best_pair


def split_small_leaf_group(
    items: list[dict[str, Any]],
    polygon: Polygon,
    depth: int,
    strategy: str,
    previous_angle: float | None,
    enforce_constraints: bool,
    stats: dict[str, int] | None,
    expand_search: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Polygon, Polygon] | None:
    best_choice: tuple[list[dict[str, Any]], list[dict[str, Any]], Polygon, Polygon, float] | None = None
    candidate_indices = build_split_index_candidates(items, exhaustive=True)
    total_area = sum(item["targetArea"] for item in items) or 1.0
    base_angles = [index * (math.pi / 18) for index in range(18)]
    if expand_search:
        base_angles = [index * (math.pi / 24) for index in range(24)]

    for split_index in candidate_indices:
        left_items = items[:split_index]
        right_items = items[split_index:]
        left_ratio = sum(item["targetArea"] for item in left_items) / total_area

        for angle in base_angles:
            normal = (math.cos(angle), math.sin(angle))
            try:
                left_polygon, right_polygon = split_polygon_by_area(polygon, normal, left_ratio)
            except ValueError:
                continue

            if enforce_constraints and not partition_respects_constraints(
                left_polygon,
                right_polygon,
                left_items,
                right_items,
            ):
                if stats is not None:
                    stats["rejected_candidates"] = stats.get("rejected_candidates", 0) + 1
                continue

            score = local_partition_score(
                left_polygon,
                right_polygon,
                left_items,
                right_items,
                angle,
                previous_angle,
                strategy,
            )
            if best_choice is None or score < best_choice[4]:
                best_choice = (left_items, right_items, left_polygon, right_polygon, score)

    if best_choice is None:
        return None

    return best_choice[0], best_choice[1], best_choice[2], best_choice[3]


def local_partition_score(
    left_polygon: Polygon,
    right_polygon: Polygon,
    left_items: list[dict[str, Any]],
    right_items: list[dict[str, Any]],
    candidate_angle: float,
    previous_angle: float | None,
    strategy: str,
) -> float:
    polygons = [left_polygon, right_polygon]
    child_items = [left_items, right_items]
    triangle_penalty = sum(1 for polygon in polygons if unique_vertex_count(polygon) <= 3) * 1.6
    compactness_penalty = sum(max(0.0, 0.16 - polygon_compactness(polygon)) for polygon in polygons) * 3.4
    aspect_penalty = sum(max(0.0, polygon_aspect_ratio(polygon) - 4.5) for polygon in polygons) * 0.34
    thickness_penalty = sum(max(0.0, 11.8 - polygon_true_minimum_width(polygon)) for polygon in polygons) * 0.55
    narrowness_penalty = sum(max(0.0, polygon_narrowness_score(polygon) - 3.2) for polygon in polygons) * 0.95
    edge_penalty = sum(edge_crowding_value(polygon) for polygon in polygons) * 0.16
    center_penalty = count_center_shared_polygons(polygons) * 1.2
    leaf_pressure_penalty = 0.0
    small_cluster_penalty = 0.0
    for polygon, items in zip(polygons, child_items, strict=False):
        if len(items) <= 1:
            continue
        thickness = polygon_true_minimum_width(polygon)
        min_required = 8.0 + min(len(items), 5) * 1.5
        leaf_pressure_penalty += max(0.0, min_required - thickness) * 0.3
        centroid_x, centroid_y = polygon_centroid(polygon)
        centroid_radius = math.hypot(centroid_x, centroid_y)
        average_target_area = sum(item["targetArea"] for item in items) / len(items)
        if len(items) >= 2 and average_target_area < 320:
            small_cluster_penalty += max(0.0, (40.0 - centroid_radius) / 40.0) * 0.8
    angle_repetition_penalty = 0.0
    if previous_angle is not None:
        angle_difference = abs(normalize_angle(candidate_angle - previous_angle))
        angle_repetition_penalty = max(0.0, 0.36 - angle_difference) * (1.1 if strategy == "v2" else 0.5)
    return (
        triangle_penalty
        + compactness_penalty
        + aspect_penalty
        + thickness_penalty
        + narrowness_penalty
        + edge_penalty
        + center_penalty
        + leaf_pressure_penalty
        + small_cluster_penalty
        + angle_repetition_penalty
    )


def partition_respects_constraints(
    left_polygon: Polygon,
    right_polygon: Polygon,
    left_items: list[dict[str, Any]],
    right_items: list[dict[str, Any]],
) -> bool:
    for polygon, items in ((left_polygon, left_items), (right_polygon, right_items)):
        if not polygon_satisfies_constraints(polygon, items):
            return False
    return True


def polygon_satisfies_constraints(
    polygon: Polygon,
    items: list[dict[str, Any]],
) -> bool:
    if len(polygon) < 3:
        return False
    if unique_vertex_count(polygon) <= 3 and len(items) <= 1:
        return False
    minimum_width = polygon_true_minimum_width(polygon)
    required_width = required_width_for_items(items)
    if minimum_width < required_width:
        return False
    if polygon_aspect_ratio(polygon) > HARD_MAX_ASPECT_RATIO:
        return False
    if polygon_compactness(polygon) < HARD_MIN_COMPACTNESS:
        return False
    if polygon_area(polygon) / max(polygon_perimeter(polygon), EPSILON) < HARD_MIN_AREA_PER_PERIMETER:
        return False
    if polygon_narrowness_score(polygon) > 4.2:
        return False
    return True


def required_width_for_items(items: list[dict[str, Any]]) -> float:
    if len(items) <= 1:
        return HARD_MIN_WIDTH
    return min(HARD_MIN_WIDTH, 8.8 + min(len(items), 4) * 0.7)


def weighted_seed_centroid(items: list[dict[str, Any]]) -> Point:
    total_weight = sum(item["targetArea"] for item in items) or 1.0
    x = sum(item["seed"][0] * item["targetArea"] for item in items) / total_weight
    y = sum(item["seed"][1] * item["targetArea"] for item in items) / total_weight
    return (x, y)


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
    low_quality_count = count_low_quality_cells(metrics)
    banded_count = count_banded_cells(metrics)
    triangle_count = count_triangle_cells(polygons)

    if center_shared_count > (MAX_CENTER_SHARED_POLYGONS + (1 if relaxed else 0)):
        return False
    if low_vertex_count > (1 if relaxed else 0):
        return False
    if triangle_count > (max(2, len(polygons) // 4) if relaxed else max(1, len(polygons) // 5)):
        return False
    if max_relative_error > (MAX_ACCEPTABLE_ERROR + (0.08 if relaxed else 0)):
        return False
    if low_quality_count > (2 if relaxed else 1):
        return False
    if banded_count > (2 if relaxed else 1):
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
    triangle_penalty = count_triangle_cells(polygons) * 0.42
    sliver_penalty = sum(1 for polygon in polygons if polygon_sliver_ratio(polygon) < 0.015) * 0.2
    compactness_penalty = sum(max(0.0, MIN_COMPACTNESS - metric["compactness"]) for metric in metrics) * 2.2
    aspect_penalty = sum(max(0.0, metric["aspectRatio"] - MAX_ASPECT_RATIO) for metric in metrics) * 0.18
    thickness_penalty = sum(max(0.0, MIN_THICKNESS - min(metric["bboxWidth"], metric["bboxHeight"])) for metric in metrics) * 0.06
    banded_penalty = count_banded_cells(metrics) * 0.4
    edge_crowding_penalty = sum(metric["edgeCrowding"] for metric in metrics) * 0.22
    return (
        (max_relative_error * 1.45)
        + mean_relative_error
        + center_penalty
        + low_vertex_penalty
        + triangle_penalty
        + sliver_penalty
        + compactness_penalty
        + aspect_penalty
        + thickness_penalty
        + banded_penalty
        + edge_crowding_penalty
    )


def count_center_shared_polygons(polygons: list[Polygon]) -> int:
    return sum(
        1
        for polygon in polygons
        if any(math.hypot(point[0], point[1]) <= CENTER_SHARE_RADIUS for point in polygon)
    )


def count_triangle_cells(polygons: list[Polygon]) -> int:
    return sum(1 for polygon in polygons if unique_vertex_count(polygon) <= 3)


def unique_vertex_count(polygon: Polygon) -> int:
    return len(dedupe_polygon(polygon))


def polygon_sliver_ratio(polygon: Polygon) -> float:
    xs = [point[0] for point in polygon]
    ys = [point[1] for point in polygon]
    width = max(xs) - min(xs) if xs else 0.0
    height = max(ys) - min(ys) if ys else 0.0
    box_area = max(width * height, EPSILON)
    return polygon_area(polygon) / box_area


def convex_hull(points: Polygon) -> Polygon:
    deduped = sorted(set(points))
    if len(deduped) <= 1:
        return deduped

    def cross(origin: Point, left: Point, right: Point) -> float:
        return ((left[0] - origin[0]) * (right[1] - origin[1])) - ((left[1] - origin[1]) * (right[0] - origin[0]))

    lower: Polygon = []
    for point in deduped:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)

    upper: Polygon = []
    for point in reversed(deduped):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)

    return lower[:-1] + upper[:-1]


def polygon_compactness(polygon: Polygon) -> float:
    area = polygon_area(polygon)
    perimeter = polygon_perimeter(polygon)
    return (4 * math.pi * area) / max(perimeter * perimeter, EPSILON)


def polygon_aspect_ratio(polygon: Polygon) -> float:
    width, height = polygon_bbox_dimensions(polygon)
    return max(width, height) / max(min(width, height), EPSILON)


def polygon_minimum_thickness(polygon: Polygon) -> float:
    width, height = polygon_bbox_dimensions(polygon)
    return min(width, height)


def polygon_true_minimum_width(polygon: Polygon) -> float:
    hull = convex_hull(dedupe_polygon(polygon))
    if len(hull) < 3:
        return polygon_minimum_thickness(polygon)

    best_width = float("inf")
    for index, start in enumerate(hull):
        end = hull[(index + 1) % len(hull)]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.hypot(dx, dy)
        if length <= EPSILON:
            continue
        normal = (-dy / length, dx / length)
        projections = [(normal[0] * point[0]) + (normal[1] * point[1]) for point in hull]
        width = max(projections) - min(projections)
        best_width = min(best_width, width)

    if best_width == float("inf"):
        return polygon_minimum_thickness(polygon)
    return best_width


def polygon_longest_internal_span(polygon: Polygon) -> float:
    hull = convex_hull(dedupe_polygon(polygon))
    if len(hull) < 2:
        return 0.0
    longest = 0.0
    for left_index, left in enumerate(hull):
        for right in hull[left_index + 1 :]:
            longest = max(longest, math.hypot(right[0] - left[0], right[1] - left[1]))
    return longest


def polygon_narrowness_score(polygon: Polygon) -> float:
    minimum_width = polygon_true_minimum_width(polygon)
    longest_span = polygon_longest_internal_span(polygon)
    return longest_span / max(minimum_width, EPSILON)


def polygon_convexity_ratio(polygon: Polygon) -> float:
    hull = convex_hull(dedupe_polygon(polygon))
    hull_area = polygon_area(hull)
    return polygon_area(polygon) / max(hull_area, EPSILON)


def polygon_perimeter(polygon: Polygon) -> float:
    closed = close_polygon(polygon)
    return sum(
        math.hypot(closed[index + 1][0] - closed[index][0], closed[index + 1][1] - closed[index][1])
        for index in range(len(closed) - 1)
    )


def polygon_bbox_dimensions(polygon: Polygon) -> tuple[float, float]:
    xs = [point[0] for point in polygon]
    ys = [point[1] for point in polygon]
    return (
        (max(xs) - min(xs)) if xs else 0.0,
        (max(ys) - min(ys)) if ys else 0.0,
    )


def compute_quality_score(
    relative_error: float,
    compactness: float,
    aspect_ratio: float,
    minimum_thickness: float,
    edge_crowding: float,
    triangle_penalty: float,
) -> float:
    return round(
        (relative_error * 1.45)
        + max(0.0, MIN_COMPACTNESS - compactness) * 2.2
        + max(0.0, aspect_ratio - MAX_ASPECT_RATIO) * 0.18
        + max(0.0, MIN_THICKNESS - minimum_thickness) * 0.06
        + (edge_crowding * 0.22)
        + (triangle_penalty * 0.42),
        6,
    )


def count_low_quality_cells(metrics: list[dict[str, float]]) -> int:
    return sum(
        1
        for metric in metrics
        if metric["compactness"] < MIN_COMPACTNESS
        or metric["aspectRatio"] > MAX_ASPECT_RATIO
        or min(metric["bboxWidth"], metric["bboxHeight"]) < MIN_THICKNESS
        or metric["trianglePenalty"] > 0
        or metric["edgeCrowding"] > 0.85
    )


def count_sliver_cells(metrics: list[dict[str, float]]) -> int:
    return sum(
        1
        for metric in metrics
        if metric["compactness"] < MIN_COMPACTNESS
        or metric["minimumWidth"] < MIN_THICKNESS
        or metric["aspectRatio"] > MAX_ASPECT_RATIO
    )


def count_true_sliver_cells(metrics: list[dict[str, float]]) -> int:
    return sum(
        1
        for metric in metrics
        if metric["minimumWidth"] < 10.5
        or metric["narrownessScore"] > 4.0
        or metric["convexityRatio"] < 0.68
        or ((metric["actualArea"] > 0) and ((polygon_perimeter_from_metric(metric) ** 2) / metric["actualArea"] > 42.0))
    )


def polygon_perimeter_from_metric(metric: dict[str, float]) -> float:
    compactness = max(metric["compactness"], EPSILON)
    area = max(metric["actualArea"], EPSILON)
    return math.sqrt((4 * math.pi * area) / compactness)


def polygon_is_true_sliver(polygon: Polygon) -> bool:
    area = polygon_area(polygon)
    compactness = polygon_compactness(polygon)
    minimum_width = polygon_true_minimum_width(polygon)
    narrowness = polygon_narrowness_score(polygon)
    convexity = polygon_convexity_ratio(polygon)
    perimeter = polygon_perimeter(polygon)
    return (
        minimum_width < 10.5
        or narrowness > 4.0
        or convexity < 0.68
        or ((perimeter * perimeter) / max(area, EPSILON) > 42.0)
        or compactness < 0.12
    )


def compute_descendant_risk_from_metrics(metrics: list[dict[str, float]]) -> float:
    if not metrics:
        return 0.0
    return mean(
        max(0.0, metric["narrownessScore"] - 2.8) * 0.45
        + max(0.0, 0.78 - metric["convexityRatio"]) * 1.8
        + max(0.0, 11.0 - metric["minimumWidth"]) * 0.2
        + metric["edgeCrowding"] * 0.35
        for metric in metrics
    )


def count_labelable_cells(metrics: list[dict[str, float]]) -> int:
    return sum(
        1
        for metric in metrics
        if min(metric["bboxWidth"], metric["bboxHeight"]) >= MIN_LABEL_WIDTH
        and max(metric["bboxWidth"], metric["bboxHeight"]) >= MIN_LABEL_HEIGHT
        and metric["actualArea"] >= MIN_LABEL_AREA
    )


def compute_small_cell_clustering_score(metrics: list[dict[str, float]]) -> float:
    if len(metrics) < 2:
        return 0.0

    sorted_areas = sorted(metric["actualArea"] for metric in metrics)
    area_threshold = sorted_areas[max(0, (len(sorted_areas) // 2) - 1)]
    small_cells = [
        metric
        for metric in metrics
        if metric["actualArea"] <= area_threshold
    ]
    if len(small_cells) < 2:
        return 0.0

    total = 0.0
    pairs = 0
    for left_index, left in enumerate(small_cells):
        for right in small_cells[left_index + 1 :]:
            distance = math.hypot(
                left["centroidX"] - right["centroidX"],
                left["centroidY"] - right["centroidY"],
            )
            total += 1 / max(distance, 1.0)
            pairs += 1
    return total / max(pairs, 1)


def compute_small_cell_center_clustering_score(metrics: list[dict[str, float]]) -> float:
    if not metrics:
        return 0.0

    sorted_areas = sorted(metric["actualArea"] for metric in metrics)
    area_threshold = sorted_areas[max(0, (len(sorted_areas) // 2) - 1)]
    small_cells = [
        metric
        for metric in metrics
        if metric["actualArea"] <= area_threshold
    ]
    if not small_cells:
        return 0.0

    return sum(
        max(0.0, (42.0 - math.hypot(metric["centroidX"], metric["centroidY"])) / 42.0)
        for metric in small_cells
    ) / len(small_cells)


def compute_label_overlap_count(
    categories: list[dict[str, Any]],
    metrics: list[dict[str, float]],
) -> int:
    label_boxes: list[tuple[float, float, float, float]] = []
    for category, metric in zip(categories, metrics, strict=False):
        if min(metric["bboxWidth"], metric["bboxHeight"]) < MIN_LABEL_WIDTH or metric["actualArea"] < MIN_LABEL_AREA:
            continue
        label_width = min(metric["bboxWidth"] * 0.9, max(10.0, len(str(category["categoryName"])) * 3.2))
        label_height = min(metric["bboxHeight"] * 0.85, 8.5)
        half_width = label_width / 2
        half_height = label_height / 2
        label_boxes.append(
            (
                metric["centroidX"] - half_width,
                metric["centroidY"] - half_height,
                metric["centroidX"] + half_width,
                metric["centroidY"] + half_height,
            )
        )

    overlap_count = 0
    for index, left in enumerate(label_boxes):
        for right in label_boxes[index + 1 :]:
            if not (
                left[2] <= right[0]
                or right[2] <= left[0]
                or left[3] <= right[1]
                or right[3] <= left[1]
            ):
                overlap_count += 1
    return overlap_count


def compute_dominant_angle_repetition_score(polygons: list[Polygon]) -> float:
    bins = [0] * 12
    total_edges = 0
    for polygon in polygons:
        closed = close_polygon(polygon)
        for index in range(len(closed) - 1):
            dx = closed[index + 1][0] - closed[index][0]
            dy = closed[index + 1][1] - closed[index][1]
            length = math.hypot(dx, dy)
            if length <= EPSILON:
                continue
            angle = normalize_angle(math.atan2(dy, dx))
            bucket = int(((angle % math.pi) / math.pi) * len(bins)) % len(bins)
            bins[bucket] += 1
            total_edges += 1
    if total_edges == 0:
        return 0.0
    return max(bins) / total_edges


def count_banded_cells(metrics: list[dict[str, float]]) -> int:
    return sum(
        1
        for metric in metrics
        if metric["bboxHeight"] < 7.5
        or (metric["bboxWidth"] > 30 and metric["bboxHeight"] < 10)
    )


def edge_crowding_value(polygon: Polygon) -> float:
    centroid_x, centroid_y = polygon_centroid(polygon)
    centroid_radius = math.hypot(centroid_x, centroid_y)
    width, height = polygon_bbox_dimensions(polygon)
    edge_proximity = max(
        0.0,
        (centroid_radius - EDGE_CROWDING_RADIUS) / max(SEMICIRCLE_RADIUS - EDGE_CROWDING_RADIUS, EPSILON),
    )
    thinness = max(0.0, (12.0 - min(width, height)) / 12.0)
    return round(edge_proximity + (thinness * 0.6), 6)


def build_seed_placement_order(categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    weighted = sorted(
        categories,
        key=lambda category: (-category["weight"], category["sortOrder"], category["categoryId"]),
    )
    if len(weighted) <= 2:
        return weighted

    left: list[dict[str, Any]] = []
    right: list[dict[str, Any]] = []
    for index, category in enumerate(weighted):
        if index % 2 == 0:
            left.append(category)
        else:
            right.append(category)

    return left + list(reversed(right))


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


def normalize_angle(angle: float) -> float:
    while angle <= -math.pi:
        angle += math.tau
    while angle > math.pi:
        angle -= math.tau
    return angle


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
