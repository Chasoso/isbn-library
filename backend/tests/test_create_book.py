from __future__ import annotations

import json
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from conftest import load_handler_module, parse_response
from shared.catalog import BOOK_FORMATS, DEFAULT_BOOK_FORMAT
from shared.statuses import DEFAULT_READING_STATUS, READING_STATUSES


create_book_handler = load_handler_module("create_book")
VALID_BOOK_FORMAT = next(iter(BOOK_FORMATS - {DEFAULT_BOOK_FORMAT}))
VALID_READING_STATUS = next(iter(READING_STATUSES - {DEFAULT_READING_STATUS}))
VALID_CATEGORY = {"categoryId": "technology", "name": "技術書"}


def test_create_book_success(lambda_event: dict[str, object]) -> None:
    table = Mock()
    lambda_event["body"] = json.dumps(
        {
          "isbn": "9784860648114",
          "title": "Sample",
          "author": "Author",
          "bookFormat": VALID_BOOK_FORMAT,
          "categoryId": VALID_CATEGORY["categoryId"],
          "readingStatus": VALID_READING_STATUS,
        },
        ensure_ascii=False,
    )

    with (
        patch.object(create_book_handler, "get_books_table", return_value=table),
        patch.object(create_book_handler, "get_category", return_value=VALID_CATEGORY),
        patch.object(
            create_book_handler,
            "resolve_english_title",
            return_value={
                "titleEn": "Sample",
                "titleEnSource": "none",
                "titleEnStatus": "resolved",
                "titleEnUpdatedAt": "2026-03-23T00:00:00+00:00",
            },
        ),
    ):
        status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 201
    assert body["isbn"] == "9784860648114"
    assert body["bookFormat"] == VALID_BOOK_FORMAT
    assert body["categoryId"] == VALID_CATEGORY["categoryId"]
    assert body["categoryName"] == VALID_CATEGORY["name"]
    assert body["readingStatus"] == VALID_READING_STATUS
    assert body["titleEn"] == "Sample"
    assert body["titleEnSource"] == "none"
    table.put_item.assert_called_once()


def test_create_book_returns_409_for_duplicate(lambda_event: dict[str, object]) -> None:
    table = Mock()
    table.put_item.side_effect = ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "duplicate"}},
        "PutItem",
    )
    lambda_event["body"] = json.dumps(
        {
            "isbn": "9784860648114",
            "title": "Sample",
            "bookFormat": VALID_BOOK_FORMAT,
            "categoryId": VALID_CATEGORY["categoryId"],
            "readingStatus": VALID_READING_STATUS,
        },
        ensure_ascii=False,
    )

    with (
        patch.object(create_book_handler, "get_books_table", return_value=table),
        patch.object(create_book_handler, "get_category", return_value=VALID_CATEGORY),
    ):
        status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 409
    assert body["message"] == "Book already exists"


def test_create_book_preserves_manual_title_en(lambda_event: dict[str, object]) -> None:
    table = Mock()
    lambda_event["body"] = json.dumps(
        {
            "isbn": "9784860648114",
            "title": "サンプル",
            "titleEn": "Sample Book",
            "bookFormat": VALID_BOOK_FORMAT,
            "categoryId": VALID_CATEGORY["categoryId"],
            "readingStatus": VALID_READING_STATUS,
        },
        ensure_ascii=False,
    )

    with (
        patch.object(create_book_handler, "get_books_table", return_value=table),
        patch.object(create_book_handler, "get_category", return_value=VALID_CATEGORY),
    ):
        status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 201
    assert body["titleEn"] == "Sample Book"
    assert body["titleEnSource"] == "manual"
    assert body["titleEnStatus"] == "manual"
    stored_item = table.put_item.call_args.kwargs["Item"]
    assert stored_item["titleEn"] == "Sample Book"


def test_create_book_uses_external_metadata_title_en(lambda_event: dict[str, object]) -> None:
    table = Mock()
    lambda_event["body"] = json.dumps(
        {
            "isbn": "9784860648114",
            "title": "サンプル",
            "bookFormat": VALID_BOOK_FORMAT,
            "categoryId": VALID_CATEGORY["categoryId"],
            "readingStatus": VALID_READING_STATUS,
        },
        ensure_ascii=False,
    )

    with (
        patch.object(create_book_handler, "get_books_table", return_value=table),
        patch.object(create_book_handler, "get_category", return_value=VALID_CATEGORY),
        patch.object(
            create_book_handler,
            "resolve_english_title",
            return_value={
                "titleEn": "Sample Book",
                "titleEnSource": "external_metadata",
                "titleEnStatus": "resolved",
                "titleEnUpdatedAt": "2026-03-23T00:00:00+00:00",
            },
        ),
    ):
        status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 201
    assert body["titleEn"] == "Sample Book"
    assert body["titleEnSource"] == "external_metadata"


