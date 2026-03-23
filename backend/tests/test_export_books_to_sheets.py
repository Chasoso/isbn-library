from __future__ import annotations

from unittest.mock import Mock, patch

from conftest import load_handler_module, parse_response


export_handler = load_handler_module("export_books_to_sheets")


def test_export_books_to_sheets_writes_books_and_categories(
    lambda_event: dict[str, object],
) -> None:
    books_table = Mock()
    books_table.scan.side_effect = [
        {
            "Items": [
                {
                    "userId": "user-123",
                    "isbn": "9784860648114",
                    "title": "Book",
                    "titleEn": "Book",
                    "author": "Author",
                    "categoryId": "technology",
                    "createdAt": "2026-03-21T00:00:00+00:00",
                }
            ]
        }
    ]
    categories_table = Mock()
    categories_table.scan.side_effect = [
        {
            "Items": [
                {
                    "userId": "user-123",
                    "categoryId": "technology",
                    "name": "Technology",
                    "sortOrder": 10,
                    "color": "#4C8BF5",
                    "createdAt": "2026-03-20T00:00:00+00:00",
                    "updatedAt": "2026-03-20T00:00:00+00:00",
                }
            ]
        }
    ]

    fake_credentials = Mock()
    fake_credentials.token = "token-123"

    def fake_post(url, headers=None, json=None, timeout=None):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"ok": True, "url": url, "payload": json}
        response.raise_for_status.return_value = None
        return response

    with (
        patch.dict(
            "os.environ",
            {
                "GOOGLE_SHEETS_SPREADSHEET_ID": "spreadsheet-123",
                "GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME": "/isbn-library/google-wif-config",
                "GOOGLE_SHEETS_BOOKS_SHEET_NAME": "books",
                "GOOGLE_SHEETS_CATEGORIES_SHEET_NAME": "categories",
                "GOOGLE_SHEETS_CATEGORY_VORONOI_SHEET_NAME": "category_voronoi",
            },
            clear=False,
        ),
        patch.object(export_handler, "get_books_table", return_value=books_table),
        patch.object(export_handler, "get_categories_table", return_value=categories_table),
        patch.object(
            export_handler,
            "get_parameter_payload",
            return_value={"type": "external_account", "audience": "//iam.googleapis.com/projects/1/locations/global/workloadIdentityPools/pool/providers/aws"},
        ),
        patch.object(
            export_handler,
            "load_credentials_from_dict",
            return_value=(fake_credentials, "project-id"),
        ) as credentials_factory,
        patch.object(export_handler.requests, "post", side_effect=fake_post) as post_mock,
    ):
        status_code, body = parse_response(export_handler.handler(lambda_event, None))

    assert status_code == 200
    assert body["booksCount"] == 1
    assert body["categoriesCount"] == 1
    assert body["categoryVoronoiSheetName"] == "category_voronoi"
    assert body["categoryVoronoiPointCount"] > 0
    credentials_factory.assert_called_once()
    fake_credentials.refresh.assert_called_once()
    assert post_mock.call_count == 2

    clear_payload = post_mock.call_args_list[0].kwargs["json"]
    update_payload = post_mock.call_args_list[1].kwargs["json"]
    assert clear_payload == {
        "ranges": ["books!A:Z", "categories!A:Z", "category_voronoi!A:Y"]
    }
    assert update_payload["data"][0]["range"] == "books!A1"
    assert update_payload["data"][1]["range"] == "categories!A1"
    assert update_payload["data"][2]["range"] == "category_voronoi!A1"
    assert update_payload["data"][0]["values"][0][0] == "isbn"
    assert "userId" not in update_payload["data"][0]["values"][0]
    assert "userId" not in update_payload["data"][1]["values"][0]
    assert update_payload["data"][0]["values"][1][0] == "9784860648114"
    assert update_payload["data"][0]["values"][1][1] == "Book"
    assert update_payload["data"][0]["values"][1][2] == "Book"
    assert update_payload["data"][0]["values"][1][9] == "Technology"
    assert update_payload["data"][2]["values"][0][0] == "polygonId"
    assert update_payload["data"][2]["values"][0][7] == "targetArea"
    assert update_payload["data"][2]["values"][0][11] == "compactness"
    assert update_payload["data"][2]["values"][0][16] == "path"


