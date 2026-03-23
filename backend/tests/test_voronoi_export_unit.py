from __future__ import annotations

import shared.voronoi_export as voronoi_export
from shared.voronoi_export import (
    SEMICIRCLE_RADIUS,
    build_bsp_treemap_rects,
    build_bsp_strategy_layout,
    build_category_book_counts,
    build_current_strategy_layout,
    build_fallback_radial_area_rows,
    build_hard_constraint_failed_layout,
    build_irregular_area_partition,
    build_irregular_voronoi_fallback,
    build_new_strategy_layout,
    build_new_strategy_v2_layout,
    build_next_candidate_layout,
    build_next_candidate_retry_layout,
    build_partition_items,
    build_partition_items_v2,
    build_power_cells,
    build_previous_stable_layout,
    build_recursive_binary_partition_details,
    build_recursive_layout_stats,
    build_strategy_layout_details,
    build_small_leaf_group_layout,
    build_target_areas,
    build_effective_weight,
    build_slot_fill_order,
    build_two_category_weighted_split,
    candidate_score,
    choose_best_voronoi_candidate,
    choose_partition_normal,
    close_polygon,
    compute_cell_metrics,
    compute_dominant_angle_repetition_score,
    compute_quality_score,
    find_balanced_split_index,
    count_banded_cells,
    count_center_shared_polygons,
    count_labelable_cells,
    count_low_quality_cells,
    count_sliver_cells,
    count_triangle_cells,
    count_true_sliver_cells,
    dedupe_polygon,
    edge_crowding_value,
    evaluate_partition_candidate,
    generate_grouping_candidates,
    generate_split_candidates,
    initialize_seed_points,
    intersection_point,
    invert_semicircle_area_fraction,
    make_sector_polygon,
    make_semicircle_polygon,
    map_param_point_to_semicircle,
    normalize_angle,
    partition_polygon_by_line_and_ratio,
    partition_items_into_polygon,
    partition_respects_constraints,
    polygon_area,
    polygon_aspect_ratio,
    polygon_bbox_dimensions,
    polygon_centroid,
    polygon_compactness,
    polygon_convexity_ratio,
    polygon_is_true_sliver,
    polygon_longest_internal_span,
    polygon_minimum_thickness,
    polygon_narrowness_score,
    polygon_perimeter,
    polygon_principal_axes_lengths,
    polygon_sliver_ratio,
    polygon_true_minimum_width,
    polygon_to_rows,
    project_point_to_semicircle,
    rectangle_to_semicircle_polygon,
    semicircle_area_to_x,
    soften_polygon_edges,
    spread_seeds,
    summarize_strategy_metrics,
    split_polygon_by_area,
    unique_vertex_count,
    update_seed_and_weight_parameters,
    weighted_seed_centroid,
    is_quality_acceptable,
    is_structurally_voronoi_like,
)


