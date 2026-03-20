from datetime import datetime, timezone
import json
from typing import Any

from botocore.exceptions import ClientError

from shared.auth import get_user_id
from shared.catalog import (
    BOOK_FORMATS,
    CATEGORIES,
    DEFAULT_BOOK_FORMAT,
    DEFAULT_CATEGORY,
)
from shared.dynamo import get_books_table
from shared.isbn import normalize_isbn
from shared.responses import json_response
from shared.statuses import DEFAULT_READING_STATUS, READING_STATUSES


def build_item(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "userId": user_id,
        "isbn": payload["isbn"],
        "title": payload.get("title", ""),
        "author": payload.get("author", ""),
        "publisher": payload.get("publisher", ""),
        "publishedDate": payload.get("publishedDate", ""),
        "coverImageUrl": payload.get("coverImageUrl", ""),
        "bookFormat": payload.get("bookFormat", DEFAULT_BOOK_FORMAT),
        "category": payload.get("category", DEFAULT_CATEGORY),
        "readingStatus": payload.get("readingStatus", DEFAULT_READING_STATUS),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        user_id = get_user_id(event)
        payload = json.loads(event.get("body") or "{}")
        isbn = normalize_isbn(str(payload.get("isbn", "")))

        if not isbn:
            return json_response(400, {"message": "Invalid ISBN"})

        book_format = str(payload.get("bookFormat", DEFAULT_BOOK_FORMAT))
        category = str(payload.get("category", DEFAULT_CATEGORY))
        reading_status = str(payload.get("readingStatus", DEFAULT_READING_STATUS))

        if book_format not in BOOK_FORMATS:
            return json_response(400, {"message": "Invalid bookFormat"})

        if category not in CATEGORIES:
            return json_response(400, {"message": "Invalid category"})

        if reading_status not in READING_STATUSES:
            return json_response(400, {"message": "Invalid readingStatus"})

        payload["isbn"] = isbn
        payload["bookFormat"] = book_format
        payload["category"] = category
        payload["readingStatus"] = reading_status
        item = build_item(user_id, payload)

        table = get_books_table()
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(userId) AND attribute_not_exists(isbn)",
        )
        return json_response(201, item)
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return json_response(409, {"message": "Book already exists"})
        return json_response(500, {"message": f"Failed to create book: {error}"})
    except Exception as error:
        return json_response(500, {"message": f"Failed to create book: {error}"})
