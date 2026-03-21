import json
from datetime import datetime, timezone
from typing import Any

from botocore.exceptions import ClientError

from shared.auth import get_user_id
from shared.categories import category_response, list_categories, normalize_category_name
from shared.dynamo import get_categories_table
from shared.responses import json_response


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        user_id = get_user_id(event)
        category_id = ((event.get("pathParameters") or {}).get("categoryId") or "").strip()
        payload = json.loads(event.get("body") or "{}")

        if not category_id:
            return json_response(400, {"message": "Invalid categoryId"})

        updates: list[str] = []
        values: dict[str, Any] = {}

        name = payload.get("name")
        if name is not None:
            trimmed_name = str(name).strip()
            if not trimmed_name:
                return json_response(400, {"message": "Category name is required"})

            normalized_name = normalize_category_name(trimmed_name)
            existing = list_categories(user_id)
            if any(
                item["categoryId"] != category_id
                and item.get("normalizedName") == normalized_name
                for item in existing
            ):
                return json_response(409, {"message": "Category already exists"})

            updates.extend(["#name = :name", "normalizedName = :normalizedName"])
            values[":name"] = trimmed_name
            values[":normalizedName"] = normalized_name

        if "color" in payload:
            updates.append("color = :color")
            values[":color"] = str(payload.get("color", "")).strip()

        if "sortOrder" in payload:
            try:
                sort_order = int(payload.get("sortOrder", 0))
            except (TypeError, ValueError):
                return json_response(400, {"message": "Invalid sortOrder"})
            updates.append("sortOrder = :sortOrder")
            values[":sortOrder"] = sort_order

        if not updates:
            return json_response(400, {"message": "No fields to update"})

        updates.append("updatedAt = :updatedAt")
        values[":updatedAt"] = datetime.now(timezone.utc).isoformat()

        result = get_categories_table().update_item(
            Key={"userId": user_id, "categoryId": category_id},
            UpdateExpression=f"SET {', '.join(updates)}",
            ExpressionAttributeNames={"#name": "name"},
            ExpressionAttributeValues=values,
            ConditionExpression="attribute_exists(userId) AND attribute_exists(categoryId)",
            ReturnValues="ALL_NEW",
        )
        return json_response(200, category_response(result.get("Attributes", {})))
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return json_response(404, {"message": "Category not found"})
        return json_response(500, {"message": f"Failed to update category: {error}"})
    except Exception as error:
        return json_response(500, {"message": f"Failed to update category: {error}"})
