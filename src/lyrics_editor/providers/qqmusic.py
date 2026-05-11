from __future__ import annotations

import base64
from dataclasses import replace
import json
import re

import requests

from lyrics_editor.lrc import lyrics_from_lrc, parse_lrc
from lyrics_editor.models import Lyrics, TrackMetadata


class QQMusicProvider:
    name = "QQ音乐"
    search_url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
    lyric_url = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"

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
                "Referer": "https://y.qq.com/",
                "Origin": "https://y.qq.com",
                "Accept": "application/json, text/plain, */*",
            }
        )

    def search(self, track: TrackMetadata, limit: int = 10) -> list[Lyrics]:
        if not track.display_title and not track.artist_text:
            return []

        songs = self._search_songs(track, limit)
        results: list[Lyrics] = []
        for song in songs[:limit]:
            songmid = song.get("songmid")
            if not songmid:
                continue
            payload = self._get_json(
                self.lyric_url,
                params={
                    "g_tk": 5381,
                    "loginUin": 0,
                    "hostUin": 0,
                    "format": "json",
                    "inCharset": "utf8",
                    "outCharset": "utf-8",
                    "notice": 0,
                    "platform": "yqq.json",
                    "needNewCode": 0,
                    "songmid": songmid,
                    "nobase64": 1,
                },
            )
            lyrics = self._parse_lyrics(song, payload)
            if lyrics is not None:
                results.append(lyrics)
        return results

    def _search_songs(self, track: TrackMetadata, limit: int) -> list[dict[str, object]]:
        query_parts = [part for part in (track.artist_text, track.display_title) if part]
        if not query_parts and track.display_title:
            query_parts = [track.display_title]
        if not query_parts:
            return []

        payload = self._get_json(
            self.search_url,
            params={
                "aggr": 1,
                "lossless": 1,
                "cr": 1,
                "p": 1,
                "n": max(10, limit * 2),
                "w": " ".join(query_parts),
                "format": "json",
            },
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        song = data.get("song") if isinstance(data, dict) else None
        song_list = song.get("list") if isinstance(song, dict) else None
        return song_list if isinstance(song_list, list) else []

    def _parse_lyrics(self, song: dict[str, object], payload: object) -> Lyrics | None:
        if not isinstance(payload, dict):
            return None
        lyric_text = _extract_lyric_text(payload.get("lyric"))
        if not lyric_text:
            return None

        title = _first_text(song.get("songname")) or _first_text(song.get("name")) or ""
        artist = _join_names(song.get("singer"))
        album = _first_text(song.get("albumname")) or None
        duration = _extract_duration(song.get("interval"))
        lyrics = lyrics_from_lrc(
            source=self.name,
            title=title,
            artist=artist,
            album=album,
            duration=duration,
            text=lyric_text,
            provider_id=str(song.get("songmid")) if song.get("songmid") is not None else None,
        )

        translated_text = _extract_lyric_text(payload.get("trans")) or _extract_lyric_text(
            payload.get("tlyric")
        )
        if translated_text:
            translated_lines = parse_lrc(translated_text)
            lyrics = replace(lyrics, lines=_merge_translation_lines(lyrics.lines, translated_lines))
        return lyrics

    def _get_json(self, url: str, *, params: dict[str, object]) -> object:
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        text = response.text.strip()
        if text.startswith("callback(") and text.endswith(")"):
            text = text[len("callback(") : -1]
        if text.startswith("jsonCallback(") and text.endswith(")"):
            text = text[len("jsonCallback(") : -1]
        try:
            return response.json()
        except Exception:
            return json.loads(text)


def _extract_lyric_text(value: object) -> str:
    if not value:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if not text.startswith("[") and _looks_base64(text):
        try:
            text = base64.b64decode(text).decode("utf-8", errors="ignore")
        except Exception:
            return ""
    return text.strip()


def _looks_base64(text: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9+/=\s]+", text))


def _merge_translation_lines(base_lines, translated_lines):
    translated_map = {round(line.start, 3): line.text for line in translated_lines}
    merged = []
    for line in base_lines:
        merged.append(
            line.__class__(
                start=line.start,
                end=line.end,
                text=line.text,
                translation=translated_map.get(round(line.start, 3)) or line.translation,
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


def _extract_duration(value: object) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if numeric < 1000 else numeric / 1000.0
