from typing import Any

from shared.catalog import DEFAULT_BOOK_FORMAT, DEFAULT_CATEGORY_ID, DEFAULT_CATEGORY_NAME
from shared.statuses import DEFAULT_READING_STATUS


def to_book_response(
    item: dict[str, Any],
    category_name: str | None = None,
) -> dict[str, Any]:
    resolved_category_id = item.get("categoryId", DEFAULT_CATEGORY_ID)
    resolved_category_name = (
        category_name
        or item.get("categoryName")
        or item.get("category")
        or DEFAULT_CATEGORY_NAME
    )

    return {
        "userId": item["userId"],
        "isbn": item["isbn"],
        "title": item.get("title", ""),
        "author": item.get("author", ""),
        "publisher": item.get("publisher", ""),
        "publishedDate": item.get("publishedDate", ""),
        "coverImageUrl": item.get("coverImageUrl", ""),
        "bookFormat": item.get("bookFormat", DEFAULT_BOOK_FORMAT),
        "categoryId": resolved_category_id,
        "categoryName": resolved_category_name,
        "readingStatus": item.get("readingStatus", DEFAULT_READING_STATUS),
        "createdAt": item.get("createdAt", ""),
    }
