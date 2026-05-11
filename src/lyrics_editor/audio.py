from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from mutagen import File

from lyrics_editor.models import TrackMetadata

SUPPORTED_AUDIO_EXTENSIONS = {
    ".aac",
    ".aiff",
    ".alac",
    ".ape",
    ".flac",
    ".m4a",
    ".mp3",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
}


def iter_audio_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        if root.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS:
            yield root
        return

    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS:
            yield path


def read_metadata(path: Path) -> TrackMetadata:
    audio = File(path, easy=True)
    if audio is None:
        return TrackMetadata(path=path)

    tags = audio.tags or {}
    title = _first(tags.get("title"))
    artists = tuple(_split_artists(tags.get("artist") or tags.get("artists")))
    album = _first(tags.get("album"))
    duration = float(audio.info.length) if getattr(audio, "info", None) else None

    return TrackMetadata(
        path=path,
        title=title,
        artists=artists,
        album=album,
        duration=duration,
    )


def _first(value: list[str] | tuple[str, ...] | str | None) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if value:
        return str(value[0]).strip() or None
    return None


def _split_artists(value: list[str] | tuple[str, ...] | str | None) -> Iterable[str]:
    first = _first(value)
    if not first:
        return ()
    normalized = first.replace("；", ";").replace("、", ";").replace("/", ";")
    return tuple(part.strip() for part in normalized.split(";") if part.strip())

