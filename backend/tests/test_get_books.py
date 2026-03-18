from __future__ import annotations

from unittest.mock import Mock, patch

from conftest import load_handler_module, parse_response


get_books_handler = load_handler_module("get_books")


def test_get_books_filters_by_title_and_classifications(
    lambda_event: dict[str, object],
) -> None:
    lambda_event["queryStringParameters"] = {
        "q": "python",
        "bookFormat": "新書",
        "category": "技術書",
    }
    table = Mock()
    table.query.return_value = {
        "Items": [
            {
                "userId": "user-123",
                "isbn": "9781111111111",
                "title": "Python入門",
                "author": "A",
                "bookFormat": "新書",
                "category": "技術書",
                "createdAt": "2026-03-16T12:00:00+00:00",
            },
            {
                "userId": "user-123",
                "isbn": "9782222222222",
                "title": "Python business",
                "author": "B",
                "bookFormat": "単行本",
                "category": "ビジネス",
                "createdAt": "2026-03-15T12:00:00+00:00",
            },
        ]
    }

    with patch.object(get_books_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(get_books_handler.handler(lambda_event, None))

    assert status_code == 200
    assert len(body["items"]) == 1
    assert body["items"][0]["isbn"] == "9781111111111"


def test_get_books_search_matches_author(lambda_event: dict[str, object]) -> None:
    lambda_event["queryStringParameters"] = {"q": "suzuki"}
    table = Mock()
    table.query.return_value = {
        "Items": [
            {
                "userId": "user-123",
                "isbn": "9781111111111",
                "title": "統計の本",
                "author": "Taro Suzuki",
                "createdAt": "2026-03-16T12:00:00+00:00",
            },
            {
                "userId": "user-123",
                "isbn": "9782222222222",
                "title": "別の本",
                "author": "Hanako Sato",
                "createdAt": "2026-03-15T12:00:00+00:00",
            },
        ]
    }

    with patch.object(get_books_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(get_books_handler.handler(lambda_event, None))

    assert status_code == 200
    assert [item["isbn"] for item in body["items"]] == ["9781111111111"]


def test_get_books_returns_sorted_items(lambda_event: dict[str, object]) -> None:
    table = Mock()
    table.query.return_value = {
        "Items": [
            {
                "userId": "user-123",
                "isbn": "1",
                "title": "Older",
                "createdAt": "2026-03-15T00:00:00+00:00",
            },
            {
                "userId": "user-123",
                "isbn": "2",
                "title": "Newer",
                "createdAt": "2026-03-16T00:00:00+00:00",
            },
        ]
    }

    with patch.object(get_books_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(get_books_handler.handler(lambda_event, None))

    assert status_code == 200
    assert [item["isbn"] for item in body["items"]] == ["2", "1"]
