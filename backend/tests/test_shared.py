from __future__ import annotations

from shared.books import to_book_response
from shared.isbn import normalize_isbn


def test_normalize_isbn_accepts_ean13() -> None:
    assert normalize_isbn("978-4-86064-811-4") == "9784860648114"


def test_normalize_isbn_rejects_invalid() -> None:
    assert normalize_isbn("123") is None


def test_to_book_response_defaults_classification() -> None:
    response = to_book_response(
        {
            "userId": "user-123",
            "isbn": "9784860648114",
            "title": "Book",
        }
    )

    assert response["bookFormat"] == "その他"
    assert response["category"] == "その他"
