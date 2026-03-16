import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from shared.constants import GOOGLE_BOOKS_API_URL
from shared.isbn import normalize_isbn
from shared.responses import json_response


def extract_book(isbn: str, payload: dict[str, Any]) -> dict[str, str] | None:
    items = payload.get("items") or []

    if not items:
        return None

    volume_info = items[0].get("volumeInfo", {})
    image_links = volume_info.get("imageLinks", {})
    authors = volume_info.get("authors") or []

    return {
        "isbn": isbn,
        "title": volume_info.get("title", ""),
        "author": ", ".join(authors),
        "publisher": volume_info.get("publisher", ""),
        "publishedDate": volume_info.get("publishedDate", ""),
        "coverImageUrl": image_links.get("thumbnail", ""),
    }


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        raw_isbn = (event.get("pathParameters") or {}).get("isbn", "")
        isbn = normalize_isbn(raw_isbn)

        if not isbn:
            return json_response(400, {"message": "Invalid ISBN"})

        query = urlencode({"q": f"isbn:{isbn}", "maxResults": 1})
        with urlopen(f"{GOOGLE_BOOKS_API_URL}?{query}") as response:
            payload = json.loads(response.read().decode("utf-8"))

        book = extract_book(isbn, payload)
        if not book:
            return json_response(404, {"message": "Book metadata not found"})

        return json_response(200, book)
    except Exception as error:
        return json_response(500, {"message": f"Failed to lookup book: {error}"})
