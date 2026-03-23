from __future__ import annotations

import json
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from conftest import load_handler_module, parse_response
from shared.catalog import DEFAULT_CATEGORIES, DEFAULT_CATEGORY_ID, DEFAULT_CATEGORY_NAME
from shared.categories import (
    build_category_item,
    category_response,
    category_sort_key,
    ensure_default_categories,
    get_categories_by_id,
    get_default_category,
    normalize_category_name,
)


get_categories_handler = load_handler_module("get_categories")
create_category_handler = load_handler_module("create_category")
update_category_handler = load_handler_module("update_category")


def test_normalize_category_name_collapses_whitespace_and_case() -> None:
    assert normalize_category_name("  Data   Science  ") == "data science"


def test_build_category_item_uses_timestamp_and_normalized_name() -> None:
    item = build_category_item(
        user_id="user-123",
        category_id="cat-1",
        name="  Data   Science  ",
        sort_order=10,
        color="#123456",
        timestamp="2026-03-23T00:00:00+00:00",
    )

    assert item == {
        "userId": "user-123",
        "categoryId": "cat-1",
        "name": "  Data   Science  ",
        "normalizedName": "data science",
        "sortOrder": 10,
        "color": "#123456",
        "createdAt": "2026-03-23T00:00:00+00:00",
        "updatedAt": "2026-03-23T00:00:00+00:00",
    }


def test_ensure_default_categories_seeds_defaults_when_empty() -> None:
    table = Mock()
    batch = Mock()
    table.query.return_value = {"Items": []}
    batch_writer = Mock()
    batch_writer.__enter__ = Mock(return_value=batch)
    batch_writer.__exit__ = Mock(return_value=None)
    table.batch_writer.return_value = batch_writer

    with (
        patch("shared.categories.get_categories_table", return_value=table),
        patch("shared.categories.now_iso", return_value="2026-03-23T00:00:00+00:00"),
    ):
        items = ensure_default_categories("user-123")

    assert len(items) == len(DEFAULT_CATEGORIES)
    assert batch.put_item.call_count == len(DEFAULT_CATEGORIES)
    first_seeded = batch.put_item.call_args_list[0].kwargs["Item"]
    assert first_seeded["userId"] == "user-123"
    assert first_seeded["createdAt"] == "2026-03-23T00:00:00+00:00"


def test_ensure_default_categories_returns_sorted_existing_items() -> None:
    table = Mock()
    table.query.return_value = {
        "Items": [
            {"categoryId": "b", "name": "Z", "sortOrder": 20},
            {"categoryId": "a", "name": "A", "sortOrder": 10},
            {"categoryId": "c", "name": "B", "sortOrder": 20},
        ]
    }

    with patch("shared.categories.get_categories_table", return_value=table):
        items = ensure_default_categories("user-123")

    assert [item["categoryId"] for item in items] == ["a", "c", "b"]


def test_get_categories_by_id_and_default_category() -> None:
    with patch(
        "shared.categories.list_categories",
        return_value=[{"categoryId": "technology", "name": "Tech", "sortOrder": 10}],
    ):
        items_by_id = get_categories_by_id("user-123")

    assert items_by_id["technology"]["name"] == "Tech"
    assert get_default_category() == {"categoryId": DEFAULT_CATEGORY_ID, "name": DEFAULT_CATEGORY_NAME}


def test_category_response_uses_defaults() -> None:
    response = category_response({"categoryId": "other"})

    assert response["categoryId"] == "other"
    assert response["name"] == DEFAULT_CATEGORY_NAME
    assert response["sortOrder"] == 0
    assert response["color"] == ""


def test_category_sort_key_uses_sort_order_then_name() -> None:
    assert category_sort_key({"sortOrder": 20, "name": "B"}) > category_sort_key({"sortOrder": 10, "name": "Z"})


def test_get_categories_returns_items(lambda_event: dict[str, object]) -> None:
    with patch.object(
        get_categories_handler,
        "list_categories",
        return_value=[{"categoryId": "technology", "name": "謚陦捺嶌", "sortOrder": 10}],
    ):
        status_code, body = parse_response(get_categories_handler.handler(lambda_event, None))

    assert status_code == 200
    assert body["items"][0]["categoryId"] == "technology"


def test_create_category_success(lambda_event: dict[str, object]) -> None:
    table = Mock()
    lambda_event["body"] = json.dumps({"name": "繝・・繧ｿ蛻・梵"}, ensure_ascii=False)

    with (
        patch.object(create_category_handler, "get_categories_table", return_value=table),
        patch.object(create_category_handler, "list_categories", return_value=[]),
    ):
        status_code, body = parse_response(create_category_handler.handler(lambda_event, None))

    assert status_code == 201
    assert body["name"] == "繝・・繧ｿ蛻・梵"
    table.put_item.assert_called_once()


def test_create_category_requires_name(lambda_event: dict[str, object]) -> None:
    lambda_event["body"] = json.dumps({"name": "   "}, ensure_ascii=False)

    status_code, body = parse_response(create_category_handler.handler(lambda_event, None))

    assert status_code == 400
    assert body["message"] == "Category name is required"


