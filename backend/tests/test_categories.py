from __future__ import annotations

import json
from unittest.mock import Mock, patch

from conftest import load_handler_module, parse_response


get_categories_handler = load_handler_module("get_categories")
create_category_handler = load_handler_module("create_category")
update_category_handler = load_handler_module("update_category")


def test_get_categories_returns_items(lambda_event: dict[str, object]) -> None:
    with patch.object(
        get_categories_handler,
        "list_categories",
        return_value=[{"categoryId": "technology", "name": "技術書", "sortOrder": 10}],
    ):
        status_code, body = parse_response(get_categories_handler.handler(lambda_event, None))

    assert status_code == 200
    assert body["items"][0]["categoryId"] == "technology"


def test_create_category_success(lambda_event: dict[str, object]) -> None:
    table = Mock()
    lambda_event["body"] = json.dumps({"name": "データ分析"}, ensure_ascii=False)

    with (
        patch.object(create_category_handler, "get_categories_table", return_value=table),
        patch.object(create_category_handler, "list_categories", return_value=[]),
    ):
        status_code, body = parse_response(create_category_handler.handler(lambda_event, None))

    assert status_code == 201
    assert body["name"] == "データ分析"
    table.put_item.assert_called_once()


def test_create_category_returns_409_for_duplicate_name(lambda_event: dict[str, object]) -> None:
    lambda_event["body"] = json.dumps({"name": "技術書"}, ensure_ascii=False)

    with patch.object(
        create_category_handler,
        "list_categories",
        return_value=[{"categoryId": "technology", "normalizedName": "技術書"}],
    ):
        status_code, body = parse_response(create_category_handler.handler(lambda_event, None))

    assert status_code == 409
    assert body["message"] == "Category already exists"


def test_update_category_success(lambda_event: dict[str, object]) -> None:
    table = Mock()
    table.update_item.return_value = {
        "Attributes": {
            "categoryId": "technology",
            "name": "技術・IT",
            "sortOrder": 10,
        }
    }
    lambda_event["pathParameters"] = {"categoryId": "technology"}
    lambda_event["body"] = json.dumps({"name": "技術・IT"}, ensure_ascii=False)

    with (
        patch.object(update_category_handler, "get_categories_table", return_value=table),
        patch.object(
            update_category_handler,
            "list_categories",
            return_value=[{"categoryId": "technology", "normalizedName": "技術書"}],
        ),
    ):
        status_code, body = parse_response(update_category_handler.handler(lambda_event, None))

    assert status_code == 200
    assert body["name"] == "技術・IT"
