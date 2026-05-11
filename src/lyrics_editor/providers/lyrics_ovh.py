from __future__ import annotations

from urllib.parse import quote

import requests

from lyrics_editor.models import Lyrics, TrackMetadata


class LyricsOvhProvider:
    name = "Lyrics.ovh"
    base_url = "https://api.lyrics.ovh/v1"

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout

    def search(self, track: TrackMetadata, limit: int = 10) -> list[Lyrics]:
        del limit
        if not track.artist_text or not track.display_title:
            return []

        artist = quote(track.artist_text, safe="")
        title = quote(track.display_title, safe="")
        response = requests.get(f"{self.base_url}/{artist}/{title}", timeout=self.timeout)
        if response.status_code == 404:
            return []
        response.raise_for_status()

        payload = response.json()
        text = (payload.get("lyrics") or "").strip()
        if not text:
            return []

        return [
            Lyrics(
                source=self.name,
                title=track.display_title,
                artist=track.artist_text or "",
                album=track.album,
                duration=track.duration,
                plain_text=text,
                provider_id=f"{track.artist_text} - {track.display_title}",
            )
        ]

