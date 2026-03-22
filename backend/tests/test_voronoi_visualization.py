from __future__ import annotations

from pathlib import Path

from shared.voronoi_export import (
    SEMICIRCLE_RADIUS,
    build_category_voronoi_rows,
    count_center_shared_polygons,
)


def test_category_voronoi_sample_generates_svg_artifact() -> None:
    category_items = [
        {
            "userId": "user-123",
            "categoryId": "technology",
            "name": "Technology",
            "sortOrder": 10,
            "color": "#4C8BF5",
        },
        {
            "userId": "user-123",
            "categoryId": "business",
            "name": "Business",
            "sortOrder": 20,
            "color": "#F28C6C",
        },
        {
            "userId": "user-123",
            "categoryId": "design",
            "name": "Design",
            "sortOrder": 30,
            "color": "#6FCF97",
        },
        {
            "userId": "user-123",
            "categoryId": "novel",
            "name": "Novel",
            "sortOrder": 40,
            "color": "#BB8AE8",
        },
        {
            "userId": "user-123",
            "categoryId": "history",
            "name": "History",
            "sortOrder": 50,
            "color": "#E0B35A",
        },
    ]

    book_items = (
        [{"userId": "user-123", "categoryId": "technology", "isbn": f"tech-{index}"} for index in range(12)]
        + [{"userId": "user-123", "categoryId": "business", "isbn": f"biz-{index}"} for index in range(8)]
        + [{"userId": "user-123", "categoryId": "design", "isbn": f"design-{index}"} for index in range(5)]
        + [{"userId": "user-123", "categoryId": "novel", "isbn": f"novel-{index}"} for index in range(3)]
        + [{"userId": "user-123", "categoryId": "history", "isbn": "history-0"}]
    )

    rows = build_category_voronoi_rows(category_items, book_items)
    polygons = _group_polygons(rows[1:])

    assert len(polygons) == 5
    assert all(len(polygon["points"]) >= 4 for polygon in polygons.values())
    assert count_center_shared_polygons([polygon["points"] for polygon in polygons.values()]) == 0

    for polygon in polygons.values():
      for x, y in polygon["points"]:
        assert y >= -0.01
        assert (x * x) + (y * y) <= (SEMICIRCLE_RADIUS + 0.25) ** 2

    output_path = Path(__file__).resolve().parents[1] / "test-results" / "voronoi-sample.svg"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_svg(polygons), encoding="utf-8")

    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").startswith("<svg")


def _group_polygons(rows: list[list[object]]) -> dict[str, dict[str, object]]:
    polygons: dict[str, dict[str, object]] = {}
    for row in rows:
        polygon_id = str(row[0])
        polygons.setdefault(
            polygon_id,
            {
                "categoryName": str(row[2]),
                "color": str(row[3]) or "#7aa7c7",
                "centroidX": float(row[15]),
                "centroidY": float(row[16]),
                "points": [],
            },
        )
        polygons[polygon_id]["points"].append((float(row[12]), float(row[13])))

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
