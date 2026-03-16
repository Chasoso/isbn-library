from typing import Any


def get_user_id(event: dict[str, Any]) -> str:
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    )
    user_id = claims.get("sub")

    if not user_id:
        raise ValueError("Missing user identity")

    return user_id
