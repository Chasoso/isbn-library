from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from boto3.dynamodb.conditions import Key

from .catalog import DEFAULT_CATEGORIES, DEFAULT_CATEGORY_ID, DEFAULT_CATEGORY_NAME
from .dynamo import get_categories_table


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_category_name(value: str) -> str:
    return " ".join(value.strip().lower().split())


def category_sort_key(item: dict[str, Any]) -> tuple[int, str]:
    return (int(item.get("sortOrder", 9999)), item.get("name", ""))


def build_category_item(
    user_id: str,
    category_id: str,
    name: str,
    name_en: str,
    sort_order: int,
    color: str = "",
    timestamp: str | None = None,
) -> dict[str, Any]:
    current = timestamp or now_iso()
    return {
        "userId": user_id,
        "categoryId": category_id,
        "name": name,
        "nameEn": name_en.strip(),
        "normalizedName": normalize_category_name(name),
        "sortOrder": sort_order,
        "color": color,
        "createdAt": current,
        "updatedAt": current,
    }


def ensure_default_categories(user_id: str) -> list[dict[str, Any]]:
    table = get_categories_table()
    result = table.query(KeyConditionExpression=Key("userId").eq(user_id))
    items = result.get("Items", [])
    if items:
        return sorted(items, key=category_sort_key)

    timestamp = now_iso()
    seeded_items = [
        build_category_item(
            user_id=user_id,
            category_id=category["categoryId"],
            name=category["name"],
            name_en=category.get("nameEn", ""),
            sort_order=category["sortOrder"],
            color=category.get("color", ""),
            timestamp=timestamp,
        )
        for category in DEFAULT_CATEGORIES
    ]

    with table.batch_writer() as batch:
        for item in seeded_items:
            batch.put_item(Item=item)

    return seeded_items


def list_categories(user_id: str) -> list[dict[str, Any]]:
    return ensure_default_categories(user_id)


def get_categories_by_id(user_id: str) -> dict[str, dict[str, Any]]:
    return {item["categoryId"]: item for item in list_categories(user_id)}


def get_category(user_id: str, category_id: str) -> dict[str, Any] | None:
    return get_categories_by_id(user_id).get(category_id)


def category_response(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "categoryId": item["categoryId"],
        "name": item.get("name", DEFAULT_CATEGORY_NAME),
        "nameEn": item.get("nameEn", ""),
        "sortOrder": int(item.get("sortOrder", 0)),
        "color": item.get("color", ""),
        "createdAt": item.get("createdAt", ""),
        "updatedAt": item.get("updatedAt", ""),
    }


def get_default_category() -> dict[str, str]:
    return {"categoryId": DEFAULT_CATEGORY_ID, "name": DEFAULT_CATEGORY_NAME}
