from __future__ import annotations

from dataclasses import replace

import requests

from lyrics_editor.lrc import lyrics_from_lrc
from lyrics_editor.models import Lyrics, TrackMetadata


class LrclibProvider:
    name = "LRCLIB"
    base_url = "https://lrclib.net/api"

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout

    def search(self, track: TrackMetadata, limit: int = 10) -> list[Lyrics]:
        results: list[Lyrics] = []
        for params in self._search_params(track):
            response = requests.get(f"{self.base_url}/search", params=params, timeout=self.timeout)
            response.raise_for_status()
            results = self._parse_results(response.json(), track, limit)
            if results:
                break
        return results

    def _search_params(self, track: TrackMetadata) -> list[dict[str, str]]:
        params: list[dict[str, str]] = []

        if track.artist_text and track.display_title:
            base = {
                "query": f"{track.artist_text} {track.display_title}".strip(),
                "track_name": track.display_title,
                "artist_name": track.artist_text,
            }
            if track.album:
                base["album_name"] = track.album
            if track.duration:
                base["duration"] = str(round(track.duration))
            params.append(base)

        if track.display_title:
            title_only = {"track_name": track.display_title}
            if track.album:
                title_only["album_name"] = track.album
            if track.duration:
                title_only["duration"] = str(round(track.duration))
            params.append(title_only)

        if track.artist_text and track.display_title:
            params.append({"query": f"{track.display_title} {track.artist_text}".strip()})

        return params or [{"query": track.display_title}]

    def _parse_results(
        self, payload: object, track: TrackMetadata, limit: int
    ) -> list[Lyrics]:
        if not isinstance(payload, list):
            return []

        results: list[Lyrics] = []
        for item in payload[:limit]:
            if not isinstance(item, dict):
                continue
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
            if plain:
                lyrics = replace(lyrics, synced_text=lyrics.synced_text, plain_text=plain)
            results.append(lyrics)
        return results