def test_create_book_uses_machine_translation_when_external_lookup_fails(
    lambda_event: dict[str, object],
) -> None:
    table = Mock()
    lambda_event["body"] = json.dumps(
        {
            "isbn": "9784860648114",
            "title": "サンプル",
            "bookFormat": VALID_BOOK_FORMAT,
            "categoryId": VALID_CATEGORY["categoryId"],
            "readingStatus": VALID_READING_STATUS,
        },
        ensure_ascii=False,
    )

    with (
        patch.object(create_book_handler, "get_books_table", return_value=table),
        patch.object(create_book_handler, "get_category", return_value=VALID_CATEGORY),
        patch.object(
            create_book_handler,
            "resolve_english_title",
            return_value={
                "titleEn": "Translated Sample",
                "titleEnSource": "machine_translation",
                "titleEnStatus": "resolved",
                "titleEnUpdatedAt": "2026-03-23T00:00:00+00:00",
            },
        ),
    ):
        status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 201
    assert body["titleEn"] == "Translated Sample"
    assert body["titleEnSource"] == "machine_translation"


def test_create_book_succeeds_even_when_title_en_resolution_fails(
    lambda_event: dict[str, object],
) -> None:
    table = Mock()
    lambda_event["body"] = json.dumps(
        {
            "isbn": "9784860648114",
            "title": "サンプル",
            "bookFormat": VALID_BOOK_FORMAT,
            "categoryId": VALID_CATEGORY["categoryId"],
            "readingStatus": VALID_READING_STATUS,
        },
        ensure_ascii=False,
    )

    with (
        patch.object(create_book_handler, "get_books_table", return_value=table),
        patch.object(create_book_handler, "get_category", return_value=VALID_CATEGORY),
        patch.object(
            create_book_handler,
            "resolve_english_title",
            return_value={
                "titleEn": "",
                "titleEnSource": "none",
                "titleEnStatus": "failed",
                "titleEnUpdatedAt": "2026-03-23T00:00:00+00:00",
            },
        ),
    ):
        status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 201
    assert body["titleEn"] == ""
    assert body["titleEnStatus"] == "failed"


def test_create_book_keeps_existing_english_title_without_translation(
    lambda_event: dict[str, object],
) -> None:
    table = Mock()
    lambda_event["body"] = json.dumps(
        {
            "isbn": "9781492052203",
            "title": "Designing Data-Intensive Applications",
            "bookFormat": VALID_BOOK_FORMAT,
            "categoryId": VALID_CATEGORY["categoryId"],
            "readingStatus": VALID_READING_STATUS,
        },
        ensure_ascii=False,
    )

    with (
        patch.object(create_book_handler, "get_books_table", return_value=table),
        patch.object(create_book_handler, "get_category", return_value=VALID_CATEGORY),
        patch.object(
            create_book_handler,
            "resolve_english_title",
            return_value={
                "titleEn": "Designing Data-Intensive Applications",
                "titleEnSource": "none",
                "titleEnStatus": "resolved",
                "titleEnUpdatedAt": "2026-03-23T00:00:00+00:00",
            },
        ),
    ):
        status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 201
    assert body["titleEn"] == "Designing Data-Intensive Applications"


def test_create_book_rejects_invalid_reading_status(lambda_event: dict[str, object]) -> None:
    lambda_event["body"] = json.dumps(
        {
            "isbn": "9784860648114",
            "title": "Sample",
            "bookFormat": VALID_BOOK_FORMAT,
            "categoryId": VALID_CATEGORY["categoryId"],
            "readingStatus": "invalid-status",
        },
        ensure_ascii=False,
    )

    with patch.object(create_book_handler, "get_category", return_value=VALID_CATEGORY):
        status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 400
    assert body["message"] == "Invalid readingStatus"


def test_create_book_rejects_invalid_book_format(lambda_event: dict[str, object]) -> None:
    lambda_event["body"] = json.dumps(
        {
            "isbn": "9784860648114",
            "title": "Sample",
            "bookFormat": "invalid-format",
            "categoryId": VALID_CATEGORY["categoryId"],
            "readingStatus": VALID_READING_STATUS,
        },
        ensure_ascii=False,
    )

    status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 400
    assert body["message"] == "Invalid bookFormat"


def test_create_book_rejects_invalid_category(lambda_event: dict[str, object]) -> None:
    lambda_event["body"] = json.dumps(
        {
            "isbn": "9784860648114",
            "title": "Sample",
            "bookFormat": VALID_BOOK_FORMAT,
            "categoryId": "invalid-category",
            "readingStatus": VALID_READING_STATUS,
        },
        ensure_ascii=False,
    )

    with patch.object(create_book_handler, "get_category", return_value=None):
        status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 400
    assert body["message"] == "Invalid categoryId"


def test_create_book_returns_500_for_unexpected_client_error(lambda_event: dict[str, object]) -> None:
    table = Mock()
    table.put_item.side_effect = ClientError(
        {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "throttled"}},
        "PutItem",
    )
    lambda_event["body"] = json.dumps(
        {
            "isbn": "9784860648114",
            "title": "Sample",
            "bookFormat": VALID_BOOK_FORMAT,
            "categoryId": VALID_CATEGORY["categoryId"],
            "readingStatus": VALID_READING_STATUS,
        },
        ensure_ascii=False,
    )

    with (
        patch.object(create_book_handler, "get_books_table", return_value=table),
        patch.object(create_book_handler, "get_category", return_value=VALID_CATEGORY),
    ):
        status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 500
    assert "Failed to create book" in body["message"]