def test_export_books_to_sheets_handles_paginated_scans(
    lambda_event: dict[str, object],
) -> None:
    books_table = Mock()
    books_table.scan.side_effect = [
        {"Items": [{"userId": "user-123", "isbn": "1", "categoryId": "technology"}], "LastEvaluatedKey": {"isbn": "1"}},
        {"Items": [{"userId": "user-123", "isbn": "2", "categoryId": "technology"}]},
    ]
    categories_table = Mock()
    categories_table.scan.return_value = {
        "Items": [
            {
                "userId": "user-123",
                "categoryId": "technology",
                "name": "Technology",
                "sortOrder": 10,
            }
        ]
    }

    fake_credentials = Mock()
    fake_credentials.token = "token-123"

    with (
        patch.dict(
            "os.environ",
            {
                "GOOGLE_SHEETS_SPREADSHEET_ID": "spreadsheet-123",
                "GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME": "/isbn-library/google-wif-config",
            },
            clear=False,
        ),
        patch.object(export_handler, "get_books_table", return_value=books_table),
        patch.object(export_handler, "get_categories_table", return_value=categories_table),
        patch.object(
            export_handler,
            "get_parameter_payload",
            return_value={
                "type": "external_account",
                "audience": "//iam.googleapis.com/projects/1/locations/global/workloadIdentityPools/pool/providers/aws",
            },
        ),
        patch.object(
            export_handler,
            "load_credentials_from_dict",
            return_value=(fake_credentials, "project-id"),
        ),
        patch.object(export_handler.requests, "post") as post_mock,
    ):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"ok": True}
        response.raise_for_status.return_value = None
        post_mock.side_effect = [response, response]

        status_code, body = parse_response(export_handler.handler(lambda_event, None))

    assert status_code == 200
    assert body["booksCount"] == 2
    assert books_table.scan.call_count == 2


def test_export_books_to_sheets_requires_configuration(
    lambda_event: dict[str, object],
) -> None:
    with patch.dict(
        "os.environ",
        {
            "GOOGLE_SHEETS_SPREADSHEET_ID": "",
            "GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME": "",
        },
        clear=False,
    ):
        status_code, body = parse_response(export_handler.handler(lambda_event, None))

    assert status_code == 500
    assert "Missing Google Sheets export configuration" in body["message"]


def test_export_books_to_sheets_returns_500_when_google_api_fails(
    lambda_event: dict[str, object],
) -> None:
    books_table = Mock()
    books_table.scan.return_value = {"Items": []}
    categories_table = Mock()
    categories_table.scan.return_value = {"Items": []}
    fake_credentials = Mock()
    fake_credentials.token = "token-123"

    response = Mock()
    response.status_code = 500
    response.json.return_value = {"error": {"message": "boom"}}
    response.raise_for_status.side_effect = RuntimeError("boom")

    with (
        patch.dict(
            "os.environ",
            {
                "GOOGLE_SHEETS_SPREADSHEET_ID": "spreadsheet-123",
                "GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME": "/isbn-library/google-wif-config",
            },
            clear=False,
        ),
        patch.object(export_handler, "get_books_table", return_value=books_table),
        patch.object(export_handler, "get_categories_table", return_value=categories_table),
        patch.object(
            export_handler,
            "get_parameter_payload",
            return_value={
                "type": "external_account",
                "audience": "//iam.googleapis.com/projects/1/locations/global/workloadIdentityPools/pool/providers/aws",
            },
        ),
        patch.object(
            export_handler,
            "load_credentials_from_dict",
            return_value=(fake_credentials, "project-id"),
        ),
        patch.object(export_handler.requests, "post", return_value=response),
    ):
        status_code, body = parse_response(export_handler.handler(lambda_event, None))

    assert status_code == 500
    assert "Failed to export books to Google Sheets" in body["message"]


