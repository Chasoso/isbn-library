from __future__ import annotations

from io import BytesIO
from urllib.parse import parse_qs, urlparse
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


def test_lookup_book_prefers_larger_cover_images(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    payload = (
        b'{"items":[{"volumeInfo":{"title":"Book","authors":["Author"],"publisher":"Pub",'
        b'"publishedDate":"2024-01-01","imageLinks":{"thumbnail":"https://example.com/thumb",'
        b'"small":"https://example.com/small","medium":"https://example.com/medium",'
        b'"large":"https://example.com/large","extraLarge":"https://example.com/extra-large"}}}]}'
    )

    with patch.object(lookup_book_handler, "urlopen", return_value=FakeResponse(payload)):
        status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 200
    assert body["coverImageUrl"] == "https://example.com/extra-large"


def test_lookup_book_includes_api_key_when_configured(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    payload = b'{"items":[]}'

    def fake_urlopen(request, timeout=10):
        parsed = urlparse(request.full_url)
        params = parse_qs(parsed.query)
        assert params["q"] == ["isbn:9784860648114"]
        assert params["maxResults"] == ["1"]
        assert params["key"] == ["test-api-key"]
        return FakeResponse(payload)

    with patch.dict("os.environ", {"GOOGLE_BOOKS_API_KEY": "test-api-key"}, clear=False), patch.object(
        lookup_book_handler, "urlopen", side_effect=fake_urlopen
    ):
        status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 404
    assert body["message"] == "Book metadata not found"


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
