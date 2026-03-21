from __future__ import annotations

import json
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from conftest import load_handler_module, parse_response
from shared.statuses import DEFAULT_READING_STATUS, READING_STATUSES


update_book_status_handler = load_handler_module("update_book_status")
VALID_READING_STATUS = next(iter(READING_STATUSES - {DEFAULT_READING_STATUS}))


def test_update_book_status_success(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    lambda_event["body"] = json.dumps({"readingStatus": VALID_READING_STATUS}, ensure_ascii=False)
    table = Mock()
    table.update_item.return_value = {
        "Attributes": {
            "userId": "user-123",
            "isbn": "9784860648114",
            "readingStatus": VALID_READING_STATUS,
        }
    }

    with patch.object(update_book_status_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(update_book_status_handler.handler(lambda_event, None))

    assert status_code == 200
    assert body["readingStatus"] == VALID_READING_STATUS


def test_update_book_status_returns_404_when_missing(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    lambda_event["body"] = json.dumps({"readingStatus": VALID_READING_STATUS}, ensure_ascii=False)
    table = Mock()
    table.update_item.side_effect = ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "missing"}},
        "UpdateItem",
    )

    with patch.object(update_book_status_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(update_book_status_handler.handler(lambda_event, None))

    assert status_code == 404
    assert body["message"] == "Book not found"


def test_update_book_status_rejects_invalid_isbn(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "invalid"}
    lambda_event["body"] = json.dumps({"readingStatus": DEFAULT_READING_STATUS}, ensure_ascii=False)

    status_code, body = parse_response(update_book_status_handler.handler(lambda_event, None))

    assert status_code == 400
    assert body["message"] == "Invalid ISBN"


def test_update_book_status_rejects_invalid_status(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    lambda_event["body"] = json.dumps({"readingStatus": "invalid"}, ensure_ascii=False)

    status_code, body = parse_response(update_book_status_handler.handler(lambda_event, None))

    assert status_code == 400
    assert body["message"] == "Invalid readingStatus"


def test_update_book_status_returns_500_for_unexpected_client_error(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    lambda_event["body"] = json.dumps({"readingStatus": DEFAULT_READING_STATUS}, ensure_ascii=False)
    table = Mock()
    table.update_item.side_effect = ClientError(
        {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "throttled"}},
        "UpdateItem",
    )

    with patch.object(update_book_status_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(update_book_status_handler.handler(lambda_event, None))

    assert status_code == 500
    assert "Failed to update reading status" in body["message"]
