from typing import Any

from shared.auth import get_user_id
from shared.books import to_book_response
from shared.categories import get_category
from shared.dynamo import get_books_table
from shared.isbn import normalize_isbn
from shared.responses import json_response


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        user_id = get_user_id(event)
        raw_isbn = (event.get("pathParameters") or {}).get("isbn", "")
        isbn = normalize_isbn(raw_isbn)

        if not isbn:
            return json_response(400, {"message": "Invalid ISBN"})

        table = get_books_table()
        result = table.get_item(Key={"userId": user_id, "isbn": isbn})
        item = result.get("Item")

        if not item:
            return json_response(404, {"message": "Book not found"})

        category = get_category(user_id, item.get("categoryId", ""))
        return json_response(
            200,
            to_book_response(item, category_name=category["name"] if category else None),
        )
    except Exception as error:
        return json_response(500, {"message": f"Failed to get book: {error}"})
