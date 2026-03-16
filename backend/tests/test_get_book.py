from __future__ import annotations

from unittest.mock import Mock, patch

from conftest import load_handler_module, parse_response


get_book_handler = load_handler_module("get_book")


def test_get_book_returns_404_when_missing(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    table = Mock()
    table.get_item.return_value = {}

    with patch.object(get_book_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(get_book_handler.handler(lambda_event, None))

    assert status_code == 404
    assert body["message"] == "Book not found"


def test_get_book_returns_book(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}
    table = Mock()
    table.get_item.return_value = {
        "Item": {
            "userId": "user-123",
            "isbn": "9784860648114",
            "title": "Sample",
            "author": "Author",
            "bookFormat": "新書",
            "category": "技術書",
        }
    }

    with patch.object(get_book_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(get_book_handler.handler(lambda_event, None))

    assert status_code == 200
    assert body["isbn"] == "9784860648114"
    assert body["bookFormat"] == "新書"
    assert body["category"] == "技術書"
