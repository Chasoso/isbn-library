from __future__ import annotations

from io import BytesIO
from urllib.error import HTTPError
from unittest.mock import patch

from conftest import load_handler_module, parse_response


lookup_book_handler = load_handler_module("lookup_book")


class FakeResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def test_lookup_book_returns_metadata(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    payload = (
        b'{"items":[{"volumeInfo":{"title":"Book","authors":["Author"],"publisher":"Pub",'
        b'"publishedDate":"2024-01-01","imageLinks":{"thumbnail":"https://example.com"}}}]}'
    )

    with patch.object(lookup_book_handler, "urlopen", return_value=FakeResponse(payload)):
        status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 200
    assert body["isbn"] == "9784860648114"
    assert body["title"] == "Book"


def test_lookup_book_returns_503_after_rate_limit(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    rate_limited = HTTPError(
        url="https://example.com",
        code=429,
        msg="Too Many Requests",
        hdrs=None,
        fp=None,
    )

    with patch.object(lookup_book_handler, "urlopen", side_effect=rate_limited), patch.object(
        lookup_book_handler.time, "sleep", return_value=None
    ):
        status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 503
    assert "rate limit" in body["message"].lower()
