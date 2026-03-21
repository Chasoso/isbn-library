from typing import Any

from boto3.dynamodb.conditions import Key

from shared.auth import get_user_id
from shared.books import to_book_response
from shared.catalog import DEFAULT_BOOK_FORMAT
from shared.categories import get_categories_by_id
from shared.dynamo import get_books_table
from shared.logging_utils import log_request, log_response
from shared.responses import json_response
from shared.statuses import DEFAULT_READING_STATUS


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        user_id = get_user_id(event)
        log_request("get_books", event, user_id)
        query_params = event.get("queryStringParameters") or {}
        query_text = (query_params.get("q") or "").strip().lower()
        book_format = (query_params.get("bookFormat") or "").strip()
        category_id = (query_params.get("categoryId") or "").strip()
        reading_status = (query_params.get("readingStatus") or "").strip()

        table = get_books_table()
        result = table.query(KeyConditionExpression=Key("userId").eq(user_id))
        items = result.get("Items", [])

        if query_text:
            items = [
                item
                for item in items
                if query_text in item.get("title", "").lower()
                or query_text in item.get("author", "").lower()
            ]

        if book_format:
            items = [
                item
                for item in items
                if item.get("bookFormat", DEFAULT_BOOK_FORMAT) == book_format
            ]

        if category_id:
            items = [
                item
                for item in items
                if item.get("categoryId", "") == category_id
            ]

        if reading_status:
            items = [
                item
                for item in items
                if item.get("readingStatus", DEFAULT_READING_STATUS) == reading_status
            ]

        items = sorted(items, key=lambda item: item.get("createdAt", ""), reverse=True)
        categories_by_id = get_categories_by_id(user_id)

        return log_response(
            "get_books",
            json_response(
                200,
                {
                    "items": [
                        to_book_response(
                            item,
                            category_name=categories_by_id.get(item.get("categoryId", ""), {}).get("name"),
                        )
                        for item in items
                    ]
                },
            ),
        )
    except Exception as error:
        return log_response("get_books", json_response(500, {"message": f"Failed to list books: {error}"}))
