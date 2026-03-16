from typing import Any

from shared.catalog import DEFAULT_BOOK_FORMAT, DEFAULT_CATEGORY


def to_book_response(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "userId": item["userId"],
        "isbn": item["isbn"],
        "title": item.get("title", ""),
        "author": item.get("author", ""),
        "publisher": item.get("publisher", ""),
        "publishedDate": item.get("publishedDate", ""),
        "coverImageUrl": item.get("coverImageUrl", ""),
        "bookFormat": item.get("bookFormat", DEFAULT_BOOK_FORMAT),
        "category": item.get("category", DEFAULT_CATEGORY),
        "createdAt": item.get("createdAt", ""),
    }
