from typing import Any

from boto3.dynamodb.conditions import Key

from shared.auth import get_user_id
from shared.books import to_book_response
from shared.dynamo import get_books_table
from shared.responses import json_response


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        user_id = get_user_id(event)
        query_params = event.get("queryStringParameters") or {}
        query_text = (query_params.get("q") or "").strip().lower()
        book_format = (query_params.get("bookFormat") or "").strip()
        category = (query_params.get("category") or "").strip()

        table = get_books_table()
        result = table.query(
            KeyConditionExpression=Key("userId").eq(user_id),
        )
        items = result.get("Items", [])

        if query_text:
            items = [
                item for item in items if query_text in item.get("title", "").lower()
            ]

        if book_format:
            items = [
                item for item in items if item.get("bookFormat", "その他") == book_format
            ]

        if category:
            items = [
                item for item in items if item.get("category", "その他") == category
            ]

        items = sorted(items, key=lambda item: item.get("createdAt", ""), reverse=True)

        return json_response(200, {"items": [to_book_response(item) for item in items]})
    except Exception as error:
        return json_response(500, {"message": f"Failed to list books: {error}"})
