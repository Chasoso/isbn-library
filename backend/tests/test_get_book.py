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
            "bookFormat": "譁ｰ譖ｸ",
            "category": "謚陦捺嶌",
        }
    }

    with patch.object(get_book_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(get_book_handler.handler(lambda_event, None))

    assert status_code == 200
    assert body["isbn"] == "9784860648114"
    assert body["bookFormat"] == "譁ｰ譖ｸ"
    assert body["category"] == "謚陦捺嶌"


def test_get_book_rejects_invalid_isbn(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "invalid"}

    status_code, body = parse_response(get_book_handler.handler(lambda_event, None))

    assert status_code == 400
    assert body["message"] == "Invalid ISBN"


def test_get_book_returns_500_when_table_access_fails(lambda_event: dict[str, object]) -> None:
    lambda_event["pathParameters"] = {"isbn": "9784860648114"}

    with patch.object(get_book_handler, "get_books_table", side_effect=RuntimeError("boom")):
        status_code, body = parse_response(get_book_handler.handler(lambda_event, None))

    assert status_code == 500
    assert "Failed to get book" in body["message"]
