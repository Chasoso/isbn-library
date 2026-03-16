import re


def normalize_isbn(raw_value: str) -> str | None:
    digits = re.sub(r"[^0-9Xx]", "", raw_value).upper()

    if len(digits) == 13 and (digits.startswith("978") or digits.startswith("979")):
        return digits

    if len(digits) == 10:
        return digits

    return None