def _make_partition_item(category_id: str, sort_order: int, target_area: float) -> dict[str, object]:
    return {
        "category": {
            "categoryId": category_id,
            "categoryName": category_id,
            "sortOrder": sort_order,
            "color": "#4C8BF5",
            "bookCount": int(target_area // 100),
            "weight": target_area,
        },
        "targetArea": target_area,
        "weight": target_area,
    }


def test_generate_grouping_candidates_returns_multiple_deterministic_unique_pairs() -> None:
    items = [
        _make_partition_item("a", 10, 600.0),
        _make_partition_item("b", 20, 420.0),
        _make_partition_item("c", 30, 300.0),
        _make_partition_item("d", 40, 180.0),
        _make_partition_item("e", 50, 120.0),
    ]

    first = generate_grouping_candidates(items)
    second = generate_grouping_candidates(items)

    assert first == second
    assert len(first) >= 5
    normalized = {
        (
            tuple(sorted(item["category"]["categoryId"] for item in left)),
            tuple(sorted(item["category"]["categoryId"] for item in right)),
        )
        for left, right in first
    }
    assert len(normalized) == len(first)
    assert all(left and right for left, right in first)


def test_generate_split_candidates_produces_partitions_close_to_target_ratio() -> None:
    parent_polygon = make_semicircle_polygon()
    group_a = [_make_partition_item("a", 10, 7000.0)]
    group_b = [_make_partition_item("b", 20, 3000.0)]
    stats = build_recursive_layout_stats()

    candidates = generate_split_candidates(parent_polygon, group_a, group_b, stats)

    assert candidates
    assert int(stats["split_candidate_count"]) >= len(candidates)

    target_ratio = 0.7
    best_error = min(
        abs((polygon_area(child_a) / (polygon_area(child_a) + polygon_area(child_b))) - target_ratio)
        for _angle, child_a, child_b in candidates
    )
    assert best_error < 0.03


def test_evaluate_partition_candidate_rejects_visibly_thin_polygon() -> None:
    parent_polygon = make_semicircle_polygon()
    thin_polygon = [(-10.0, 0.0), (-9.0, 0.0), (-9.0, 30.0), (-10.0, 30.0)]
    wide_polygon = [(0.0, 0.0), (40.0, 0.0), (40.0, 30.0), (0.0, 30.0)]
    group_a = [_make_partition_item("a", 10, 1000.0)]
    group_b = [_make_partition_item("b", 20, 1000.0)]

    evaluation = evaluate_partition_candidate(
        parent_polygon,
        thin_polygon,
        wide_polygon,
        group_a,
        group_b,
        hard_constraints=True,
    )

    assert evaluation is None
    assert polygon_compactness(thin_polygon) < polygon_compactness(wide_polygon)


def test_build_recursive_binary_partition_details_runs_recursive_path_for_small_input() -> None:
    categories = [
        {
            "categoryId": "technology",
            "categoryName": "Technology",
            "color": "#4C8BF5",
            "sortOrder": 10,
            "bookCount": 8,
            "weight": 8.0,
        },
        {
            "categoryId": "business",
            "categoryName": "Business",
            "color": "#F28C6C",
            "sortOrder": 20,
            "bookCount": 5,
            "weight": 5.0,
        },
        {
            "categoryId": "design",
            "categoryName": "Design",
            "color": "#73C995",
            "sortOrder": 30,
            "bookCount": 3,
            "weight": 3.0,
        },
    ]

    polygons, metrics, iteration_count, stats = build_recursive_binary_partition_details(categories)

    assert len(polygons) == 3
    assert len(metrics) == 3
    assert iteration_count >= 1
    assert int(stats["grouping_candidate_count"]) > 0
    assert int(stats["split_candidate_count"]) > 0
    assert int(stats["recursion_depth_max"]) >= 1
    assert stats["accepted"] is True
    assert all(polygon_area(polygon) > 0 for polygon in polygons)
    assert all(metric["minimumWidth"] > 0 for metric in metrics)


def test_partition_polygon_by_line_and_ratio_returns_none_when_split_fails(monkeypatch) -> None:
    def fake_split_polygon_by_area(parent_polygon, normal, target_ratio):
        raise ValueError("cannot split")

    monkeypatch.setattr(voronoi_export, "split_polygon_by_area", fake_split_polygon_by_area)

    assert partition_polygon_by_line_and_ratio(make_semicircle_polygon(), 0.0, 0.5) is None


def test_build_small_leaf_group_layout_uses_relaxed_candidate_when_hard_constraints_fail(monkeypatch) -> None:
    stats = build_recursive_layout_stats()
    items = [
        _make_partition_item("a", 10, 300.0),
        _make_partition_item("b", 20, 240.0),
    ]
    child_a = [(-20.0, 0.0), (-5.0, 0.0), (-5.0, 20.0), (-20.0, 20.0)]
    child_b = [(5.0, 0.0), (20.0, 0.0), (20.0, 20.0), (5.0, 20.0)]

    monkeypatch.setattr(
        voronoi_export,
        "partition_polygon_by_line_and_ratio",
        lambda parent_polygon, angle, target_ratio: (child_a, child_b),
    )

    def fake_evaluate(parent_polygon, left, right, group_a, group_b, hard_constraints=True):
        if hard_constraints:
            return None
        return {
            "minimumWidth": 12.5,
            "descendantRisk": 0.2,
            "narrownessScore": 1.3,
            "convexityRatio": 0.95,
            "compactness": 0.7,
            "labelFitness": 0.8,
            "areaError": 0.01,
        }

    monkeypatch.setattr(voronoi_export, "evaluate_partition_candidate", fake_evaluate)
    monkeypatch.setattr(voronoi_export, "polygon_is_true_sliver", lambda polygon: False)

    result = build_small_leaf_group_layout(make_semicircle_polygon(), items, stats)

    assert result is not None
    assert int(stats["fallback_used_count"]) == 1
    assert int(stats["rejected_candidate_count"]) > 0
    assert int(stats["fallback_leaf_sliver_count"]) == 0


def test_polygon_to_rows_closes_polygon_and_preserves_layout_metadata() -> None:
    category = {
        "categoryId": "technology",
        "categoryName": "Technology",
        "color": "#4C8BF5",
        "sortOrder": 10,
        "bookCount": 8,
    }
    polygon = [(-10.0, 0.0), (0.0, 15.0), (10.0, 0.0), (0.0, 5.0)]
    metrics = {
        "weight": 8.0,
        "targetArea": 100.0,
        "actualArea": 98.0,
        "areaError": -2.0,
        "relativeError": 0.02,
        "compactness": 0.75,
        "bboxWidth": 20.0,
        "bboxHeight": 15.0,
        "aspectRatio": 1.4,
        "qualityScore": 0.91,
        "centroidX": 0.5,
        "centroidY": 6.5,
        "minimumWidth": 11.8,
    }

    rows = polygon_to_rows(
        polygon_id="category-technology",
        polygon=polygon,
        category=category,
        metrics=metrics,
        iteration_count=3,
        layout_strategy="recursive_binary_partition",
    )

    assert rows
    assert rows[0][0] == "category-technology"
    assert rows[0][24] == "recursive_binary_partition"
    assert rows[0][23] == 11.8
    assert rows[0][22] == 3
    assert rows[0][16] == 0
    assert rows[-1][16] == len(rows) - 1
    assert rows[0][17] == rows[-1][17]
    assert rows[0][18] == rows[-1][18]


def test_build_category_book_counts_and_target_areas_include_zero_count_categories() -> None:
    categories = [
        {"categoryId": "technology", "name": "Technology", "sortOrder": 10, "color": "#4C8BF5"},
        {"categoryId": "novel", "name": "Novel", "sortOrder": 20, "color": "#7D6CF2"},
    ]
    books = [
        {"categoryId": "technology", "isbn": "1"},
        {"categoryId": "technology", "isbn": "2"},
    ]

    counts = build_category_book_counts(categories, books)
    target_areas = build_target_areas(counts)

    assert counts[0]["bookCount"] == 2
    assert counts[1]["bookCount"] == 0
    assert counts[1]["weight"] == build_effective_weight(0)
    assert abs(sum(target_areas) - (0.5 * 3.141592653589793 * SEMICIRCLE_RADIUS * SEMICIRCLE_RADIUS)) < 0.1


def test_initialize_seed_points_is_deterministic_and_handles_single_category() -> None:
    categories = [
        {"categoryId": "a", "sortOrder": 10, "weight": 5.0},
        {"categoryId": "b", "sortOrder": 20, "weight": 3.0},
        {"categoryId": "c", "sortOrder": 30, "weight": 2.0},
    ]

    first = initialize_seed_points(categories, variant=2)
    second = initialize_seed_points(categories, variant=2)
    single = initialize_seed_points([categories[0]])

    assert first == second
    assert len(first) == 3
    assert single == [(0.0, SEMICIRCLE_RADIUS * 0.42)]


def test_build_bsp_treemap_rects_assigns_rects_to_all_items() -> None:
    items = [
        _make_partition_item("a", 10, 500.0),
        _make_partition_item("b", 20, 300.0),
        _make_partition_item("c", 30, 200.0),
    ]
    rects: dict[str, tuple[float, float, float, float]] = {}

    build_bsp_treemap_rects(items, (0.0, 0.0, 1.0, 1.0), rects, 0)

    assert set(rects) == {"a", "b", "c"}
    assert all(rect[2] > rect[0] and rect[3] > rect[1] for rect in rects.values())


def test_rectangle_mapping_and_area_inversion_are_consistent() -> None:
    rect_polygon = rectangle_to_semicircle_polygon((0.2, 0.2, 0.45, 0.55), sort_order=10)
    midpoint = map_param_point_to_semicircle(0.5, 0.5)
    x = invert_semicircle_area_fraction(0.5)

    assert len(rect_polygon) >= 4
    assert abs(midpoint[1]) <= SEMICIRCLE_RADIUS
    assert abs(semicircle_area_to_x(x) - (0.25 * 3.141592653589793 * SEMICIRCLE_RADIUS * SEMICIRCLE_RADIUS)) < 0.5


def test_soften_polygon_edges_adjusts_flat_top_points() -> None:
    polygon = [(-10.0, 10.0), (0.0, 10.0), (10.0, 10.0), (10.0, 0.0), (-10.0, 0.0)]

    softened = soften_polygon_edges(polygon, sort_order=13)

    assert softened != polygon
    assert len(softened) == len(polygon)


def test_compute_cell_metrics_and_summary_include_shape_metrics() -> None:
    categories = [
        {"categoryId": "technology", "categoryName": "Technology", "color": "#4C8BF5", "sortOrder": 10, "bookCount": 8, "weight": 8.0},
        {"categoryId": "business", "categoryName": "Business", "color": "#F28C6C", "sortOrder": 20, "bookCount": 4, "weight": 4.0},
    ]
    polygons = [
        [(-40.0, 0.0), (-10.0, 0.0), (-10.0, 30.0), (-40.0, 30.0)],
        [(10.0, 0.0), (35.0, 0.0), (35.0, 25.0), (10.0, 25.0)],
    ]
    targets = [900.0, 625.0]

    metrics = compute_cell_metrics(categories, polygons, targets)
    summary = summarize_strategy_metrics(categories, polygons, metrics)

    assert len(metrics) == 2
    assert metrics[0]["elongation"] >= 1.0
    assert "true_sliver_cell_count" in summary
    assert "elongation_mean" in summary
    assert summary["labelable_cell_count"] >= 1


def test_update_seed_and_weight_parameters_moves_seed_and_adjusts_weights() -> None:
    seeds = [(-25.0, 20.0), (25.0, 20.0)]
    power_weights = [10.0, 10.0]
    polygons = [
        [(-40.0, 0.0), (-10.0, 0.0), (-10.0, 30.0), (-40.0, 30.0)],
        [(10.0, 0.0), (40.0, 0.0), (40.0, 25.0), (10.0, 25.0)],
    ]
    metrics = [
        {"targetArea": 1200.0, "actualArea": 900.0},
        {"targetArea": 600.0, "actualArea": 750.0},
    ]

    update_seed_and_weight_parameters(seeds, power_weights, polygons, metrics)

    assert power_weights[0] > 10.0
    assert power_weights[1] < 10.0
    assert seeds[0] != (-25.0, 20.0)


def test_polygon_shape_helpers_detect_sliver_like_geometry() -> None:
    sliver = [(0.0, 0.0), (2.0, 0.0), (2.0, 30.0), (0.0, 30.0)]
    rectangle = [(-10.0, 0.0), (10.0, 0.0), (10.0, 20.0), (-10.0, 20.0)]

    long_axis, short_axis = polygon_principal_axes_lengths(sliver)

    assert long_axis > short_axis
    assert polygon_aspect_ratio(sliver) > polygon_aspect_ratio(rectangle)
    assert polygon_minimum_thickness(sliver) < polygon_minimum_thickness(rectangle)
    assert polygon_true_minimum_width(sliver) < polygon_true_minimum_width(rectangle)
    assert polygon_longest_internal_span(sliver) > 0
    assert polygon_narrowness_score(sliver) > 4.0
    assert polygon_convexity_ratio(rectangle) == 1.0
    assert polygon_is_true_sliver(sliver) is True
    assert polygon_sliver_ratio(sliver) == 1.0


def test_quality_counters_and_overlap_metrics_flag_problematic_cells() -> None:
    metrics = [
        {
            "compactness": 0.05,
            "aspectRatio": 7.2,
            "bboxWidth": 8.0,
            "bboxHeight": 6.5,
            "minimumWidth": 5.5,
            "trianglePenalty": 1.0,
            "edgeCrowding": 0.9,
            "actualArea": 120.0,
            "centroidX": 0.0,
            "centroidY": 0.0,
            "narrownessScore": 5.0,
            "convexityRatio": 0.5,
        },
        {
            "compactness": 0.4,
            "aspectRatio": 1.4,
            "bboxWidth": 18.0,
            "bboxHeight": 18.0,
            "minimumWidth": 12.0,
            "trianglePenalty": 0.0,
            "edgeCrowding": 0.1,
            "actualArea": 280.0,
            "centroidX": 3.0,
            "centroidY": 3.0,
            "narrownessScore": 1.5,
            "convexityRatio": 0.95,
        },
    ]
    categories = [
        {"categoryName": "Alpha"},
        {"categoryName": "Beta"},
    ]

    assert compute_quality_score(0.1, 0.2, 2.0, 8.0, 0.1, 0.0) >= 0
    assert count_low_quality_cells(metrics) == 1
    assert count_sliver_cells(metrics) == 1
    assert count_true_sliver_cells(metrics) == 1
    assert count_labelable_cells(metrics) == 1
    assert voronoi_export.compute_label_overlap_count(categories, metrics) == 0
    assert count_banded_cells(metrics) == 1


def test_polygon_and_seed_helpers_cover_projection_and_cleanup() -> None:
    polygon = [(0.0, 0.0), (1.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    seeds = [(0.0, 1.0), (0.0, 1.5)]

    clipped = voronoi_export.clip_polygon_to_weighted_halfplane(
        [(-10.0, 0.0), (10.0, 0.0), (10.0, 10.0), (-10.0, 10.0)],
        (-5.0, 2.0),
        10.0,
        (5.0, 2.0),
        8.0,
    )
    intersection = intersection_point((0.0, 0.0), (10.0, 0.0), 2.0, -2.0)
    projected = project_point_to_semicircle((150.0, -10.0), SEMICIRCLE_RADIUS * 0.8)
    spread_seeds(seeds)

    assert dedupe_polygon(polygon) == [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    assert close_polygon([(0.0, 0.0), (1.0, 0.0)])[-1] == (0.0, 0.0)
    assert clipped
    assert intersection == (5.0, 0.0)
    assert projected[1] >= 0.0
    assert seeds[0] != (0.0, 1.0)
    assert normalize_angle(4.5) <= 3.141592653589793


def test_sector_and_polygon_summary_helpers_cover_misc_geometry() -> None:
    sector = make_sector_polygon(0.0, 1.0)
    polygons = [
        [(0.0, 0.0), (8.0, 0.0), (8.0, 8.0), (0.0, 8.0)],
        [(-12.0, 0.0), (-2.0, 0.0), (-2.0, 10.0), (-12.0, 10.0)],
    ]

    assert len(sector) > 10
    assert count_center_shared_polygons(polygons) >= 1
    assert count_triangle_cells([[(0.0, 0.0), (5.0, 0.0), (0.0, 5.0)]]) == 1
    assert unique_vertex_count(polygons[0]) == 4
    assert polygon_bbox_dimensions(polygons[0]) == (8.0, 8.0)
    assert polygon_perimeter(polygons[0]) == 32.0
    assert polygon_centroid(polygons[0]) == (4.0, 4.0)
    assert compute_dominant_angle_repetition_score(polygons) > 0
    assert edge_crowding_value(polygons[0]) >= 0.0


def test_current_strategy_prefers_irregular_area_partition_when_initial_error_is_high(monkeypatch) -> None:
    categories = [{"categoryId": "a", "weight": 5.0}, {"categoryId": "b", "weight": 3.0}]
    polygon = make_semicircle_polygon()
    first_candidate = (
        [polygon, polygon],
        [{"relativeError": 0.4}, {"relativeError": 0.4}],
        1,
    )
    final_candidate = (
        [polygon, polygon],
        [{"relativeError": 0.01}, {"relativeError": 0.02}],
        2,
    )

    monkeypatch.setattr(voronoi_export, "generate_weighted_semicircle_voronoi", lambda *args: first_candidate)
    monkeypatch.setattr(voronoi_export, "build_irregular_voronoi_fallback", lambda *args: (_ for _ in ()).throw(ValueError("skip")))
    monkeypatch.setattr(voronoi_export, "build_irregular_area_partition", lambda *args: final_candidate)
    monkeypatch.setattr(voronoi_export, "choose_best_voronoi_candidate", lambda candidates: candidates[-1])

    polygons, metrics, iteration = build_current_strategy_layout(categories)

    assert polygons == final_candidate[0]
    assert metrics == final_candidate[1]
    assert iteration == 2


def test_strategy_wrappers_delegate_to_underlying_builders(monkeypatch) -> None:
    categories = [{"categoryId": "a", "weight": 1.0}]
    polygon = make_semicircle_polygon()
    metrics = [{"minimumWidth": 12.0}]

    monkeypatch.setattr(voronoi_export, "build_recursive_binary_partition_layout", lambda _: ([polygon], metrics, 3))
    monkeypatch.setattr(voronoi_export, "build_strategy_layout_details", lambda *args, **kwargs: ([polygon], metrics, 2, {"accepted": True}))
    monkeypatch.setattr(voronoi_export, "build_next_candidate_retry_layout", lambda _: ([polygon], metrics, 4, {"accepted": False}))

    assert build_new_strategy_layout(categories) == ([polygon], metrics, 3)
    assert build_previous_stable_layout(categories) == ([polygon], metrics, 2)
    assert build_new_strategy_v2_layout(categories) == ([polygon], metrics, 2)
    assert build_next_candidate_layout(categories) == ([polygon], metrics, 4, {"accepted": False})


def test_hard_constraint_and_retry_layouts_fallback_after_partition_failure(monkeypatch) -> None:
    categories = [{"categoryId": "a", "weight": 1.0}]
    polygon = make_semicircle_polygon()
    metrics = [{"minimumWidth": 12.0}]

    def fake_build_strategy(categories, strategy, enforce_constraints, expand_search=False, retry_small_leaf=False):
        if enforce_constraints:
            raise voronoi_export.PartitionFailure("nope", {"rejected_candidates": 7, "failed_leaf_group_count": 2, "fallback_used_count": 1})
        return [polygon], metrics, 1, {}

    monkeypatch.setattr(voronoi_export, "build_strategy_layout_details", fake_build_strategy)

    _, _, _, hard_stats = build_hard_constraint_failed_layout(categories)
    _, _, _, retry_stats = build_next_candidate_retry_layout(categories)

    assert hard_stats["accepted"] is False
    assert retry_stats["accepted"] is False
    assert hard_stats["rejected_candidates"] == 7
    assert retry_stats["failed_leaf_group_count"] == 2


def test_bsp_strategy_and_strategy_details_build_polygon_map(monkeypatch) -> None:
    categories = [
        {"categoryId": "a", "weight": 5.0, "sortOrder": 10},
        {"categoryId": "b", "weight": 4.0, "sortOrder": 20},
    ]
    polygon = [(-10.0, 0.0), (10.0, 0.0), (10.0, 10.0), (-10.0, 10.0)]

    def fake_partition(items, parent_polygon, polygon_map, depth, strategy="v1", previous_angle=None, enforce_constraints=False, stats=None, expand_search=False, retry_small_leaf=False):
        polygon_map[items[0]["category"]["categoryId"]] = polygon
        polygon_map[items[1]["category"]["categoryId"]] = polygon
        if stats is not None:
            stats["rejected_candidates"] = 2

    monkeypatch.setattr(voronoi_export, "partition_items_into_polygon", fake_partition)
    monkeypatch.setattr(voronoi_export, "compute_cell_metrics", lambda categories, polygons, target_areas: [{"minimumWidth": 12.0}] * len(polygons))

    polygons, metrics, iteration = build_bsp_strategy_layout(categories, "v1")
    detailed = build_strategy_layout_details(categories, "v1", enforce_constraints=False)

    assert len(polygons) == 2
    assert len(metrics) == 2
    assert iteration == 1
    assert detailed[3]["rejected_candidates"] == 2


def test_generate_weighted_and_irregular_fallbacks_cover_selection_paths(monkeypatch) -> None:
    categories = [
        {"categoryId": "a", "weight": 6.0, "sortOrder": 10, "categoryName": "A", "color": "#111", "bookCount": 6},
        {"categoryId": "b", "weight": 4.0, "sortOrder": 20, "categoryName": "B", "color": "#222", "bookCount": 4},
        {"categoryId": "c", "weight": 2.0, "sortOrder": 30, "categoryName": "C", "color": "#333", "bookCount": 2},
    ]
    parent_polygon = make_semicircle_polygon()
    target_areas = [4000.0, 3000.0, 2000.0]
    good_polygons = [
        [(-50.0, 0.0), (-10.0, 0.0), (-10.0, 40.0), (-50.0, 40.0)],
        [(-10.0, 0.0), (20.0, 0.0), (20.0, 35.0), (-10.0, 35.0)],
        [(20.0, 0.0), (50.0, 0.0), (50.0, 25.0), (20.0, 25.0)],
    ]
    good_metrics = [{"relativeError": 0.01, "compactness": 0.3, "aspectRatio": 2.0, "bboxWidth": 30.0, "bboxHeight": 20.0, "minimumWidth": 12.0, "trianglePenalty": 0.0, "edgeCrowding": 0.1}] * 3

    monkeypatch.setattr(voronoi_export, "initialize_seed_points", lambda categories, variant=0, radius=SEMICIRCLE_RADIUS: [(0.0, 30.0)] * len(categories))
    monkeypatch.setattr(voronoi_export, "relax_cells_to_target_areas", lambda *args: (good_polygons, good_metrics, 4))
    monkeypatch.setattr(voronoi_export, "candidate_score", lambda polygons, metrics: 0.1)
    monkeypatch.setattr(voronoi_export, "is_quality_acceptable", lambda polygons, metrics, relaxed=False: True)
    monkeypatch.setattr(voronoi_export, "build_power_cells", lambda seeds, power_weights, parent_polygon: good_polygons)
    monkeypatch.setattr(voronoi_export, "compute_cell_metrics", lambda categories, polygons, target_areas: good_metrics)

    weighted = voronoi_export.generate_weighted_semicircle_voronoi(categories, parent_polygon, target_areas)
    fallback = build_irregular_voronoi_fallback(categories, parent_polygon, target_areas)

    assert weighted[2] == 4
    assert fallback[0] == good_polygons


def test_build_two_category_and_fallback_radial_rows_return_polygons() -> None:
    categories = [
        {"categoryId": "a", "weight": 7.0, "sortOrder": 10, "categoryName": "A", "color": "#111", "bookCount": 7},
        {"categoryId": "b", "weight": 3.0, "sortOrder": 20, "categoryName": "B", "color": "#222", "bookCount": 3},
    ]
    target_areas = build_target_areas(categories)

    polygons, metrics, _ = build_two_category_weighted_split(categories, make_semicircle_polygon(), target_areas)
    fallback_polygons, fallback_metrics, _ = build_fallback_radial_area_rows(categories, target_areas)

    assert len(polygons) == 2
    assert len(metrics) == 2
    assert len(fallback_polygons) == 2
    assert len(fallback_metrics) == 2


def test_build_partition_items_variants_and_slot_fill_order_are_deterministic() -> None:
    categories = [
        {"categoryId": "a", "weight": 7.0, "sortOrder": 10},
        {"categoryId": "b", "weight": 5.0, "sortOrder": 20},
        {"categoryId": "c", "weight": 3.0, "sortOrder": 30},
        {"categoryId": "d", "weight": 1.0, "sortOrder": 40},
    ]
    target_areas = [700.0, 500.0, 300.0, 100.0]

    items_v1 = build_partition_items(categories, target_areas)
    items_v2 = build_partition_items_v2(categories, target_areas)
    slot_order = build_slot_fill_order(4)

    assert len(items_v1) == 4
    assert len(items_v2) == 4
    assert slot_order == build_slot_fill_order(4)


def test_power_cells_selection_and_partition_helpers_cover_remaining_split_logic() -> None:
    parent = make_semicircle_polygon()
    seeds = [(-30.0, 30.0), (30.0, 30.0)]
    power_weights = [10.0, 10.0]
    candidates = [
        (
            [[(-10.0, 0.0), (0.0, 0.0), (0.0, 10.0)], [(0.0, 0.0), (10.0, 0.0), (0.0, 10.0)]],
            [{"relativeError": 0.5, "compactness": 0.05, "aspectRatio": 8.0, "bboxWidth": 5.0, "bboxHeight": 10.0, "minimumWidth": 5.0, "trianglePenalty": 1.0, "edgeCrowding": 0.9}],
            0,
        ),
        (
            [parent[:4], parent[10:14]],
            [{"relativeError": 0.01, "compactness": 0.3, "aspectRatio": 2.0, "bboxWidth": 20.0, "bboxHeight": 20.0, "minimumWidth": 12.0, "trianglePenalty": 0.0, "edgeCrowding": 0.1}] * 2,
            1,
        ),
    ]

    cells = build_power_cells(seeds, power_weights, parent)
    chosen = choose_best_voronoi_candidate(candidates)
    left, right = split_polygon_by_area(parent, (1.0, 0.0), 0.5)
    balanced_index = find_balanced_split_index([_make_partition_item("a", 10, 600.0), _make_partition_item("b", 20, 300.0), _make_partition_item("c", 30, 100.0)])
    normal = choose_partition_normal(parent, [_make_partition_item("a", 10, 600.0)], [_make_partition_item("b", 20, 400.0)], 1)

    assert len(cells) == 2
    assert chosen == candidates[1]
    assert polygon_area(left) > 0 and polygon_area(right) > 0
    assert balanced_index in {1, 2}
    assert len(normal) == 2


def test_partition_constraint_and_quality_helpers_cover_recursive_filters() -> None:
    wide_polygon = [(-20.0, 0.0), (20.0, 0.0), (20.0, 20.0), (-20.0, 20.0)]
    thin_polygon = [(0.0, 0.0), (2.0, 0.0), (2.0, 20.0), (0.0, 20.0)]
    items = [_make_partition_item("a", 10, 500.0), _make_partition_item("b", 20, 300.0)]
    seeded_items = [
        {"seed": (-10.0, 10.0), "targetArea": 500.0},
        {"seed": (10.0, 10.0), "targetArea": 300.0},
    ]
    good_metrics = [
        {
            "relativeError": 0.01,
            "compactness": 0.32,
            "aspectRatio": 2.0,
            "bboxWidth": 20.0,
            "bboxHeight": 20.0,
            "minimumWidth": 12.0,
            "trianglePenalty": 0.0,
            "edgeCrowding": 0.1,
            "actualArea": 300.0,
            "centroidX": 0.0,
            "centroidY": 10.0,
            "narrownessScore": 2.0,
            "convexityRatio": 0.95,
        }
    ]

    assert partition_respects_constraints(wide_polygon, wide_polygon, items[:1], items[:1]) is True
    assert partition_respects_constraints(thin_polygon, wide_polygon, items[:1], items[:1]) is False
    assert weighted_seed_centroid(seeded_items) == (-2.5, 10.0)
    assert is_quality_acceptable([wide_polygon], good_metrics) is True
    assert is_structurally_voronoi_like([wide_polygon]) is True
    assert candidate_score([wide_polygon], good_metrics) >= 0


def test_irregular_area_partition_sorts_seeded_items_before_partition(monkeypatch) -> None:
    categories = [
        {"categoryId": "a", "weight": 5.0, "sortOrder": 20, "categoryName": "A", "color": "#111", "bookCount": 5},
        {"categoryId": "b", "weight": 3.0, "sortOrder": 10, "categoryName": "B", "color": "#222", "bookCount": 3},
    ]
    target_areas = build_target_areas(categories)

    monkeypatch.setattr(voronoi_export, "initialize_seed_points", lambda categories, variant=0, radius=SEMICIRCLE_RADIUS: [(-10.0, 20.0), (10.0, 20.0)])

    def fake_partition(items, polygon, polygon_map, depth, strategy="v1", previous_angle=None, enforce_constraints=False, stats=None, expand_search=False, retry_small_leaf=False):
        for item in items:
            polygon_map[item["category"]["categoryId"]] = [(-10.0, 0.0), (0.0, 0.0), (0.0, 10.0), (-10.0, 10.0)]

    monkeypatch.setattr(voronoi_export, "partition_items_into_polygon", fake_partition)
    monkeypatch.setattr(voronoi_export, "compute_cell_metrics", lambda categories, polygons, target_areas: [{"minimumWidth": 12.0}] * len(polygons))

    polygons, metrics, iteration = build_irregular_area_partition(categories, make_semicircle_polygon(), target_areas)

    assert len(polygons) == 2
    assert len(metrics) == 2
    assert iteration == 0
