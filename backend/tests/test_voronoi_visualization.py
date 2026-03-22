from __future__ import annotations

from pathlib import Path
import json

from shared.voronoi_export import (
    SEMICIRCLE_RADIUS,
    build_category_book_counts,
    build_previous_stable_layout,
    build_recursive_binary_partition_details,
    build_recursive_binary_partition_layout,
    build_category_voronoi_rows,
    count_center_shared_polygons,
    summarize_strategy_metrics,
)


def test_category_voronoi_sample_generates_svg_artifact() -> None:
    category_specs = [
        ("manga", "漫画", 0, "#7D91B2"),
        ("novel", "小説", 0, "#A989D8"),
        ("history", "歴史", 1, "#D6B562"),
        ("technical", "技術書", 1, "#5B8AC4"),
        ("server", "サーバ", 1, "#79A9D1"),
        ("javascript", "JavaScript", 1, "#F0C95B"),
        ("community", "コミュニティ", 2, "#B993D6"),
        ("cloud", "クラウド", 2, "#76C7B7"),
        ("linux", "Linux", 2, "#8DB06A"),
        ("ai", "AI", 2, "#EF8F6B"),
        ("statistics", "統計", 3, "#7BB98F"),
        ("network", "ネットワーク", 3, "#6BA3C7"),
        ("hobby", "趣味", 4, "#D993A6"),
        ("programming", "プログラミング", 4, "#6F9CEB"),
        ("database", "データベース", 4, "#55B6AE"),
        ("iot", "IoT", 5, "#9B7FD1"),
        ("english", "英語", 6, "#E4A45F"),
        ("engineer", "エンジニア論", 6, "#6FBA7A"),
        ("other", "その他", 7, "#B7A37B"),
        ("security", "セキュリティ", 7, "#D77474"),
        ("python", "Python", 7, "#4E9BDA"),
        ("certification", "資格試験", 10, "#8A92D1"),
        ("design", "デザイン", 13, "#73C995"),
        ("data-science", "データサイエンス", 13, "#61A7C4"),
        ("business", "ビジネス", 19, "#E05B5B"),
    ]

    category_items = [
        {
            "userId": "user-123",
            "categoryId": category_id,
            "name": category_name,
            "sortOrder": (index + 1) * 10,
            "color": color,
        }
        for index, (category_id, category_name, _, color) in enumerate(category_specs)
    ]

    book_items = [
        {
            "userId": "user-123",
            "categoryId": category_id,
            "isbn": f"{category_id}-{index}",
        }
        for category_id, _, book_count, _ in category_specs
        for index in range(book_count)
    ]

    rows = build_category_voronoi_rows(category_items, book_items)
    categories = [
        category
        for category in build_category_book_counts(category_items, book_items)
        if category["bookCount"] > 0
    ]
    previous_polygons, previous_metrics, _ = build_previous_stable_layout(categories)
    recursive_polygons, recursive_metrics, _, recursive_stats = build_recursive_binary_partition_details(categories)
    recursive_summary = summarize_strategy_metrics(categories, recursive_polygons, recursive_metrics)
    previous_summary = summarize_strategy_metrics(categories, previous_polygons, previous_metrics)
    comparison = {
        "previous_stable_version": previous_summary,
        "recursive_binary_partition_version": {
            **recursive_summary,
            "grouping_candidate_count": float(recursive_stats["grouping_candidate_count"]),
            "split_candidate_count": float(recursive_stats["split_candidate_count"]),
            "feasible_candidate_count": float(recursive_stats["feasible_candidate_count"]),
            "rejected_candidate_count": float(recursive_stats["rejected_candidate_count"]),
            "fallback_used_count": float(recursive_stats["fallback_used_count"]),
            "fallback_leaf_sliver_count": float(recursive_stats["fallback_leaf_sliver_count"]),
            "recursion_depth_max": float(recursive_stats["recursion_depth_max"]),
            "accepted": bool(recursive_stats["accepted"]) and (
                recursive_summary["minimum_width_min"] >= previous_summary["minimum_width_min"]
                and recursive_summary["sliver_cell_count"] <= previous_summary["sliver_cell_count"]
                and recursive_summary["labelable_cell_count"] >= previous_summary["labelable_cell_count"]
                and recursive_summary["label_overlap_count"] <= previous_summary["label_overlap_count"]
            ),
        },
    }
    polygons = _group_polygons(rows[1:])
    expected_non_zero_categories = {
        category_name
        for _, category_name, book_count, _ in category_specs
        if book_count > 0
    }

    assert len(polygons) == len(expected_non_zero_categories)
    assert all(len(polygon["points"]) >= 4 for polygon in polygons.values())
    assert {polygon["categoryName"] for polygon in polygons.values()} == expected_non_zero_categories
    assert "漫画" not in {polygon["categoryName"] for polygon in polygons.values()}
    assert "小説" not in {polygon["categoryName"] for polygon in polygons.values()}
    assert count_center_shared_polygons([polygon["points"] for polygon in polygons.values()]) <= 2

    for polygon in polygons.values():
        for x, y in polygon["points"]:
            assert y >= -0.01
            assert (x * x) + (y * y) <= (SEMICIRCLE_RADIUS + 0.25) ** 2

    output_path = Path(__file__).resolve().parents[1] / "test-results" / "voronoi-sample.svg"
    current_output_path = Path(__file__).resolve().parents[1] / "test-results" / "voronoi-current-sample.svg"
    new_output_path = Path(__file__).resolve().parents[1] / "test-results" / "voronoi-new-sample.svg"
    comparison_path = Path(__file__).resolve().parents[1] / "test-results" / "voronoi-strategy-comparison.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_svg(polygons), encoding="utf-8")
    current_output_path.write_text(
        _render_svg(_build_polygons_from_layout(categories, previous_polygons, previous_metrics)),
        encoding="utf-8",
    )
    previous_output_path = Path(__file__).resolve().parents[1] / "test-results" / "voronoi-previous-stable-sample.svg"
    previous_output_path.write_text(
        _render_svg(_build_polygons_from_layout(categories, previous_polygons, previous_metrics)),
        encoding="utf-8",
    )
    new_output_path.write_text(
        _render_svg(_build_polygons_from_layout(categories, recursive_polygons, recursive_metrics)),
        encoding="utf-8",
    )
    comparison_path.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    assert output_path.exists()
    assert current_output_path.exists()
    assert previous_output_path.exists()
    assert new_output_path.exists()
    assert comparison_path.exists()
    assert output_path.read_text(encoding="utf-8").startswith("<svg")
    assert "elongation_mean" in comparison["previous_stable_version"]
    assert "elongation_max" in comparison["recursive_binary_partition_version"]
    assert "min_thickness_mean" in comparison["recursive_binary_partition_version"]
    assert "min_thickness_min" in comparison["recursive_binary_partition_version"]


