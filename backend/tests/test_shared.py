from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from shared.auth import get_user_id
from shared.books import to_book_response
from shared.catalog import DEFAULT_BOOK_FORMAT, DEFAULT_CATEGORY_ID, DEFAULT_CATEGORY_NAME
from shared.constants import BOOKS_TABLE_NAME_ENV, CATEGORIES_TABLE_NAME_ENV
from shared.dynamo import get_books_table, get_categories_table
from shared.isbn import normalize_isbn
from shared.responses import empty_response
from shared.statuses import DEFAULT_READING_STATUS


def test_normalize_isbn_accepts_ean13() -> None:
    assert normalize_isbn("978-4-86064-811-4") == "9784860648114"


def test_normalize_isbn_accepts_isbn10() -> None:
    assert normalize_isbn("4-87311-368-0") == "4873113680"


def test_normalize_isbn_rejects_invalid() -> None:
    assert normalize_isbn("123") is None


def test_to_book_response_defaults_classification_and_status() -> None:
    response = to_book_response(
        {
            "userId": "user-123",
            "isbn": "9784860648114",
            "title": "Book",
        }
    )

    assert response["bookFormat"] == DEFAULT_BOOK_FORMAT
    assert response["categoryId"] == DEFAULT_CATEGORY_ID
    assert response["categoryName"] == DEFAULT_CATEGORY_NAME
    assert response["readingStatus"] == DEFAULT_READING_STATUS


def test_get_user_id_raises_when_claim_missing() -> None:
    with pytest.raises(ValueError, match="Missing user identity"):
        get_user_id({})


def test_get_books_table_uses_environment_and_dynamodb_resource() -> None:
    fake_table = Mock()
    fake_resource = Mock()
    fake_resource.Table.return_value = fake_table

    with patch.dict("os.environ", {BOOKS_TABLE_NAME_ENV: "books-test"}, clear=False), patch(
        "shared.dynamo.get_dynamodb_resource", return_value=fake_resource
    ):
        table = get_books_table()

    assert table is fake_table
    fake_resource.Table.assert_called_once_with("books-test")


def test_get_categories_table_uses_environment_and_dynamodb_resource() -> None:
    fake_table = Mock()
    fake_resource = Mock()
    fake_resource.Table.return_value = fake_table

    with patch.dict(
        "os.environ",
        {CATEGORIES_TABLE_NAME_ENV: "categories-test"},
        clear=False,
    ), patch("shared.dynamo.get_dynamodb_resource", return_value=fake_resource):
        table = get_categories_table()

    assert table is fake_table
    fake_resource.Table.assert_called_once_with("categories-test")


def test_empty_response_defaults_to_204() -> None:
    response = empty_response()

    assert response["statusCode"] == 204
    assert response["headers"] == {}
    assert response["body"] == ""
