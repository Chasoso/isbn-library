from __future__ import annotations

from unittest.mock import Mock, patch

from conftest import load_handler_module, parse_response


patch_titles_handler = load_handler_module("patch_book_titles_en")


def make_book(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "userId": "user-123",
        "isbn": "9784860648114",
        "title": "サンプル",
    }
    item.update(overrides)
    return item


def test_should_patch_book_title_en_targets_missing_title_en() -> None:
    assert patch_titles_handler.should_patch_book_title_en(make_book())
    assert patch_titles_handler.should_patch_book_title_en(make_book(titleEn="", titleEnStatus="failed"))


def test_should_patch_book_title_en_skips_manual() -> None:
    assert not patch_titles_handler.should_patch_book_title_en(
        make_book(titleEn="Sample", titleEnSource="manual", titleEnStatus="manual")
    )


def test_patch_book_titles_en_updates_target_books() -> None:
    table = Mock()
    table.scan.return_value = {"Items": [make_book()]}

    with (
        patch.object(patch_titles_handler, "get_books_table", return_value=table),
        patch.object(
            patch_titles_handler,
            "resolve_english_title",
            return_value={
                "titleEn": "Sample Book",
                "titleEnSource": "external_metadata",
                "titleEnStatus": "resolved",
                "titleEnUpdatedAt": "2026-03-23T00:00:00+00:00",
            },
        ),
    ):
        status_code, body = parse_response(
            patch_titles_handler.handler({"dryRun": False, "limit": 50}, None)
        )

    assert status_code == 200
    assert body["targetCount"] == 1
    assert body["updatedCount"] == 1
    table.update_item.assert_called_once()


def test_patch_book_titles_en_skips_manual_books() -> None:
    table = Mock()
    table.scan.return_value = {
        "Items": [make_book(titleEn="Sample", titleEnSource="manual", titleEnStatus="manual")]
    }

    with patch.object(patch_titles_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(
            patch_titles_handler.handler({"dryRun": False, "limit": 50}, None)
        )

    assert status_code == 200
    assert body["targetCount"] == 0
    assert body["skippedCount"] == 1
    table.update_item.assert_not_called()


def test_patch_book_titles_en_uses_translation_fallback() -> None:
    table = Mock()
    table.scan.return_value = {"Items": [make_book()]}

    with (
        patch.object(patch_titles_handler, "get_books_table", return_value=table),
        patch.object(
            patch_titles_handler,
            "resolve_english_title",
            return_value={
                "titleEn": "Translated Sample",
                "titleEnSource": "machine_translation",
                "titleEnStatus": "resolved",
                "titleEnUpdatedAt": "2026-03-23T00:00:00+00:00",
            },
        ),
    ):
        status_code, body = parse_response(
            patch_titles_handler.handler({"dryRun": False, "limit": 50}, None)
        )

    assert status_code == 200
    assert body["updatedCount"] == 1
    assert body["itemsPreview"][0]["resolvedTitleEnSource"] == "machine_translation"


def test_patch_book_titles_en_continues_when_resolution_fails() -> None:
    table = Mock()
    table.scan.return_value = {
        "Items": [
            make_book(isbn="9784860648114"),
            make_book(isbn="9784873113685"),
        ]
    }

    def resolve_side_effect(payload: dict[str, object]) -> dict[str, str]:
        if payload["isbn"] == "9784860648114":
            raise RuntimeError("boom")
        return {
            "titleEn": "Recovered",
            "titleEnSource": "machine_translation",
            "titleEnStatus": "resolved",
            "titleEnUpdatedAt": "2026-03-23T00:00:00+00:00",
        }

    with (
        patch.object(patch_titles_handler, "get_books_table", return_value=table),
        patch.object(patch_titles_handler, "resolve_english_title", side_effect=resolve_side_effect),
    ):
        status_code, body = parse_response(
            patch_titles_handler.handler({"dryRun": False, "limit": 50}, None)
        )

    assert status_code == 200
    assert body["failedCount"] == 1
    assert body["updatedCount"] == 1


def test_patch_book_titles_en_respects_dry_run() -> None:
    table = Mock()
    table.scan.return_value = {"Items": [make_book()]}

    with (
        patch.object(patch_titles_handler, "get_books_table", return_value=table),
        patch.object(
            patch_titles_handler,
            "resolve_english_title",
            return_value={
                "titleEn": "Sample Book",
                "titleEnSource": "external_metadata",
                "titleEnStatus": "resolved",
                "titleEnUpdatedAt": "2026-03-23T00:00:00+00:00",
            },
        ),
    ):
        status_code, body = parse_response(
            patch_titles_handler.handler({"dryRun": True, "limit": 50}, None)
        )

    assert status_code == 200
    assert body["dryRun"] is True
    assert body["updatedCount"] == 0
    table.update_item.assert_not_called()


def test_patch_book_titles_en_limit_and_next_key() -> None:
    table = Mock()
    table.scan.return_value = {
        "Items": [make_book(), make_book(isbn="9784873113685")],
        "LastEvaluatedKey": {"userId": "user-123", "isbn": "9784873113685"},
    }

    with (
        patch.object(patch_titles_handler, "get_books_table", return_value=table),
        patch.object(
            patch_titles_handler,
            "resolve_english_title",
            return_value={
                "titleEn": "Sample Book",
                "titleEnSource": "external_metadata",
                "titleEnStatus": "resolved",
                "titleEnUpdatedAt": "2026-03-23T00:00:00+00:00",
            },
        ),
    ):
        status_code, body = parse_response(
            patch_titles_handler.handler({"dryRun": True, "limit": 2}, None)
        )

    assert status_code == 200
    assert body["scannedCount"] == 2
    assert body["nextKey"] == {"userId": "user-123", "isbn": "9784873113685"}
    table.scan.assert_called_once_with(Limit=2)


def test_patch_book_titles_en_uses_next_key_for_pagination() -> None:
    table = Mock()
    table.scan.return_value = {"Items": []}

    with patch.object(patch_titles_handler, "get_books_table", return_value=table):
        status_code, _body = parse_response(
            patch_titles_handler.handler(
                {
                    "dryRun": True,
                    "limit": 10,
                    "nextKey": {"userId": "user-123", "isbn": "9784860648114"},
                },
                None,
            )
        )

    assert status_code == 200
    table.scan.assert_called_once_with(
        Limit=10,
        ExclusiveStartKey={"userId": "user-123", "isbn": "9784860648114"},
    )


def test_patch_book_titles_en_is_idempotent_for_resolved_titles() -> None:
    table = Mock()
    table.scan.return_value = {
        "Items": [make_book(titleEn="Sample Book", titleEnSource="external_metadata", titleEnStatus="resolved")]
    }

    with patch.object(patch_titles_handler, "get_books_table", return_value=table):
        status_code, body = parse_response(
            patch_titles_handler.handler({"dryRun": False, "limit": 50}, None)
        )

    assert status_code == 200
    assert body["targetCount"] == 0
    assert body["skippedCount"] == 1
    table.update_item.assert_not_called()
