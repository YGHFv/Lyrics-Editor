from __future__ import annotations

import re

from lyrics_editor.models import LyricLine, Lyrics

TIME_TAG_RE = re.compile(r"\[(?P<minutes>\d{1,3}):(?P<seconds>\d{2})(?:\.(?P<fraction>\d{1,3}))?\]")


def parse_lrc(text: str) -> tuple[LyricLine, ...]:
    lines: list[LyricLine] = []
    for raw_line in text.splitlines():
        matches = list(TIME_TAG_RE.finditer(raw_line))
        if not matches:
            continue
        lyric_text = TIME_TAG_RE.sub("", raw_line).strip()
        for match in matches:
            lines.append(LyricLine(start=_tag_to_seconds(match), text=lyric_text))

    sorted_lines = sorted(lines, key=lambda item: item.start)
    with_end: list[LyricLine] = []
    for index, line in enumerate(sorted_lines):
        next_start = sorted_lines[index + 1].start if index + 1 < len(sorted_lines) else None
        with_end.append(LyricLine(start=line.start, end=next_start, text=line.text))
    return tuple(with_end)


def lyrics_from_lrc(
    *,
    source: str,
    title: str,
    artist: str,
    text: str,
    album: str | None = None,
    duration: float | None = None,
    provider_id: str | None = None,
) -> Lyrics:
    return Lyrics(
        source=source,
        title=title,
        artist=artist,
        album=album,
        duration=duration,
        synced_text=text,
        lines=parse_lrc(text),
        provider_id=provider_id,
    )


def to_lrc(lyrics: Lyrics) -> str:
    if lyrics.synced_text and not lyrics.lines:
        return lyrics.synced_text.strip() + "\n"

    header = [
        f"[ti:{lyrics.title}]",
        f"[ar:{lyrics.artist}]",
    ]
    if lyrics.album:
        header.append(f"[al:{lyrics.album}]")
    header.append(f"[by:{lyrics.source}]")

    body = [f"{_seconds_to_tag(line.start)}{line.text}" for line in lyrics.lines]
    return "\n".join([*header, *body]).strip() + "\n"


def _tag_to_seconds(match: re.Match[str]) -> float:
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds"))
    fraction = match.group("fraction") or "0"
    milliseconds = int(fraction.ljust(3, "0")[:3])
    return minutes * 60 + seconds + milliseconds / 1000


def _seconds_to_tag(seconds: float) -> str:
    minutes = int(seconds // 60)
    rest = seconds - minutes * 60
    whole_seconds = int(rest)
    hundredths = int(round((rest - whole_seconds) * 100))
    if hundredths == 100:
        whole_seconds += 1
        hundredths = 0
    return f"[{minutes:02d}:{whole_seconds:02d}.{hundredths:02d}]"

