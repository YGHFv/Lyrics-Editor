from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class TrackMetadata:
    path: Path
    title: str | None = None
    artists: tuple[str, ...] = ()
    album: str | None = None
    duration: float | None = None
    embedded_lyrics: "Lyrics" | None = None
    cover_data: bytes | None = None
    cover_mime: str | None = None

    @property
    def artist_text(self) -> str | None:
        return " / ".join(self.artists) if self.artists else None

    @property
    def display_title(self) -> str:
        return self.title or self.path.stem


@dataclass(frozen=True)
class LyricLine:
    start: float
    text: str
    end: float | None = None
    translation: str | None = None


@dataclass(frozen=True)
class WordTiming:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Lyrics:
    source: str
    title: str
    artist: str
    album: str | None = None
    duration: float | None = None
    synced_text: str | None = None
    plain_text: str | None = None
    lines: tuple[LyricLine, ...] = ()
    words: tuple[WordTiming, ...] = ()
    provider_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class LyricCandidate:
    lyrics: Lyrics
    score: float
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    words: tuple[WordTiming, ...] = ()
