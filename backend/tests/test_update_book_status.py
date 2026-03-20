from __future__ import annotations

import json
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from conftest import load_handler_module, parse_response


update_book_status_handler = load_handler_module("update_book_status")


def test_update_book_status_success(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    lambda_event["body"] = json.dumps({"readingStatus": "読書中"}, ensure_ascii=False)
    table = Mock()
    table.update_item.return_value = {
        "Attributes": {
            "userId": "user-123",
            "isbn": "9784860648114",
            "readingStatus": "読書中",
        }
    }

    with patch.object(update_book_status_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(update_book_status_handler.handler(lambda_event, None))

    assert status_code == 200
    assert body["readingStatus"] == "読書中"


def test_update_book_status_returns_404_when_missing(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    lambda_event["body"] = json.dumps({"readingStatus": "完了"}, ensure_ascii=False)
    table = Mock()
    table.update_item.side_effect = ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "missing"}},
        "UpdateItem",
    )

    with patch.object(update_book_status_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(update_book_status_handler.handler(lambda_event, None))

    assert status_code == 404
    assert body["message"] == "Book not found"
