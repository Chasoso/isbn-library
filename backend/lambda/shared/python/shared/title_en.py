from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import boto3

from shared.constants import GOOGLE_BOOKS_API_KEY_ENV, GOOGLE_BOOKS_API_URL
from shared.logging_utils import log_external_api

_JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")
_ASCII_ALPHA_RE = re.compile(r"[A-Za-z]")
_NON_ALNUM_RE = re.compile(r"[\W_]+", re.UNICODE)


def build_title_en_metadata(
    title_en: str,
    source: str,
    status: str,
    updated_at: str | None = None,
) -> dict[str, str]:
    return {
        "titleEn": title_en.strip(),
        "titleEnSource": source,
        "titleEnStatus": status,
        "titleEnUpdatedAt": updated_at or datetime.now(timezone.utc).isoformat(),
    }


def looks_like_english_title(title: str) -> bool:
    normalized = title.strip()
    if not normalized:
        return False
    if _JAPANESE_RE.search(normalized):
        return False
    alpha_count = sum(1 for char in normalized if char.isalpha() and char.isascii())
    return alpha_count >= max(3, len(normalized) // 3)


def should_skip_translation(title: str) -> bool:
    normalized = title.strip()
    if not normalized:
        return True
    collapsed = _NON_ALNUM_RE.sub("", normalized)
    if not collapsed:
        return True
    if collapsed.isdigit():
        return True
    if looks_like_english_title(normalized):
        return True
    return False


def extract_english_title_from_external_metadata(payload: dict[str, Any]) -> str | None:
    items = payload.get("items") or []
    if not items:
        return None

    volume_info = items[0].get("volumeInfo", {})
    title = str(volume_info.get("title", "")).strip()
    language = str(volume_info.get("language", "")).strip().lower()

    if not title:
        return None
    if language == "en":
        return title
    if looks_like_english_title(title):
        return title
    return None


def fetch_google_books_payload(isbn: str) -> dict[str, Any]:
    query_params = {"q": f"isbn:{isbn}", "maxResults": 1}
    api_key = os.getenv(GOOGLE_BOOKS_API_KEY_ENV, "").strip()
    if api_key:
        query_params["key"] = api_key

    request_url = f"{GOOGLE_BOOKS_API_URL}?{urlencode(query_params)}"
    request = Request(
        request_url,
        headers={
            "User-Agent": "isbn-library/1.0",
            "Accept": "application/json",
        },
    )

    retry_delays = [0.4, 0.8, 1.6]
    for attempt, delay in enumerate(retry_delays, start=1):
        try:
            with urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
                log_external_api(
                    "title_en.google_books",
                    request_url,
                    getattr(response, "status", 200),
                    payload,
                )
                return payload
        except HTTPError as error:
            try:
                error_body = error.read().decode("utf-8", errors="replace")
            except Exception:
                error_body = str(error)
            log_external_api("title_en.google_books", request_url, error.code, error_body)
            if error.code == 429 and attempt < len(retry_delays):
                time.sleep(delay)
                continue
            raise
        except URLError:
            if attempt < len(retry_delays):
                time.sleep(delay)
                continue
            raise

    raise RuntimeError("Failed to fetch Google Books payload")


def resolve_english_title_from_external_metadata(isbn: str) -> str | None:
    if not isbn:
        return None
    payload = fetch_google_books_payload(isbn)
    return extract_english_title_from_external_metadata(payload)


def translate_title_to_english(title: str) -> str | None:
    normalized = title.strip()
    if should_skip_translation(normalized):
        return normalized if looks_like_english_title(normalized) else None

    translate = boto3.client("translate")
    response = translate.translate_text(
        Text=normalized,
        SourceLanguageCode="ja",
        TargetLanguageCode="en",
    )
    translated = str(response.get("TranslatedText", "")).strip()
    return translated or None


def resolve_english_title(payload: dict[str, Any]) -> dict[str, str]:
    manual_title_en = str(payload.get("titleEn", "")).strip()
    if manual_title_en:
        return build_title_en_metadata(manual_title_en, "manual", "manual")

    title = str(payload.get("title", "")).strip()
    isbn = str(payload.get("isbn", "")).strip()

    try:
        resolved_external = resolve_english_title_from_external_metadata(isbn)
        if resolved_external:
            return build_title_en_metadata(
                resolved_external,
                "external_metadata",
                "resolved",
            )
    except Exception as error:
        print(f"[WARNING] title_en external metadata lookup failed: {error}")

    if looks_like_english_title(title):
        return build_title_en_metadata(title, "none", "resolved")

    try:
        translated = translate_title_to_english(title)
        if translated:
            return build_title_en_metadata(
                translated,
                "machine_translation",
                "resolved",
            )
    except Exception as error:
        print(f"[WARNING] title_en translation failed: {error}")

    return build_title_en_metadata("", "none", "failed")
