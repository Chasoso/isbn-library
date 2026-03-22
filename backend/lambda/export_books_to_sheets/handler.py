from __future__ import annotations

import json
import os
from typing import Any

import boto3
import requests
from google.auth import load_credentials_from_dict
from google.auth.transport.requests import Request

from shared.books import to_book_response
from shared.categories import category_response
from shared.constants import (
    GOOGLE_SHEETS_API_BASE_URL,
    GOOGLE_SHEETS_BOOKS_SHEET_NAME_ENV,
    GOOGLE_SHEETS_CATEGORY_VORONOI_SHEET_NAME_ENV,
    GOOGLE_SHEETS_CATEGORIES_SHEET_NAME_ENV,
    GOOGLE_SHEETS_SCOPE,
    GOOGLE_SHEETS_SPREADSHEET_ID_ENV,
    GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME_ENV,
)
from shared.dynamo import get_books_table, get_categories_table
from shared.logging_utils import log_external_api, log_request, log_response
from shared.responses import json_response
from shared.voronoi_export import build_category_voronoi_rows

BOOK_HEADERS = [
    "isbn",
    "title",
    "author",
    "publisher",
    "publishedDate",
    "coverImageUrl",
    "bookFormat",
    "categoryId",
    "categoryName",
    "readingStatus",
    "createdAt",
]

CATEGORY_HEADERS = [
    "categoryId",
    "name",
    "sortOrder",
    "color",
    "createdAt",
    "updatedAt",
]


def get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def get_parameter_payload(parameter_name: str) -> dict[str, Any]:
    client = boto3.client("ssm")
    response = client.get_parameter(Name=parameter_name, WithDecryption=True)
    return json.loads(response["Parameter"]["Value"])


def validate_credential_config(credential_config: dict[str, Any]) -> None:
    audience = str(credential_config.get("audience", ""))
    if credential_config.get("type") != "external_account":
        raise ValueError("WIF credential config type must be external_account")
    if not audience.startswith("//iam.googleapis.com/projects/"):
        raise ValueError(
            "WIF credential config audience must start with //iam.googleapis.com/projects/"
        )


def build_access_token(credential_config: dict[str, Any]) -> str:
    validate_credential_config(credential_config)
    credentials, _project_id = load_credentials_from_dict(
        credential_config,
        scopes=[GOOGLE_SHEETS_SCOPE],
    )
    credentials.refresh(Request())
    return credentials.token


