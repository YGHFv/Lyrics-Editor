from __future__ import annotations

from dataclasses import replace

import requests

from lyrics_editor.lrc import lyrics_from_lrc, parse_lrc
from lyrics_editor.models import Lyrics, TrackMetadata


class NeteaseProvider:
    name = "网易云音乐"
    base_url = "https://music.163.com"

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Referer": "https://music.163.com/",
                "Accept": "application/json, text/plain, */*",
            }
        )

    def search(self, track: TrackMetadata, limit: int = 10) -> list[Lyrics]:
        if not track.display_title and not track.artist_text:
            return []

        results = self._search_songs(track, limit)
        lyrics_items: list[Lyrics] = []
        for item in results[:limit]:
            song = item.get("song", item)
            song_id = song.get("id")
            if song_id is None:
                continue
            lyric_payload = self._get_json(
                f"{self.base_url}/api/song/lyric",
                params={"id": song_id, "lv": 1, "kv": 1, "tv": -1},
            )
            lyrics = self._parse_lyrics(song, lyric_payload)
            if lyrics is not None:
                lyrics_items.append(lyrics)
        return lyrics_items

    def _search_songs(self, track: TrackMetadata, limit: int) -> list[dict[str, object]]:
        query_parts = [part for part in (track.artist_text, track.display_title) if part]
        if not query_parts and track.display_title:
            query_parts = [track.display_title]
        if not query_parts:
            return []

        payload = self._get_json(
            f"{self.base_url}/api/search/get/web",
            params={
                "type": 1,
                "s": " ".join(query_parts),
                "limit": max(10, limit * 2),
                "offset": 0,
            },
        )
        result = payload.get("result") if isinstance(payload, dict) else None
        songs = result.get("songs") if isinstance(result, dict) else None
        return songs if isinstance(songs, list) else []

    def _parse_lyrics(self, song: dict[str, object], payload: object) -> Lyrics | None:
        if not isinstance(payload, dict):
            return None
        lrc_text = _extract_lyric_text(payload.get("lrc"))
        if not lrc_text:
            return None

        title = _first_text(song.get("name")) or _first_text(song.get("songName")) or ""
        artist = _join_names(song.get("ar") or song.get("artists") or song.get("singer"))
        album = _extract_album_name(song.get("al") or song.get("album"))
        duration = _extract_duration(song.get("dt") or song.get("duration"))
        lyrics = lyrics_from_lrc(
            source=self.name,
            title=title,
            artist=artist,
            album=album,
            duration=duration,
            text=lrc_text,
            provider_id=str(song.get("id")) if song.get("id") is not None else None,
        )

        translated_text = _extract_lyric_text(payload.get("tlyric"))
        if translated_text:
            translated_lines = parse_lrc(translated_text)
            lyrics = replace(lyrics, lines=_merge_translation_lines(lyrics.lines, translated_lines))
        return lyrics

    def _get_json(self, url: str, *, params: dict[str, object]) -> object:
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()


def _extract_lyric_text(value: object) -> str:
    if isinstance(value, dict):
        text = value.get("lyric") or value.get("text")
        return str(text).strip() if text else ""
    return ""


def _merge_translation_lines(
    base_lines, translated_lines
):
    translated_map = {round(line.start, 3): line.text for line in translated_lines}
    merged = []
    for line in base_lines:
        translation = translated_map.get(round(line.start, 3))
        merged.append(
            type(line)(
                start=line.start,
                end=line.end,
                text=line.text,
                translation=translation or line.translation,
            )
        )
    return tuple(merged)


def _first_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("name", "title"):
            text = value.get(key)
            if text:
                return str(text).strip()
    return ""


def _join_names(value: object) -> str:
    if isinstance(value, list):
        names = []
        for item in value:
            name = _first_text(item)
            if name:
                names.append(name)
        return " / ".join(names)
    return _first_text(value)


def _extract_album_name(value: object) -> str | None:
    text = _first_text(value)
    return text or None


def _extract_duration(value: object) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric / 1000.0 if numeric > 1000 else numeric
