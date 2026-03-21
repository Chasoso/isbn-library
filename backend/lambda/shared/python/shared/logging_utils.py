from __future__ import annotations

import json
from typing import Any


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _parse_body(body: Any) -> Any:
    if body in (None, ""):
        return None
    if isinstance(body, (dict, list)):
        return body
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body
    return body


def log_request(name: str, event: dict[str, Any], user_id: str | None = None) -> None:
    payload = {
        "operation": name,
        "request": {
            "method": (event.get("requestContext", {}).get("http", {}) or {}).get("method"),
            "path": (event.get("requestContext", {}).get("http", {}) or {}).get("path"),
            "pathParameters": event.get("pathParameters") or {},
            "queryStringParameters": event.get("queryStringParameters") or {},
            "body": _parse_body(event.get("body")),
            "userId": user_id,
        },
    }
    print(f"[REQUEST] {_safe_json(payload)}")


def log_response(name: str, response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body", "")
    payload = {
        "operation": name,
        "response": {
            "statusCode": response.get("statusCode"),
            "headers": response.get("headers", {}),
            "body": _parse_body(body),
        },
    }
    print(f"[RESPONSE] {_safe_json(payload)}")
    return response


def log_external_api(name: str, url: str, status_code: int, payload: Any) -> None:
    print(
        f"[EXTERNAL_API] {_safe_json({'operation': name, 'url': url, 'statusCode': status_code, 'payload': payload})}"
    )
