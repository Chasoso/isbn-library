from __future__ import annotations

from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from unittest.mock import Mock, patch

from shared.title_en import (
    build_title_en_metadata,
    extract_english_title_from_external_metadata,
    fetch_google_books_payload,
    looks_like_english_title,
    resolve_english_title_from_external_metadata,
    resolve_english_title,
    should_skip_translation,
    translate_title_to_english,
)


class FakeResponse(BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def test_resolve_english_title_preserves_manual_value() -> None:
    metadata = resolve_english_title({"isbn": "9784860648114", "title": "サンプル", "titleEn": "Sample"})

    assert metadata["titleEn"] == "Sample"
    assert metadata["titleEnSource"] == "manual"
    assert metadata["titleEnStatus"] == "manual"


def test_resolve_english_title_prefers_external_metadata() -> None:
    payload = b'{"items":[{"volumeInfo":{"title":"Sample Book","language":"en"}}]}'

    with patch("shared.title_en.urlopen", return_value=FakeResponse(payload)):
        metadata = resolve_english_title({"isbn": "9784860648114", "title": "サンプル"})

    assert metadata["titleEn"] == "Sample Book"
    assert metadata["titleEnSource"] == "external_metadata"
    assert metadata["titleEnStatus"] == "resolved"


def test_resolve_english_title_falls_back_to_machine_translation() -> None:
    translate_client = Mock()
    translate_client.translate_text.return_value = {"TranslatedText": "Translated Sample"}

    with (
        patch("shared.title_en.urlopen", return_value=FakeResponse(b'{"items":[]}')),
        patch("shared.title_en.boto3.client", return_value=translate_client),
    ):
        metadata = resolve_english_title({"isbn": "9784860648114", "title": "サンプル"})

    assert metadata["titleEn"] == "Translated Sample"
    assert metadata["titleEnSource"] == "machine_translation"
    assert metadata["titleEnStatus"] == "resolved"


def test_resolve_english_title_returns_failed_without_breaking_on_errors() -> None:
    with (
        patch("shared.title_en.urlopen", side_effect=RuntimeError("lookup failed")),
        patch("shared.title_en.boto3.client", side_effect=RuntimeError("translate failed")),
    ):
        metadata = resolve_english_title({"isbn": "9784860648114", "title": "サンプル"})

    assert metadata["titleEn"] == ""
    assert metadata["titleEnSource"] == "none"
    assert metadata["titleEnStatus"] == "failed"


def test_resolve_english_title_keeps_already_english_title() -> None:
    with patch("shared.title_en.urlopen", return_value=FakeResponse(b'{"items":[]}')):
        metadata = resolve_english_title({"isbn": "9781492052203", "title": "Clean Architecture"})

    assert metadata["titleEn"] == "Clean Architecture"
    assert metadata["titleEnSource"] == "none"
    assert metadata["titleEnStatus"] == "resolved"


def test_translate_title_to_english_skips_invalid_or_empty_titles() -> None:
    assert translate_title_to_english("") is None
    assert translate_title_to_english("9784860648114") is None
    assert translate_title_to_english("!!!") is None


def test_english_title_heuristics_detect_ascii_titles() -> None:
    assert looks_like_english_title("Domain-Driven Design")
    assert not looks_like_english_title("ドメイン駆動設計")
    assert should_skip_translation("Clean Code")


def test_extract_english_title_from_external_metadata_handles_missing_and_english_like_titles() -> None:
    assert extract_english_title_from_external_metadata({"items": [{"volumeInfo": {"language": "en"}}]}) is None
    assert (
        extract_english_title_from_external_metadata(
            {"items": [{"volumeInfo": {"title": "Refactoring", "language": "fr"}}]}
        )
        == "Refactoring"
    )


def test_fetch_google_books_payload_includes_api_key_and_handles_unreadable_http_error_body() -> None:
    http_error = HTTPError(
        url="https://example.com",
        code=500,
        msg="boom",
        hdrs=None,
        fp=None,
    )
    http_error.read = Mock(side_effect=RuntimeError("read failed"))

    def fake_urlopen(request, timeout=10):
        parsed = urlparse(request.full_url)
        params = parse_qs(parsed.query)
        assert params["key"] == ["test-api-key"]
        raise http_error

    with (
        patch.dict("os.environ", {"GOOGLE_BOOKS_API_KEY": "test-api-key"}, clear=False),
        patch("shared.title_en.urlopen", side_effect=fake_urlopen),
    ):
        try:
            fetch_google_books_payload("9784860648114")
        except HTTPError as error:
            assert error.code == 500
        else:
            raise AssertionError("Expected HTTPError")


def test_fetch_google_books_payload_retries_url_error_and_raises() -> None:
    with (
        patch("shared.title_en.urlopen", side_effect=URLError("dns failure")),
        patch("shared.title_en.time.sleep", return_value=None) as sleep_mock,
    ):
        try:
            fetch_google_books_payload("9784860648114")
        except URLError:
            pass
        else:
            raise AssertionError("Expected URLError")

    assert sleep_mock.call_count == 2


def test_resolve_english_title_from_external_metadata_returns_none_without_isbn() -> None:
    assert resolve_english_title_from_external_metadata("") is None


def test_build_title_en_metadata_sets_timestamp() -> None:
    metadata = build_title_en_metadata("Sample", "manual", "manual")

    assert metadata["titleEn"] == "Sample"
    assert metadata["titleEnSource"] == "manual"
    assert metadata["titleEnStatus"] == "manual"
    assert metadata["titleEnUpdatedAt"]
