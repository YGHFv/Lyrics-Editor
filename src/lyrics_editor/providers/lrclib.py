from __future__ import annotations

import requests

from lyrics_editor.lrc import lyrics_from_lrc
from lyrics_editor.models import Lyrics, TrackMetadata


class LrclibProvider:
    name = "LRCLIB"
    base_url = "https://lrclib.net/api"

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout

    def search(self, track: TrackMetadata, limit: int = 10) -> list[Lyrics]:
        params = {
            "track_name": track.display_title,
        }
        if track.artist_text:
            params["artist_name"] = track.artist_text
        if track.album:
            params["album_name"] = track.album
        if track.duration:
            params["duration"] = str(round(track.duration))

        response = requests.get(f"{self.base_url}/search", params=params, timeout=self.timeout)
        response.raise_for_status()

        results = []
        for item in response.json()[:limit]:
            synced = item.get("syncedLyrics")
            plain = item.get("plainLyrics")
            if not synced and not plain:
                continue
            lyrics = lyrics_from_lrc(
                source=self.name,
                title=item.get("trackName") or track.display_title,
                artist=item.get("artistName") or track.artist_text or "",
                album=item.get("albumName"),
                duration=float(item["duration"]) if item.get("duration") is not None else None,
                text=synced or "",
                provider_id=str(item.get("id")) if item.get("id") is not None else None,
            )
            if plain and not synced:
                lyrics = Lyrics(
                    source=lyrics.source,
                    title=lyrics.title,
                    artist=lyrics.artist,
                    album=lyrics.album,
                    duration=lyrics.duration,
                    plain_text=plain,
                    provider_id=lyrics.provider_id,
                )
            results.append(lyrics)
        return results

