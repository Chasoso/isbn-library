from __future__ import annotations

from io import BytesIO
from urllib.parse import parse_qs, urlparse
from urllib.error import HTTPError, URLError
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


def test_lookup_book_does_not_call_rakuten_when_google_succeeds(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    payload = b'{"items":[{"volumeInfo":{"title":"Book"}}]}'

    with patch.dict(
        "os.environ",
        {"RAKUTEN_APPLICATION_ID": "test-app-id", "RAKUTEN_ACCESS_KEY": "test-access-key"},
        clear=False,
    ), patch.object(lookup_book_handler, "urlopen", return_value=FakeResponse(payload)) as mocked_urlopen:
        status_code, _body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 200
    assert mocked_urlopen.call_count == 1


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


def test_lookup_book_falls_back_to_rakuten_when_google_has_no_result(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    google_payload = b'{"items":[]}'
    rakuten_payload = (
        b'{"Items":[{"title":"Rakuten Book","author":"Author",'
        b'"publisherName":"Publisher","salesDate":"2024-02-01",'
        b'"isbn":"9784860648114","largeImageUrl":"https://example.com/cover"}]}'
    )

    with patch.dict(
        "os.environ",
        {"RAKUTEN_APPLICATION_ID": "test-app-id", "RAKUTEN_ACCESS_KEY": "test-access-key"},
        clear=False,
    ), patch.object(
        lookup_book_handler,
        "urlopen",
        side_effect=[FakeResponse(google_payload), FakeResponse(rakuten_payload)],
    ) as mocked_urlopen:
        status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 200
    assert body == {
        "isbn": "9784860648114",
        "title": "Rakuten Book",
        "author": "Author",
        "publisher": "Publisher",
        "publishedDate": "2024-02-01",
        "coverImageUrl": "https://example.com/cover",
    }
    assert mocked_urlopen.call_count == 2
    rakuten_request = mocked_urlopen.call_args_list[1].args[0]
    assert "test-access-key" not in rakuten_request.full_url
    assert rakuten_request.get_header("Accesskey") == "test-access-key"


def test_lookup_book_returns_404_when_both_providers_have_no_result(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}

    with patch.dict(
        "os.environ",
        {"RAKUTEN_APPLICATION_ID": "test-app-id", "RAKUTEN_ACCESS_KEY": "test-access-key"},
        clear=False,
    ), patch.object(
        lookup_book_handler,
        "urlopen",
        side_effect=[
            FakeResponse(b'{"items":[]}'),
            FakeResponse(b'{"Items":[]}'),
            FakeResponse(b"<rss><channel /></rss>"),
        ],
    ):
        status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 404
    assert body["message"] == "Book metadata not found"


def test_lookup_book_falls_back_to_ndl_after_google_and_rakuten(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    ndl_payload = b"""
    <rss xmlns:dc="http://purl.org/dc/elements/1.1/">
      <channel><item>
        <dc:identifier>ISBN 9784860648114</dc:identifier>
        <dc:title>NDL Book</dc:title>
        <dc:creator>NDL Author</dc:creator>
        <dc:publisher>NDL Publisher</dc:publisher>
        <dc:date>2024-03-01</dc:date>
        <dc:thumbnail>https://example.com/ndl-cover.jpg</dc:thumbnail>
      </item></channel>
    </rss>
    """

    with patch.dict(
        "os.environ",
        {"RAKUTEN_APPLICATION_ID": "test-app-id", "RAKUTEN_ACCESS_KEY": "test-access-key"},
        clear=False,
    ), patch.object(
        lookup_book_handler,
        "urlopen",
        side_effect=[FakeResponse(b'{"items":[]}'), FakeResponse(b'{"Items":[]}'), FakeResponse(ndl_payload)],
    ) as mocked_urlopen:
        status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 200
    assert body == {
        "isbn": "9784860648114",
        "title": "NDL Book",
        "author": "NDL Author",
        "publisher": "NDL Publisher",
        "publishedDate": "2024-03-01",
        "coverImageUrl": "https://example.com/ndl-cover.jpg",
    }
    assert mocked_urlopen.call_count == 3


def test_lookup_book_keeps_ndl_result_without_cover(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    ndl_payload = b"<rss><channel><item><title>NDL Book</title><creator>Author</creator></item></channel></rss>"

    with patch.dict(
        "os.environ",
        {"RAKUTEN_APPLICATION_ID": "test-app-id", "RAKUTEN_ACCESS_KEY": "test-access-key"},
        clear=False,
    ), patch.object(
        lookup_book_handler,
        "urlopen",
        side_effect=[FakeResponse(b'{"items":[]}'), FakeResponse(b'{"Items":[]}'), FakeResponse(ndl_payload)],
    ):
        status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 200
    assert body["coverImageUrl"] == ""


def test_lookup_book_returns_502_for_malformed_ndl_response(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}

    with patch.dict(
        "os.environ",
        {"RAKUTEN_APPLICATION_ID": "test-app-id", "RAKUTEN_ACCESS_KEY": "test-access-key"},
        clear=False,
    ), patch.object(
        lookup_book_handler,
        "urlopen",
        side_effect=[FakeResponse(b'{"items":[]}'), FakeResponse(b'{"Items":[]}'), FakeResponse(b"not xml")],
    ):
        status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 502
    assert "malformed XML" in body["message"]


def test_lookup_book_returns_502_for_ndl_http_error(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    upstream_error = HTTPError(
        url="https://ndlsearch.ndl.go.jp/api/opensearch",
        code=503,
        msg="Service Unavailable",
        hdrs=None,
        fp=None,
    )

    with patch.dict(
        "os.environ",
        {"RAKUTEN_APPLICATION_ID": "test-app-id", "RAKUTEN_ACCESS_KEY": "test-access-key"},
        clear=False,
    ), patch.object(
        lookup_book_handler,
        "urlopen",
        side_effect=[FakeResponse(b'{"items":[]}'), FakeResponse(b'{"Items":[]}'), upstream_error],
    ):
        status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 502
    assert "Failed to lookup book" in body["message"]


def test_lookup_book_returns_502_for_ndl_timeout(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}

    with patch.dict(
        "os.environ",
        {"RAKUTEN_APPLICATION_ID": "test-app-id", "RAKUTEN_ACCESS_KEY": "test-access-key"},
        clear=False,
    ), patch.object(
        lookup_book_handler,
        "urlopen",
        side_effect=[FakeResponse(b'{"items":[]}'), FakeResponse(b'{"Items":[]}'), URLError("timeout")],
    ):
        status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 502
    assert "Failed to lookup book" in body["message"]


def test_lookup_book_returns_502_for_rakuten_http_error(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    upstream_error = HTTPError(
        url="https://example.com",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=None,
    )

    with patch.dict(
        "os.environ",
        {"RAKUTEN_APPLICATION_ID": "test-app-id", "RAKUTEN_ACCESS_KEY": "test-access-key"},
        clear=False,
    ), patch.object(
        lookup_book_handler, "urlopen", side_effect=[FakeResponse(b'{"items":[]}'), upstream_error]
    ):
        status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 502
    assert "Failed to lookup book" in body["message"]


def test_lookup_book_returns_502_for_rakuten_timeout(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}

    with patch.dict(
        "os.environ",
        {"RAKUTEN_APPLICATION_ID": "test-app-id", "RAKUTEN_ACCESS_KEY": "test-access-key"},
        clear=False,
    ), patch.object(
        lookup_book_handler, "urlopen", side_effect=[FakeResponse(b'{"items":[]}'), URLError("timeout")]
    ):
        status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 502
    assert "Failed to lookup book" in body["message"]


def test_lookup_book_includes_api_key_when_configured(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    payload = b'{"items":[]}'

    def fake_urlopen(request, timeout=10):
        parsed = urlparse(request.full_url)
        if "ndlsearch.ndl.go.jp" in request.full_url:
            return FakeResponse(b"<rss><channel /></rss>")
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


def test_lookup_book_rejects_invalid_isbn(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "invalid"}

    status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 400
    assert body["message"] == "Invalid ISBN"


def test_lookup_book_returns_502_for_non_rate_limited_http_error(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    upstream_error = HTTPError(
        url="https://example.com",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=None,
    )

    with patch.object(lookup_book_handler, "urlopen", side_effect=upstream_error):
        status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 502
    assert "Failed to lookup book" in body["message"]


def test_lookup_book_returns_502_for_url_error(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}

    with patch.object(lookup_book_handler, "urlopen", side_effect=URLError("dns failure")), patch.object(
        lookup_book_handler.time, "sleep", return_value=None
    ):
        status_code, body = parse_response(lookup_book_handler.handler(lambda_event, None))

    assert status_code == 502
    assert "Failed to lookup book" in body["message"]
