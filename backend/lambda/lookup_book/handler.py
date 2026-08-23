import json
import os
import re
import time
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from shared.constants import (
    GOOGLE_BOOKS_API_KEY_ENV,
    GOOGLE_BOOKS_API_URL,
    NDL_SEARCH_API_URL,
    RAKUTEN_ACCESS_KEY_ENV,
    RAKUTEN_APPLICATION_ID_ENV,
    RAKUTEN_BOOKS_API_URL,
)
from shared.isbn import normalize_isbn
from shared.logging_utils import log_external_api, log_request, log_response
from shared.responses import json_response


def select_cover_image_url(image_links: dict[str, Any]) -> str:
    for key in ("extraLarge", "large", "medium", "small", "thumbnail"):
        value = image_links.get(key)
        if value:
            return value
    return ""


def select_rakuten_cover_image(item: dict[str, Any]) -> str:
    for key in ("largeImageUrl", "mediumImageUrl", "smallImageUrl"):
        value = item.get(key)
        if value:
            return value
    return ""


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
        "coverImageUrl": select_cover_image_url(image_links),
    }


def extract_rakuten_book(isbn: str, payload: dict[str, Any]) -> dict[str, str] | None:
    items = payload.get("Items") or payload.get("items") or []
    if not items:
        return None

    item = items[0].get("item", items[0])
    author = item.get("author", "")
    if isinstance(author, list):
        author = ", ".join(str(value) for value in author)

    return {
        "isbn": item.get("isbn") or isbn,
        "title": item.get("title", ""),
        "author": str(author),
        "publisher": item.get("publisherName", ""),
        "publishedDate": item.get("salesDate", ""),
        "coverImageUrl": select_rakuten_cover_image(item),
    }


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _element_text(element: ET.Element, names: set[str]) -> str:
    for child in element.iter():
        if _local_name(child.tag) in names and child.text and child.text.strip():
            return child.text.strip()
    return ""


def _element_texts(element: ET.Element, names: set[str]) -> list[str]:
    return [
        child.text.strip()
        for child in element.iter()
        if _local_name(child.tag) in names and child.text and child.text.strip()
    ]


def _element_url(element: ET.Element) -> str:
    url_names = {"thumbnail", "cover", "coverimage", "image", "depiction"}
    for child in element.iter():
        if _local_name(child.tag) in url_names:
            for attribute in ("resource", "href", "url"):
                value = child.attrib.get(attribute, "").strip()
                if value:
                    return value
            if child.text and child.text.strip().startswith(("http://", "https://")):
                return child.text.strip()
    return ""


def extract_ndl_book(isbn: str, payload: bytes) -> dict[str, str] | None:
    root = ET.fromstring(payload)
    items = [element for element in root.iter() if _local_name(element.tag) == "item"]
    if not items:
        return None

    item = items[0]
    identifiers = _element_texts(item, {"identifier"})
    isbn_value = isbn
    for identifier in identifiers:
        match = re.search(r"(?:97[89][0-9\- ]{10,}|[0-9\- ]{10,})", identifier)
        if match:
            normalized = re.sub(r"[^0-9Xx]", "", match.group(0)).upper()
            if len(normalized) in (10, 13):
                isbn_value = normalized
                break

    authors = _element_texts(item, {"creator", "author"})
    return {
        "isbn": isbn_value,
        "title": _element_text(item, {"title"}),
        "author": ", ".join(dict.fromkeys(authors)),
        "publisher": _element_text(item, {"publisher"}),
        "publishedDate": _element_text(item, {"issued", "date", "publicationdate"}),
        "coverImageUrl": _element_url(item),
    }


def fetch_google_books_payload(isbn: str) -> dict[str, Any]:
    query_params = {"q": f"isbn:{isbn}", "maxResults": 1}
    api_key = os.getenv(GOOGLE_BOOKS_API_KEY_ENV, "").strip()
    if api_key:
        query_params["key"] = api_key

    query = urlencode(query_params)
    request_url = f"{GOOGLE_BOOKS_API_URL}?{query}"
    request = Request(
        request_url,
        headers={
            "User-Agent": "isbn-library/1.0",
            "Accept": "application/json",
        },
    )

    retry_delays = [0.4, 0.8, 1.6]

    for attempt, delay in enumerate(retry_delays, start=1):
        try:
            with urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
                log_external_api(
                    "lookup_book.google_books",
                    request_url,
                    getattr(response, "status", 200),
                    payload,
                )
                return payload
        except HTTPError as error:
            try:
                error_body = error.read().decode("utf-8", errors="replace")
            except Exception:
                error_body = str(error)
            log_external_api(
                "lookup_book.google_books",
                request_url,
                error.code,
                error_body,
            )
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


