from typing import Any

from shared.auth import get_user_id
from shared.dynamo import get_books_table
from shared.isbn import normalize_isbn
from shared.logging_utils import log_request, log_response
from shared.responses import empty_response, json_response


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        user_id = get_user_id(event)
        log_request("delete_book", event, user_id)
        raw_isbn = (event.get("pathParameters") or {}).get("isbn", "")
        isbn = normalize_isbn(raw_isbn)

        if not isbn:
            return log_response("delete_book", json_response(400, {"message": "Invalid ISBN"}))

        table = get_books_table()
        table.delete_item(Key={"userId": user_id, "isbn": isbn})
        return log_response("delete_book", empty_response())
    except Exception as error:
        return log_response("delete_book", json_response(500, {"message": f"Failed to delete book: {error}"}))
