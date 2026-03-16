from typing import Any


def to_book_response(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "userId": item["userId"],
        "isbn": item["isbn"],
        "title": item.get("title", ""),
        "author": item.get("author", ""),
        "publisher": item.get("publisher", ""),
        "publishedDate": item.get("publishedDate", ""),
        "coverImageUrl": item.get("coverImageUrl", ""),
        "bookFormat": item.get("bookFormat", "その他"),
        "category": item.get("category", "その他"),
        "createdAt": item.get("createdAt", ""),
    }