def test_export_books_to_sheets_rejects_invalid_audience_format(
    lambda_event: dict[str, object],
) -> None:
    with (
        patch.dict(
            "os.environ",
            {
                "GOOGLE_SHEETS_SPREADSHEET_ID": "spreadsheet-123",
                "GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME": "/isbn-library/google-wif-config",
            },
            clear=False,
        ),
        patch.object(
            export_handler,
            "get_parameter_payload",
            return_value={"type": "external_account", "audience": "invalid-audience"},
        ),
    ):
        status_code, body = parse_response(export_handler.handler(lambda_event, None))

    assert status_code == 500
    assert "audience must start with //iam.googleapis.com/projects/" in body["message"]


def test_export_books_to_sheets_surfaces_invalid_target_with_audience(
    lambda_event: dict[str, object],
) -> None:
    invalid_target_error = Exception(
        'Error code invalid_target: The target service indicated by the "audience" parameters is invalid.'
    )

    with (
        patch.dict(
            "os.environ",
            {
                "GOOGLE_SHEETS_SPREADSHEET_ID": "spreadsheet-123",
                "GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME": "/isbn-library/google-wif-config",
            },
            clear=False,
        ),
        patch.object(
            export_handler,
            "get_parameter_payload",
            return_value={
                "type": "external_account",
                "audience": "//iam.googleapis.com/projects/123/locations/global/workloadIdentityPools/pool/providers/provider",
            },
        ),
        patch.object(export_handler, "build_access_token", side_effect=invalid_target_error),
    ):
        status_code, body = parse_response(export_handler.handler(lambda_event, None))

    assert status_code == 500
    assert "invalid_target from Google STS" in body["message"]
    assert "audience=//iam.googleapis.com/projects/123/locations/global/workloadIdentityPools/pool/providers/provider" in body["message"]


def test_build_category_voronoi_rows_returns_full_semicircle_for_single_category() -> None:
    rows = export_handler.build_category_voronoi_rows(
        [
            {
                "userId": "user-123",
                "categoryId": "technology",
                "name": "Technology",
                "sortOrder": 10,
                "color": "#4C8BF5",
            }
        ],
        [
            {
                "userId": "user-123",
                "isbn": "9784860648114",
                "categoryId": "technology",
            }
        ],
    )

    assert rows[0][0] == "polygonId"
    assert len(rows) > 50
    assert all(row[1] == "technology" for row in rows[1:])
    assert rows[1][16] == 0
    assert rows[-1][16] == len(rows) - 2
    assert rows[1][17] == rows[-1][17]
    assert rows[1][18] == rows[-1][18]
    assert abs(rows[1][7] - rows[1][8]) < 2.0
    assert rows[1][10] < 0.001
    assert rows[1][11] > 0


def test_build_category_voronoi_rows_supports_multiple_categories_with_zero_count() -> None:
    rows = export_handler.build_category_voronoi_rows(
        [
            {
                "userId": "user-123",
                "categoryId": "business",
                "name": "Business",
                "sortOrder": 20,
                "color": "#F28C6C",
            },
            {
                "userId": "user-123",
                "categoryId": "technology",
                "name": "Technology",
                "sortOrder": 10,
                "color": "#4C8BF5",
            },
        ],
        [
            {
                "userId": "user-123",
                "isbn": "9784860648114",
                "categoryId": "technology",
            }
        ],
    )

    polygon_rows = rows[1:]
    category_ids = {row[1] for row in polygon_rows}
    assert category_ids == {"technology"}

    grouped_paths: dict[str, list[int]] = {}
    for row in polygon_rows:
        grouped_paths.setdefault(row[0], []).append(row[16])

    for paths in grouped_paths.values():
        assert paths == list(range(len(paths)))

    business_rows = [row for row in polygon_rows if row[1] == "business"]
    technology_rows = [row for row in polygon_rows if row[1] == "technology"]
    assert business_rows == []
    assert technology_rows[0][5] == 1
    assert technology_rows[0][10] <= 0.28
