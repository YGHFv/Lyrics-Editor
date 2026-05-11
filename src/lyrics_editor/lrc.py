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
    merged: list[LyricLine] = []
    for line in sorted_lines:
        if merged and merged[-1].start == line.start:
            last = merged[-1]
            translation = _merge_translation(last.translation, line.text)
            merged[-1] = LyricLine(
                start=last.start,
                end=last.end,
                text=last.text,
                translation=translation,
            )
            continue
        merged.append(line)

    with_end: list[LyricLine] = []
    for index, line in enumerate(merged):
        next_start = merged[index + 1].start if index + 1 < len(merged) else None
        with_end.append(
            LyricLine(
                start=line.start,
                end=next_start,
                text=line.text,
                translation=line.translation,
            )
        )
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


def lyrics_preview(
    lyrics: Lyrics,
    max_lines: int | None = 3,
    max_chars: int | None = 120,
    *,
    show_translation: bool = False,
) -> str:
    source_text = _preview_source_text(lyrics, show_translation=show_translation)
    if not source_text:
        return ""

    lines = [line.strip() for line in source_text.splitlines() if line.strip()]
    if max_lines is None:
        preview = "\n".join(lines)
    else:
        preview = " | ".join(lines[:max_lines])
    if max_chars is not None and len(preview) > max_chars:
        return preview[: max(0, max_chars - 1)].rstrip() + "…"
    return preview


def to_lrc(lyrics: Lyrics, *, show_translation: bool = False) -> str:
    if lyrics.lines:
        header = [
            f"[ti:{lyrics.title}]",
            f"[ar:{lyrics.artist}]",
        ]
        if lyrics.album:
            header.append(f"[al:{lyrics.album}]")
        header.append(f"[by:{lyrics.source}]")

        body: list[str] = []
        for line in lyrics.lines:
            body.append(f"{_seconds_to_tag(line.start)}{line.text}")
            if show_translation and line.translation:
                body.append(f"{_seconds_to_tag(line.start)}{line.translation}")
        return "\n".join([*header, *body]).strip() + "\n"

    if lyrics.words:
        header = [
            f"[ti:{lyrics.title}]",
            f"[ar:{lyrics.artist}]",
        ]
        if lyrics.album:
            header.append(f"[al:{lyrics.album}]")
        header.append(f"[by:{lyrics.source}]")

        body = [f"{_seconds_to_tag(word.start)}{word.text}" for word in lyrics.words]
        return "\n".join([*header, *body]).strip() + "\n"

    if lyrics.synced_text:
        return lyrics.synced_text.strip() + "\n"
    if lyrics.plain_text and not lyrics.lines:
        return lyrics.plain_text.strip() + "\n"
    return ""


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


def _preview_source_text(lyrics: Lyrics, *, show_translation: bool) -> str:
    if lyrics.lines:
        rendered: list[str] = []
        previous: str | None = None
        for line in lyrics.lines:
            rendered_line = _render_preview_line(line, show_translation=show_translation)
            if rendered_line == previous:
                continue
            rendered.append(rendered_line)
            previous = rendered_line
        return "\n".join(rendered)
    if lyrics.words:
        rendered = []
        previous: str | None = None
        for word in lyrics.words:
            rendered_line = f"{_seconds_to_tag(word.start)} {word.text}".rstrip()
            if rendered_line == previous:
                continue
            rendered.append(rendered_line)
            previous = rendered_line
        return "\n".join(rendered)
    if lyrics.synced_text:
        return lyrics.synced_text
    if lyrics.plain_text:
        return lyrics.plain_text
    return ""


def _render_preview_line(line: LyricLine, *, show_translation: bool) -> str:
    text = line.text.strip()
    if show_translation and line.translation:
        translation = line.translation.strip()
        if translation and translation != text:
            text = f"{text} | {translation}"
    return f"{_seconds_to_tag(line.start)} {text}".rstrip()


def _merge_translation(existing: str | None, new_text: str) -> str | None:
    if not existing:
        return new_text
    return existing + "\n" + new_text
