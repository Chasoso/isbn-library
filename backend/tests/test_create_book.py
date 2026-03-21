from __future__ import annotations

import json
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from conftest import load_handler_module, parse_response
from shared.catalog import BOOK_FORMATS, CATEGORIES, DEFAULT_BOOK_FORMAT, DEFAULT_CATEGORY
from shared.statuses import DEFAULT_READING_STATUS, READING_STATUSES


create_book_handler = load_handler_module("create_book")
VALID_BOOK_FORMAT = next(iter(BOOK_FORMATS - {DEFAULT_BOOK_FORMAT}))
VALID_CATEGORY = next(iter(CATEGORIES - {DEFAULT_CATEGORY}))
VALID_READING_STATUS = next(iter(READING_STATUSES - {DEFAULT_READING_STATUS}))


def test_create_book_success(lambda_event: dict[str, object]) -> None:
    table = Mock()
    lambda_event["body"] = json.dumps(
        {
            "isbn": "9784860648114",
            "title": "Sample",
            "author": "Author",
            "bookFormat": VALID_BOOK_FORMAT,
            "category": VALID_CATEGORY,
            "readingStatus": VALID_READING_STATUS,
        },
        ensure_ascii=False,
    )

    with patch.object(create_book_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 201
    assert body["isbn"] == "9784860648114"
    assert body["bookFormat"] == VALID_BOOK_FORMAT
    assert body["category"] == VALID_CATEGORY
    assert body["readingStatus"] == VALID_READING_STATUS
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
            "category": VALID_CATEGORY,
            "readingStatus": VALID_READING_STATUS,
        },
        ensure_ascii=False,
    )

    with patch.object(create_book_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 409
    assert body["message"] == "Book already exists"


def test_create_book_rejects_invalid_reading_status(lambda_event: dict[str, object]) -> None:
    lambda_event["body"] = json.dumps(
        {
            "isbn": "9784860648114",
            "title": "Sample",
            "bookFormat": VALID_BOOK_FORMAT,
            "category": VALID_CATEGORY,
            "readingStatus": "invalid-status",
        },
        ensure_ascii=False,
    )

    status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 400
    assert body["message"] == "Invalid readingStatus"


def test_create_book_rejects_invalid_book_format(lambda_event: dict[str, object]) -> None:
    lambda_event["body"] = json.dumps(
        {
            "isbn": "9784860648114",
            "title": "Sample",
            "bookFormat": "invalid-format",
            "category": VALID_CATEGORY,
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
            "category": "invalid-category",
            "readingStatus": VALID_READING_STATUS,
        },
        ensure_ascii=False,
    )

    status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 400
    assert body["message"] == "Invalid category"


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
            "category": VALID_CATEGORY,
            "readingStatus": VALID_READING_STATUS,
        },
        ensure_ascii=False,
    )

    with patch.object(create_book_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 500
    assert "Failed to create book" in body["message"]
