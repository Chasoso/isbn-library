from __future__ import annotations

import json
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from conftest import load_handler_module, parse_response


create_book_handler = load_handler_module("create_book")


def test_create_book_success(lambda_event: dict[str, object]) -> None:
    table = Mock()
    lambda_event["body"] = json.dumps(
        {
            "isbn": "9784860648114",
            "title": "Sample",
            "author": "Author",
            "bookFormat": "新書",
            "category": "技術書",
            "readingStatus": "未読",
        },
        ensure_ascii=False,
    )

    with patch.object(create_book_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 201
    assert body["isbn"] == "9784860648114"
    assert body["bookFormat"] == "新書"
    assert body["category"] == "技術書"
    assert body["readingStatus"] == "未読"
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
            "bookFormat": "新書",
            "category": "技術書",
            "readingStatus": "未読",
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
            "bookFormat": "新書",
            "category": "技術書",
            "readingStatus": "積読",
        },
        ensure_ascii=False,
    )

    status_code, body = parse_response(create_book_handler.handler(lambda_event, None))

    assert status_code == 400
    assert body["message"] == "Invalid readingStatus"
