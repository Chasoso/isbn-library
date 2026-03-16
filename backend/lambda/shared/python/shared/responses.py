import json
from typing import Any


def json_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def empty_response(status_code: int = 204) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {},
        "body": "",
    }
