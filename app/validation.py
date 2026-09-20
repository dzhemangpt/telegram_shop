"""Deterministic validators for checkout input."""

import re


def valid_name(text: str | None) -> bool:
    return bool(text and 1 <= len(text.strip()) <= 25 and not text.strip().startswith("/"))


def normalize_phone(text: str | None) -> str | None:
    if text is None:
        return None
    value = text.strip()
    if re.fullmatch(r"(?:\+7|8)[0-9]{10}", value):
        return "+7" + value[-10:]
    return None


def valid_email(text: str | None) -> bool:
    if not text:
        return False
    value = text.strip()
    if len(value) > 50 or value.count("@") != 1:
        return False
    local, domain = value.split("@")
    if not re.fullmatch(r"[a-zA-Z0-9_+.-]+", local):
        return False
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    labels = domain.split(".")
    return (
        len(labels) >= 2
        and bool(re.fullmatch(r"[a-zA-Z]{2,}", labels[-1]))
        and all(
            re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
            for label in labels
        )
    )
