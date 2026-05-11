from __future__ import annotations

import unicodedata

SEPARATORS = {" ", "\t", "\r", "\n", "-", "_"}


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "".join(
        char
        for char in normalized
        if char not in SEPARATORS and not unicodedata.category(char).startswith("P")
    )


def lyric_line_tokens(text: str) -> list[str]:
    normalized = _normalize_for_tokens(text)
    if not normalized:
        return []
    if _looks_cjk(normalized):
        return [char for char in normalized if not char.isspace()]
    return normalized.split()


def _looks_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _normalize_for_tokens(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "".join(
        " " if char in SEPARATORS or unicodedata.category(char).startswith("P") else char
        for char in normalized
    )
