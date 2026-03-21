import json
from typing import Any

from botocore.exceptions import ClientError

from shared.auth import get_user_id
from shared.books import to_book_response
from shared.categories import get_category
from shared.dynamo import get_books_table
from shared.isbn import normalize_isbn
from shared.logging_utils import log_request, log_response
from shared.responses import json_response
from shared.statuses import READING_STATUSES


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        user_id = get_user_id(event)
        log_request("update_book_status", event, user_id)
        raw_isbn = (event.get("pathParameters") or {}).get("isbn", "")
        isbn = normalize_isbn(raw_isbn)
        payload = json.loads(event.get("body") or "{}")
        reading_status = str(payload.get("readingStatus", "")).strip()

        if not isbn:
            return log_response("update_book_status", json_response(400, {"message": "Invalid ISBN"}))

        if reading_status not in READING_STATUSES:
            return log_response("update_book_status", json_response(400, {"message": "Invalid readingStatus"}))

        table = get_books_table()
        result = table.update_item(
            Key={"userId": user_id, "isbn": isbn},
            UpdateExpression="SET readingStatus = :readingStatus",
            ExpressionAttributeValues={":readingStatus": reading_status},
            ConditionExpression="attribute_exists(userId) AND attribute_exists(isbn)",
            ReturnValues="ALL_NEW",
        )
        item = result.get("Attributes", {})
        category = get_category(user_id, item.get("categoryId", ""))
        return log_response(
            "update_book_status",
            json_response(
                200,
                to_book_response(item, category_name=category["name"] if category else None),
            ),
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return log_response("update_book_status", json_response(404, {"message": "Book not found"}))
        return log_response("update_book_status", json_response(500, {"message": f"Failed to update reading status: {error}"}))
    except Exception as error:
        return log_response("update_book_status", json_response(500, {"message": f"Failed to update reading status: {error}"}))