def test_create_category_returns_409_for_duplicate_name(lambda_event: dict[str, object]) -> None:
    lambda_event["body"] = json.dumps({"name": "謚陦捺嶌"}, ensure_ascii=False)

    with patch.object(
        create_category_handler,
        "list_categories",
        return_value=[{"categoryId": "technology", "normalizedName": "謚陦捺嶌"}],
    ):
        status_code, body = parse_response(create_category_handler.handler(lambda_event, None))

    assert status_code == 409
    assert body["message"] == "Category already exists"


def test_create_category_returns_409_for_conditional_duplicate(lambda_event: dict[str, object]) -> None:
    table = Mock()
    table.put_item.side_effect = ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "duplicate"}},
        "PutItem",
    )
    lambda_event["body"] = json.dumps({"name": "新カテゴリ"}, ensure_ascii=False)

    with (
        patch.object(create_category_handler, "get_categories_table", return_value=table),
        patch.object(create_category_handler, "list_categories", return_value=[]),
    ):
        status_code, body = parse_response(create_category_handler.handler(lambda_event, None))

    assert status_code == 409
    assert body["message"] == "Category already exists"


def test_create_category_returns_500_for_unexpected_client_error(lambda_event: dict[str, object]) -> None:
    table = Mock()
    table.put_item.side_effect = ClientError(
        {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "boom"}},
        "PutItem",
    )
    lambda_event["body"] = json.dumps({"name": "新カテゴリ"}, ensure_ascii=False)

    with (
        patch.object(create_category_handler, "get_categories_table", return_value=table),
        patch.object(create_category_handler, "list_categories", return_value=[]),
    ):
        status_code, body = parse_response(create_category_handler.handler(lambda_event, None))

    assert status_code == 500
    assert "Failed to create category" in body["message"]


def test_update_category_success(lambda_event: dict[str, object]) -> None:
    table = Mock()
    table.update_item.return_value = {
        "Attributes": {
            "categoryId": "technology",
            "name": "謚陦薙・IT",
            "sortOrder": 10,
        }
    }
    lambda_event["pathParameters"] = {"categoryId": "technology"}
    lambda_event["body"] = json.dumps({"name": "謚陦薙・IT"}, ensure_ascii=False)

    with (
        patch.object(update_category_handler, "get_categories_table", return_value=table),
        patch.object(
            update_category_handler,
            "list_categories",
            return_value=[{"categoryId": "technology", "normalizedName": "謚陦捺嶌"}],
        ),
    ):
        status_code, body = parse_response(update_category_handler.handler(lambda_event, None))

    assert status_code == 200
    assert body["name"] == "謚陦薙・IT"


def test_update_category_requires_category_id(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"categoryId": "   "}
    lambda_event["body"] = json.dumps({"name": "updated"}, ensure_ascii=False)

    status_code, body = parse_response(update_category_handler.handler(lambda_event, None))

    assert status_code == 400
    assert body["message"] == "Invalid categoryId"


def test_update_category_requires_non_blank_name(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"categoryId": "technology"}
    lambda_event["body"] = json.dumps({"name": "   "}, ensure_ascii=False)

    status_code, body = parse_response(update_category_handler.handler(lambda_event, None))

    assert status_code == 400
    assert body["message"] == "Category name is required"


def test_update_category_rejects_invalid_sort_order(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"categoryId": "technology"}
    lambda_event["body"] = json.dumps({"sortOrder": "abc"}, ensure_ascii=False)

    status_code, body = parse_response(update_category_handler.handler(lambda_event, None))

    assert status_code == 400
    assert body["message"] == "Invalid sortOrder"


def test_update_category_requires_fields_to_update(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"categoryId": "technology"}
    lambda_event["body"] = json.dumps({}, ensure_ascii=False)

    status_code, body = parse_response(update_category_handler.handler(lambda_event, None))

    assert status_code == 400
    assert body["message"] == "No fields to update"


def test_update_category_returns_409_for_duplicate_name(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"categoryId": "technology"}
    lambda_event["body"] = json.dumps({"name": "重複名"}, ensure_ascii=False)

    with patch.object(
        update_category_handler,
        "list_categories",
        return_value=[
            {"categoryId": "technology", "normalizedName": "technology"},
            {"categoryId": "business", "normalizedName": "重複名"},
        ],
    ):
        status_code, body = parse_response(update_category_handler.handler(lambda_event, None))

    assert status_code == 409
    assert body["message"] == "Category already exists"


def test_update_category_returns_404_for_missing_category(lambda_event: dict[str, object]) -> None:
    table = Mock()
    table.update_item.side_effect = ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "missing"}},
        "UpdateItem",
    )
    lambda_event["pathParameters"] = {"categoryId": "technology"}
    lambda_event["body"] = json.dumps({"color": "#123456"}, ensure_ascii=False)

    with patch.object(update_category_handler, "get_categories_table", return_value=table):
        status_code, body = parse_response(update_category_handler.handler(lambda_event, None))

    assert status_code == 404
    assert body["message"] == "Category not found"


def test_update_category_returns_500_for_unexpected_client_error(lambda_event: dict[str, object]) -> None:
    table = Mock()
    table.update_item.side_effect = ClientError(
        {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "boom"}},
        "UpdateItem",
    )
    lambda_event["pathParameters"] = {"categoryId": "technology"}
    lambda_event["body"] = json.dumps({"color": "#123456"}, ensure_ascii=False)

    with patch.object(update_category_handler, "get_categories_table", return_value=table):
        status_code, body = parse_response(update_category_handler.handler(lambda_event, None))

    assert status_code == 500
    assert "Failed to update category" in body["message"]
