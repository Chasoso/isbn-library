import json
import uuid
from typing import Any

from botocore.exceptions import ClientError

from shared.auth import get_user_id
from shared.categories import (
    build_category_item,
    category_response,
    list_categories,
    normalize_category_name,
)
from shared.dynamo import get_categories_table
from shared.logging_utils import log_request, log_response
from shared.responses import json_response


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        user_id = get_user_id(event)
        log_request("create_category", event, user_id)
        payload = json.loads(event.get("body") or "{}")
        name = str(payload.get("name", "")).strip()
        color = str(payload.get("color", "")).strip()

        if not name:
            return log_response("create_category", json_response(400, {"message": "Category name is required"}))

        existing = list_categories(user_id)
        normalized_name = normalize_category_name(name)
        if any(item.get("normalizedName") == normalized_name for item in existing):
            return log_response("create_category", json_response(409, {"message": "Category already exists"}))

        sort_order = (
            max((int(item.get("sortOrder", 0)) for item in existing), default=0) + 10
        )
        item = build_category_item(
            user_id=user_id,
            category_id=f"cat_{uuid.uuid4().hex[:10]}",
            name=name,
            sort_order=sort_order,
            color=color,
        )

        get_categories_table().put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(userId) AND attribute_not_exists(categoryId)",
        )
        return log_response("create_category", json_response(201, category_response(item)))
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return log_response("create_category", json_response(409, {"message": "Category already exists"}))
        return log_response("create_category", json_response(500, {"message": f"Failed to create category: {error}"}))
    except Exception as error:
        return log_response("create_category", json_response(500, {"message": f"Failed to create category: {error}"}))
