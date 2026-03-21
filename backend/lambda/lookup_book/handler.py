import json
import os
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from shared.constants import GOOGLE_BOOKS_API_KEY_ENV, GOOGLE_BOOKS_API_URL
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


def fetch_google_books_payload(isbn: str) -> dict[str, Any]:
    query_params = {"q": f"isbn:{isbn}", "maxResults": 1}
    api_key = os.getenv(GOOGLE_BOOKS_API_KEY_ENV, "").strip()
    if api_key:
        query_params["key"] = api_key

    query = urlencode(query_params)
    request = Request(
        f"{GOOGLE_BOOKS_API_URL}?{query}",
        headers={
            "User-Agent": "isbn-library/1.0",
            "Accept": "application/json",
        },
    )

    retry_delays = [0.4, 0.8, 1.6]

    for attempt, delay in enumerate(retry_delays, start=1):
        try:
            with urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 429:
                if attempt == len(retry_delays):
                    raise
                time.sleep(delay)
                continue
            raise
        except URLError:
            if attempt == len(retry_delays):
                raise
            time.sleep(delay)

    raise RuntimeError("Failed to fetch Google Books payload")


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        raw_isbn = (event.get("pathParameters") or {}).get("isbn", "")
        isbn = normalize_isbn(raw_isbn)

        if not isbn:
            return json_response(400, {"message": "Invalid ISBN"})

        payload = fetch_google_books_payload(isbn)

        book = extract_book(isbn, payload)
        if not book:
            return json_response(404, {"message": "Book metadata not found"})

        return json_response(200, book)
    except HTTPError as error:
        if error.code == 429:
            return json_response(
                503,
                {
                    "message": "Google Books API rate limit exceeded. Please try again shortly."
                },
            )
        return json_response(502, {"message": f"Failed to lookup book: {error}"})
    except URLError as error:
        return json_response(502, {"message": f"Failed to lookup book: {error}"})
    except Exception as error:
        return json_response(500, {"message": f"Failed to lookup book: {error}"})
