from __future__ import annotations

from lyrics_editor.models import Lyrics, TrackMetadata


class EmbeddedLyricsProvider:
    name = "内嵌歌词"

    def search(self, track: TrackMetadata, limit: int = 10) -> list[Lyrics]:
        del limit
        if track.embedded_lyrics is None:
            return []
        return [track.embedded_lyrics]
