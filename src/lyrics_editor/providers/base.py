from __future__ import annotations

from typing import Protocol

from lyrics_editor.models import Lyrics, TrackMetadata


class LyricsProvider(Protocol):
    name: str

    def search(self, track: TrackMetadata, limit: int = 10) -> list[Lyrics]:
        """Return possible lyrics for a local track."""

