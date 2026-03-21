from typing import Any

from shared.auth import get_user_id
from shared.categories import category_response, list_categories
from shared.responses import json_response


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        user_id = get_user_id(event)
        items = list_categories(user_id)
        return json_response(200, {"items": [category_response(item) for item in items]})
    except Exception as error:
        return json_response(500, {"message": f"Failed to list categories: {error}"})