def scan_all_items(table: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    scan_kwargs: dict[str, Any] = {}

    while True:
        result = table.scan(**scan_kwargs)
        items.extend(result.get("Items", []))
        last_key = result.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return items


def build_category_map(items: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    category_map: dict[tuple[str, str], str] = {}
    for item in items:
        category = category_response(item)
        category_map[(item["userId"], category["categoryId"])] = category["name"]
    return category_map


def build_books_rows(
    items: list[dict[str, Any]],
    category_map: dict[tuple[str, str], str],
) -> list[list[str]]:
    rows: list[list[str]] = [BOOK_HEADERS]
    sorted_items = sorted(
        items,
        key=lambda item: (
            item.get("createdAt", ""),
            item.get("isbn", ""),
        ),
    )

    for item in sorted_items:
        book = to_book_response(
            item,
            category_name=category_map.get((item["userId"], item.get("categoryId", ""))),
        )
        rows.append([str(book.get(column, "")) for column in BOOK_HEADERS])

    return rows


def build_categories_rows(items: list[dict[str, Any]]) -> list[list[str]]:
    rows: list[list[str]] = [CATEGORY_HEADERS]
    sorted_items = sorted(
        items,
        key=lambda item: (
            int(item.get("sortOrder", 9999)),
            item.get("categoryId", ""),
        ),
    )

    for item in sorted_items:
        category = category_response(item)
        rows.append(
            [
                str(category.get("categoryId", "")),
                str(category.get("name", "")),
                str(category.get("sortOrder", "")),
                str(category.get("color", "")),
                str(category.get("createdAt", "")),
                str(category.get("updatedAt", "")),
            ]
        )

    return rows


def post_google_api(
    operation: str,
    url: str,
    access_token: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=20,
    )

    try:
        response_payload: Any = response.json()
    except ValueError:
        response_payload = response.text

    log_external_api(operation, url, response.status_code, response_payload)
    response.raise_for_status()
    return response_payload if isinstance(response_payload, dict) else {"raw": response_payload}


def clear_sheets(access_token: str, spreadsheet_id: str, ranges: list[str]) -> None:
    post_google_api(
        "google_sheets_batch_clear",
        f"{GOOGLE_SHEETS_API_BASE_URL}/{spreadsheet_id}/values:batchClear",
        access_token,
        {"ranges": ranges},
    )


def update_sheets(
    access_token: str,
    spreadsheet_id: str,
    books_sheet_name: str,
    books_rows: list[list[Any]],
    categories_sheet_name: str,
    categories_rows: list[list[Any]],
    category_voronoi_sheet_name: str,
    category_voronoi_rows: list[list[Any]],
) -> None:
    post_google_api(
        "google_sheets_batch_update",
        f"{GOOGLE_SHEETS_API_BASE_URL}/{spreadsheet_id}/values:batchUpdate",
        access_token,
        {
            "valueInputOption": "RAW",
            "data": [
                {
                    "range": f"{books_sheet_name}!A1",
                    "majorDimension": "ROWS",
                    "values": books_rows,
                },
                {
                    "range": f"{categories_sheet_name}!A1",
                    "majorDimension": "ROWS",
                    "values": categories_rows,
                },
                {
                    "range": f"{category_voronoi_sheet_name}!A1",
                    "majorDimension": "ROWS",
                    "values": category_voronoi_rows,
                },
            ],
        },
    )


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    credential_audience = ""
    try:
        log_request("export_books_to_sheets", event)
        spreadsheet_id = get_env(GOOGLE_SHEETS_SPREADSHEET_ID_ENV)
        parameter_name = get_env(GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME_ENV)
        books_sheet_name = get_env(GOOGLE_SHEETS_BOOKS_SHEET_NAME_ENV, "books")
        categories_sheet_name = get_env(GOOGLE_SHEETS_CATEGORIES_SHEET_NAME_ENV, "categories")
        category_voronoi_sheet_name = get_env(
            GOOGLE_SHEETS_CATEGORY_VORONOI_SHEET_NAME_ENV,
            "category_voronoi",
        )

        if not spreadsheet_id or not parameter_name:
            return log_response(
                "export_books_to_sheets",
                json_response(
                    500,
                    {
                        "message": (
                            "Missing Google Sheets export configuration. "
                            "Set GOOGLE_SHEETS_SPREADSHEET_ID and "
                            "GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME."
                        )
                    },
                ),
            )

        credential_config = get_parameter_payload(parameter_name)
        credential_audience = str(credential_config.get("audience", ""))
        access_token = build_access_token(credential_config)

        category_items = scan_all_items(get_categories_table())
        category_map = build_category_map(category_items)
        book_items = scan_all_items(get_books_table())

        books_rows = build_books_rows(book_items, category_map)
        categories_rows = build_categories_rows(category_items)
        category_voronoi_rows = build_category_voronoi_rows(category_items, book_items)

        clear_sheets(
            access_token,
            spreadsheet_id,
            [
                f"{books_sheet_name}!A:Z",
                f"{categories_sheet_name}!A:Z",
                f"{category_voronoi_sheet_name}!A:R",
            ],
        )
        update_sheets(
            access_token,
            spreadsheet_id,
            books_sheet_name,
            books_rows,
            categories_sheet_name,
            categories_rows,
            category_voronoi_sheet_name,
            category_voronoi_rows,
        )

        return log_response(
            "export_books_to_sheets",
            json_response(
                200,
                {
                    "message": "Books exported to Google Sheets",
                    "booksCount": max(len(books_rows) - 1, 0),
                    "categoriesCount": max(len(categories_rows) - 1, 0),
                    "categoryVoronoiPointCount": max(len(category_voronoi_rows) - 1, 0),
                    "booksSheetName": books_sheet_name,
                    "categoriesSheetName": categories_sheet_name,
                    "categoryVoronoiSheetName": category_voronoi_sheet_name,
                },
            ),
        )
    except Exception as error:
        message = f"Failed to export books to Google Sheets: {error}"
        if "invalid_target" in str(error):
            message = (
                "Failed to export books to Google Sheets: invalid_target from Google STS. "
                "Check that the WIF audience matches an existing and enabled pool/provider. "
                f"audience={credential_audience}"
            )
        return log_response(
            "export_books_to_sheets",
            json_response(500, {"message": message}),
        )