def fetch_rakuten_books_payload(isbn: str) -> dict[str, Any]:
    application_id = os.getenv(RAKUTEN_APPLICATION_ID_ENV, "").strip()
    access_key = os.getenv(RAKUTEN_ACCESS_KEY_ENV, "").strip()
    if not application_id or not access_key:
        return {}

    query = urlencode(
        {
            "applicationId": application_id,
            "format": "json",
            "formatVersion": 2,
            "hits": 1,
            "isbn": isbn,
        }
    )
    request_url = f"{RAKUTEN_BOOKS_API_URL}?{query}"
    request = Request(
        request_url,
        headers={
            "Accept": "application/json",
            "User-Agent": "isbn-library/1.0",
            "accessKey": access_key,
        },
    )

    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
            log_external_api(
                "lookup_book.rakuten_books",
                request_url,
                getattr(response, "status", 200),
                payload,
            )
            return payload
    except HTTPError as error:
        try:
            error_body = error.read().decode("utf-8", errors="replace")
        except Exception:
            error_body = str(error)
        log_external_api(
            "lookup_book.rakuten_books",
            request_url,
            error.code,
            error_body,
        )
        if error.code == 404:
            return {}
        raise


def fetch_ndl_search_payload(isbn: str) -> bytes:
    request_url = f"{NDL_SEARCH_API_URL}?{urlencode({'isbn': isbn, 'cnt': 1})}"
    request = Request(
        request_url,
        headers={
            "Accept": "application/rss+xml, application/xml",
            "User-Agent": "isbn-library/1.0",
        },
    )

    try:
        with urlopen(request, timeout=10) as response:
            payload = response.read()
            # Parse here so malformed XML is treated as an upstream failure, not no result.
            ET.fromstring(payload)
            log_external_api(
                "lookup_book.ndl_search",
                request_url,
                getattr(response, "status", 200),
                {"has_item": b"<item" in payload.lower()},
            )
            return payload
    except HTTPError as error:
        try:
            error_body = error.read().decode("utf-8", errors="replace")
        except Exception:
            error_body = str(error)
        log_external_api("lookup_book.ndl_search", request_url, error.code, error_body)
        if error.code == 404:
            return b"<rss><channel /></rss>"
        raise
    except ET.ParseError as error:
        raise ValueError("NDL Search returned malformed XML") from error


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        log_request("lookup_book", event)
        raw_isbn = (event.get("pathParameters") or {}).get("isbn", "")
        isbn = normalize_isbn(raw_isbn)

        if not isbn:
            return log_response("lookup_book", json_response(400, {"message": "Invalid ISBN"}))

        payload = fetch_google_books_payload(isbn)
        book = extract_book(isbn, payload)
        source = "google_books"
        if not book:
            payload = fetch_rakuten_books_payload(isbn)
            book = extract_rakuten_book(isbn, payload)
            source = "rakuten_books"

        if not book:
            payload = fetch_ndl_search_payload(isbn)
            book = extract_ndl_book(isbn, payload)
            source = "ndl_search"

        if not book:
            return log_response("lookup_book", json_response(404, {"message": "Book metadata not found"}))

        return log_response(f"lookup_book.{source}", json_response(200, book))
    except HTTPError as error:
        if error.code == 429:
            return log_response(
                "lookup_book",
                json_response(
                    503,
                    {
                        "message": "Books metadata API rate limit exceeded. Please try again shortly."
                    },
                ),
            )
        return log_response("lookup_book", json_response(502, {"message": f"Failed to lookup book: {error}"}))
    except URLError as error:
        return log_response("lookup_book", json_response(502, {"message": f"Failed to lookup book: {error}"}))
    except ValueError as error:
        return log_response("lookup_book", json_response(502, {"message": f"Failed to lookup book: {error}"}))
    except Exception as error:
        return log_response("lookup_book", json_response(500, {"message": f"Failed to lookup book: {error}"}))