def _build_polygons_from_layout(
    categories: list[dict[str, object]],
    polygons: list[list[tuple[float, float]]],
    metrics: list[dict[str, float]],
) -> dict[str, dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for category, polygon, metric in zip(categories, polygons, metrics, strict=False):
        grouped[f"category-{category['categoryId']}"] = {
            "categoryName": str(category["categoryName"]),
            "color": str(category["color"]) or "#7aa7c7",
            "centroidX": float(metric["centroidX"]),
            "centroidY": float(metric["centroidY"]),
            "points": polygon,
        }
    return grouped


def _group_polygons(rows: list[list[object]]) -> dict[str, dict[str, object]]:
    polygons: dict[str, dict[str, object]] = {}
    for row in rows:
        polygon_id = str(row[0])
        polygons.setdefault(
            polygon_id,
            {
                "categoryName": str(row[2]),
                "color": str(row[3]) or "#7aa7c7",
                "centroidX": float(row[20]),
                "centroidY": float(row[21]),
                "points": [],
            },
        )
        polygons[polygon_id]["points"].append((float(row[17]), float(row[18])))

    return polygons


def _render_svg(polygons: dict[str, dict[str, object]]) -> str:
    size = 420
    margin = 16
    diameter = (SEMICIRCLE_RADIUS * 2) + margin * 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size // 2 + margin * 2}" viewBox="0 0 {diameter} {SEMICIRCLE_RADIUS + margin * 2}">',
        '<rect width="100%" height="100%" fill="#f6f8fd"/>',
        f'<path d="M {margin} {SEMICIRCLE_RADIUS + margin} A {SEMICIRCLE_RADIUS} {SEMICIRCLE_RADIUS} 0 0 1 {margin + SEMICIRCLE_RADIUS * 2} {SEMICIRCLE_RADIUS + margin} L {margin} {SEMICIRCLE_RADIUS + margin} Z" fill="#ffffff" stroke="#cfd8e3" stroke-width="1.2"/>',
    ]

    for polygon in polygons.values():
        points = " ".join(
            f"{margin + x + SEMICIRCLE_RADIUS:.2f},{margin + SEMICIRCLE_RADIUS - y:.2f}"
            for x, y in polygon["points"]
        )
        centroid_x = margin + float(polygon["centroidX"]) + SEMICIRCLE_RADIUS
        centroid_y = margin + SEMICIRCLE_RADIUS - float(polygon["centroidY"])
        parts.append(
            f'<polygon points="{points}" fill="{polygon["color"]}" fill-opacity="0.72" stroke="#ffffff" stroke-width="1.6"/>'
        )
        parts.append(
            f'<text x="{centroid_x:.2f}" y="{centroid_y:.2f}" text-anchor="middle" font-size="7" fill="#173042">{polygon["categoryName"]}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)
