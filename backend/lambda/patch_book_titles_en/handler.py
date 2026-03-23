from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from botocore.exceptions import ClientError

from shared.dynamo import get_books_table
from shared.logging_utils import log_request, log_response
from shared.responses import json_response
from shared.title_en import resolve_english_title

UNRESOLVED_STATUSES = {"", "none", "pending", "failed"}


def normalize_limit(raw_limit: Any) -> int:
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return 50
    return max(1, min(limit, 200))


def normalize_next_key(raw_next_key: Any) -> dict[str, Any] | None:
    if not isinstance(raw_next_key, dict):
        return None
    user_id = str(raw_next_key.get("userId", "")).strip()
    isbn = str(raw_next_key.get("isbn", "")).strip()
    if not user_id or not isbn:
        return None
    return {"userId": user_id, "isbn": isbn}


def preview_item(item: dict[str, Any], metadata: dict[str, str] | None = None) -> dict[str, Any]:
    preview = {
        "userId": item.get("userId", ""),
        "isbn": item.get("isbn", ""),
        "title": item.get("title", ""),
        "titleEn": item.get("titleEn", ""),
        "titleEnStatus": item.get("titleEnStatus", ""),
        "titleEnSource": item.get("titleEnSource", ""),
    }
    if metadata is not None:
        preview["resolvedTitleEn"] = metadata.get("titleEn", "")
        preview["resolvedTitleEnStatus"] = metadata.get("titleEnStatus", "")
        preview["resolvedTitleEnSource"] = metadata.get("titleEnSource", "")
    return preview


def should_patch_book_title_en(item: dict[str, Any]) -> bool:
    source = str(item.get("titleEnSource", "")).strip().lower()
    status = str(item.get("titleEnStatus", "")).strip().lower()
    title_en = str(item.get("titleEn", "")).strip()

    if source == "manual" or status == "manual":
        return False
    if title_en and status not in UNRESOLVED_STATUSES:
        return False
    return not title_en or status in UNRESOLVED_STATUSES


def build_update_expression(metadata: dict[str, str]) -> tuple[str, dict[str, str], dict[str, str]]:
    return (
        "SET #titleEn = :titleEn, #titleEnSource = :titleEnSource, "
        "#titleEnStatus = :titleEnStatus, #titleEnUpdatedAt = :titleEnUpdatedAt, "
        "#patchedAt = :patchedAt, #patchVersion = :patchVersion",
        {
            "#titleEn": "titleEn",
            "#titleEnSource": "titleEnSource",
            "#titleEnStatus": "titleEnStatus",
            "#titleEnUpdatedAt": "titleEnUpdatedAt",
            "#patchedAt": "patchedAt",
            "#patchVersion": "patchVersion",
        },
        {
            ":titleEn": metadata["titleEn"],
            ":titleEnSource": metadata["titleEnSource"],
            ":titleEnStatus": metadata["titleEnStatus"],
            ":titleEnUpdatedAt": metadata["titleEnUpdatedAt"],
            ":patchedAt": datetime.now(timezone.utc).isoformat(),
            ":patchVersion": "titleEn-v1",
        },
    )


def update_book_title_en(table: Any, item: dict[str, Any], metadata: dict[str, str]) -> None:
    update_expression, names, values = build_update_expression(metadata)
    names["#titleEnSource"] = "titleEnSource"
    names["#titleEnStatus"] = "titleEnStatus"
    values[":manualSource"] = "manual"
    values[":manualStatus"] = "manual"
    table.update_item(
        Key={"userId": item["userId"], "isbn": item["isbn"]},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
        ConditionExpression="attribute_not_exists(titleEnSource) OR (#titleEnSource <> :manualSource AND #titleEnStatus <> :manualStatus)",
        ReturnValues="NONE",
    )


def scan_books_page(
    table: Any,
    limit: int,
    exclusive_start_key: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scan_kwargs: dict[str, Any] = {"Limit": limit}
    if exclusive_start_key:
        scan_kwargs["ExclusiveStartKey"] = exclusive_start_key
    return table.scan(**scan_kwargs)


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        log_request("patch_book_titles_en", {"body": event})
        dry_run = bool(event.get("dryRun", False))
        limit = normalize_limit(event.get("limit"))
        next_key = normalize_next_key(event.get("nextKey"))

        table = get_books_table()
        page = scan_books_page(table, limit, next_key)
        items = page.get("Items", [])

        scanned_count = len(items)
        target_count = 0
        skipped_count = 0
        updated_count = 0
        failed_count = 0
        items_preview: list[dict[str, Any]] = []

        for item in items:
            if not should_patch_book_title_en(item):
                skipped_count += 1
                continue

            target_count += 1
            try:
                metadata = resolve_english_title(
                    {
                        "isbn": item.get("isbn", ""),
                        "title": item.get("title", ""),
                    }
                )
                items_preview.append(preview_item(item, metadata))

                if dry_run:
                    continue

                update_book_title_en(table, item, metadata)
                updated_count += 1
            except ClientError as error:
                failed_count += 1
                print(f"[WARNING] patch_book_titles_en update failed for {item.get('isbn', '')}: {error}")
            except Exception as error:
                failed_count += 1
                print(f"[WARNING] patch_book_titles_en resolution failed for {item.get('isbn', '')}: {error}")

        body = {
            "scannedCount": scanned_count,
            "targetCount": target_count,
            "skippedCount": skipped_count,
            "updatedCount": 0 if dry_run else updated_count,
            "failedCount": failed_count,
            "dryRun": dry_run,
            "nextKey": page.get("LastEvaluatedKey"),
            "itemsPreview": items_preview[:20],
        }
        return log_response("patch_book_titles_en", json_response(200, body))
    except Exception as error:
        return log_response(
            "patch_book_titles_en",
            json_response(500, {"message": f"Failed to patch english titles: {error}"}),
        )
