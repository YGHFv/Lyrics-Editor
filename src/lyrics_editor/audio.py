from __future__ import annotations

import base64
from collections.abc import Iterable
from io import BytesIO
from pathlib import Path

from mutagen import File
from mutagen.asf import ASF
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, ID3NoHeaderError, USLT
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

from lyrics_editor.lrc import lyrics_from_lrc, parse_lrc, to_lrc
from lyrics_editor.models import Lyrics, TrackMetadata, WordTiming

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
    easy_audio = File(path, easy=True)
    audio = File(path)
    if easy_audio is None and audio is None:
        return TrackMetadata(path=path)

    tags = easy_audio.tags if easy_audio is not None else {}
    title = _first(tags.get("title"))
    artists = tuple(_split_artists(tags.get("artist") or tags.get("artists")))
    album = _first(tags.get("album"))
    duration = _read_duration(easy_audio or audio)
    embedded_lyrics = _read_embedded_lyrics(
        audio,
        path,
        title=title,
        artist=_first(artists) if artists else None,
        album=album,
        duration=duration,
    )
    cover_data, cover_mime = _read_cover_art(audio)

    return TrackMetadata(
        path=path,
        title=title,
        artists=artists,
        album=album,
        duration=duration,
        embedded_lyrics=embedded_lyrics,
        cover_data=cover_data,
        cover_mime=cover_mime,
    )


def write_embedded_lyrics(
    path: Path,
    lyrics: Lyrics,
    *,
    show_translation: bool = False,
) -> None:
    audio = File(path)
    if audio is None:
        raise ValueError(f"不支持的音频文件：{path}")

    text = to_lrc(lyrics, show_translation=show_translation).strip()
    if isinstance(audio, MP3):
        _write_mp3_lyrics(audio, text)
    elif isinstance(audio, MP4):
        _write_mp4_lyrics(audio, text)
    elif isinstance(audio, FLAC):
        _write_flac_lyrics(audio, text)
    elif isinstance(audio, (OggVorbis, OggOpus)):
        _write_ogg_lyrics(audio, text)
    elif isinstance(audio, ASF):
        _write_asf_lyrics(audio, text)
    else:
        raise ValueError(f"当前暂不支持直接写入该格式：{path.suffix}")


def _read_duration(audio: object | None) -> float | None:
    if audio is None:
        return None
    info = getattr(audio, "info", None)
    if info is None:
        return None
    length = getattr(info, "length", None)
    return float(length) if length is not None else None


def _read_embedded_lyrics(
    audio: object | None,
    path: Path,
    *,
    title: str | None,
    artist: str | None,
    album: str | None,
    duration: float | None,
) -> Lyrics | None:
    if audio is None:
        return None

    text = ""
    if isinstance(audio, MP3):
        lyrics = _read_id3_lyrics(
            audio.tags,
            title=title or path.stem,
            artist=artist or "",
            album=album,
            duration=duration,
            provider_id=str(path),
        )
        if lyrics is not None:
            return lyrics
    elif isinstance(audio, MP4):
        text = _read_mp4_lyrics(audio.tags)
    elif isinstance(audio, FLAC):
        text = _read_text_from_mapping(audio.tags, ("lyrics", "LYRICS", "unsyncedlyrics"))
    elif isinstance(audio, (OggVorbis, OggOpus)):
        text = _read_ogg_lyrics(audio.tags)
    elif isinstance(audio, ASF):
        text = _read_text_from_mapping(
            audio.tags,
            ("WM/Lyrics", "WM/UnsyncedLyrics", "Lyrics", "LYRICS", "unsyncedlyrics"),
        )
    else:
        tags = getattr(audio, "tags", None)
        text = _read_text_from_mapping(tags, ("lyrics", "LYRICS", "unsyncedlyrics"))

    text = text.strip()
    if not text:
        return None

    if parse_lrc(text):
        return lyrics_from_lrc(
            source="内嵌歌词",
            title=title or path.stem,
            artist=artist or "",
            text=text,
            album=album,
            duration=duration,
            provider_id=str(path),
        )

    return Lyrics(
        source="内嵌歌词",
        title=title or path.stem,
        artist=artist or "",
        album=album,
        duration=duration,
        plain_text=text,
        provider_id=str(path),
    )


def _read_cover_art(audio: object | None) -> tuple[bytes | None, str | None]:
    if audio is None:
        return None, None

    if isinstance(audio, MP3):
        return _read_id3_cover(audio.tags)
    if isinstance(audio, MP4):
        return _read_mp4_cover(audio.tags)
    if isinstance(audio, FLAC):
        return _read_flac_cover(audio)
    if isinstance(audio, (OggVorbis, OggOpus)):
        return _read_ogg_cover(audio.tags)
    if isinstance(audio, ASF):
        return _read_asf_cover(audio.tags)
    return None, None


def _read_id3_lyrics(
    tags: ID3 | None,
    *,
    title: str,
    artist: str,
    album: str | None,
    duration: float | None,
    provider_id: str,
) -> Lyrics | None:
    if tags is None:
        return None
    for frame in tags.getall("SYLT"):
        lyrics = _lyrics_from_sylt(
            frame,
            title=title,
            artist=artist,
            album=album,
            duration=duration,
            provider_id=provider_id,
        )
        if lyrics is not None:
            return lyrics
    for frame in tags.getall("USLT"):
        text = getattr(frame, "text", "")
        if text:
            return Lyrics(
                source="内嵌歌词",
                title=title,
                artist=artist,
                album=album,
                duration=duration,
                synced_text=str(text),
                plain_text=str(text),
                provider_id=provider_id,
            )
    return None


def _lyrics_from_sylt(
    frame: object,
    *,
    title: str,
    artist: str,
    album: str | None,
    duration: float | None,
    provider_id: str,
) -> Lyrics | None:
    pairs = getattr(frame, "text", None)
    if not pairs:
        return None

    words: list[WordTiming] = []
    for index, (timestamp, text) in enumerate(pairs):
        word = str(text).strip()
        if not word:
            continue
        start = _timestamp_to_seconds(timestamp)
        next_timestamp = pairs[index + 1][0] if index + 1 < len(pairs) else None
        end = _timestamp_to_seconds(next_timestamp) if next_timestamp is not None else None
        words.append(WordTiming(start=start, end=end, text=word))

    if not words:
        return None

    synced_text = "\n".join(f"{_seconds_to_lrc_tag(word.start)}{word.text}" for word in words)
    return Lyrics(
        source="内嵌歌词",
        title=title,
        artist=artist,
        album=album,
        duration=duration,
        synced_text=synced_text,
        words=tuple(words),
        provider_id=provider_id,
    )


def _read_mp4_lyrics(tags: object | None) -> str:
    if tags is None:
        return ""
    value = _mapping_get(tags, "©lyr")
    return "\n".join(_flatten_text(value))


def _read_ogg_lyrics(tags: object | None) -> str:
    if tags is None:
        return ""
    text = _read_text_from_mapping(tags, ("lyrics", "LYRICS", "unsyncedlyrics"))
    if text:
        return text

    for key in ("metadata_block_picture", "METADATA_BLOCK_PICTURE"):
        values = _flatten_text(_mapping_get(tags, key))
        for encoded in values:
            try:
                picture = Picture()
                picture.load(BytesIO(base64.b64decode(encoded)))
            except Exception:
                continue
            if picture.data:
                return _guess_text_from_bytes(picture.data)
    return ""


def _read_text_from_mapping(tags: object | None, keys: tuple[str, ...]) -> str:
    if tags is None:
        return ""
    for key in keys:
        value = _mapping_get(tags, key)
        text = "\n".join(_flatten_text(value)).strip()
        if text:
            return text
    return ""


def _read_id3_cover(tags: ID3 | None) -> tuple[bytes | None, str | None]:
    if tags is None:
        return None, None
    frames = sorted(tags.getall("APIC"), key=_apic_priority)
    for frame in frames:
        data = getattr(frame, "data", None)
        mime = getattr(frame, "mime", None)
        if data:
            return bytes(data), str(mime or "image/jpeg")
    return None, None


def _read_mp4_cover(tags: object | None) -> tuple[bytes | None, str | None]:
    if tags is None:
        return None, None
    covers = _mapping_get(tags, "covr") or []
    for cover in covers:
        data = bytes(cover)
        imageformat = getattr(cover, "imageformat", None)
        if imageformat == MP4Cover.FORMAT_PNG:
            return data, "image/png"
        return data, "image/jpeg"
    return None, None


def _read_flac_cover(audio: FLAC) -> tuple[bytes | None, str | None]:
    if not getattr(audio, "pictures", None):
        return None, None
    for picture in audio.pictures:
        if picture.data:
            return bytes(picture.data), picture.mime or "image/jpeg"
    return None, None


def _read_ogg_cover(tags: object | None) -> tuple[bytes | None, str | None]:
    if tags is None:
        return None, None
    values = _flatten_text(_mapping_get(tags, "metadata_block_picture"))
    for encoded in values:
        try:
            picture = Picture()
            picture.load(BytesIO(base64.b64decode(encoded)))
        except Exception:
            continue
        if picture.data:
            return bytes(picture.data), picture.mime or "image/jpeg"

    coverart = _mapping_get(tags, "coverart")
    covermime = _first_text(_mapping_get(tags, "coverartmime"))
    if coverart:
        try:
            return base64.b64decode(_first_text(coverart) or ""), covermime or "image/jpeg"
        except Exception:
            return None, None
    return None, None


def _read_asf_cover(tags: object | None) -> tuple[bytes | None, str | None]:
    if tags is None:
        return None, None
    picture = _mapping_get(tags, "WM/Picture")
    if not picture:
        return None, None
    for item in _flatten_values(picture):
        data = getattr(item, "value", None)
        if data and hasattr(data, "data"):
            mime = getattr(data, "mime", None) or "image/jpeg"
            payload = getattr(data, "data", None)
            if payload:
                return bytes(payload), mime
    return None, None


def _write_mp3_lyrics(audio: MP3, text: str) -> None:
    if audio.tags is None:
        try:
            audio.add_tags()
        except ID3NoHeaderError:
            audio.tags = ID3()
    tags = audio.tags or ID3()
    tags.delall("USLT")
    tags.add(USLT(encoding=3, lang="und", desc="", text=text))
    audio.tags = tags
    audio.save()


def _write_mp4_lyrics(audio: MP4, text: str) -> None:
    if audio.tags is None:
        audio.add_tags()
    audio.tags["©lyr"] = [text]
    audio.save()


def _write_flac_lyrics(audio: FLAC, text: str) -> None:
    if audio.tags is None:
        audio.add_tags()
    audio["LYRICS"] = [text]
    audio.save()


def _write_ogg_lyrics(audio: OggVorbis | OggOpus, text: str) -> None:
    if audio.tags is None:
        audio.add_tags()
    audio["LYRICS"] = [text]
    audio.save()


def _write_asf_lyrics(audio: ASF, text: str) -> None:
    if audio.tags is None:
        audio.add_tags()
    audio["WM/Lyrics"] = [text]
    audio.save()


def _guess_text_from_bytes(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "utf-16"):
        try:
            return data.decode(encoding).strip()
        except Exception:
            continue
    return ""


def _flatten_text(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, bytes):
        return (_guess_text_from_bytes(value),)
    if hasattr(value, "text") and isinstance(getattr(value, "text"), str):
        return (str(getattr(value, "text")).strip(),)
    if hasattr(value, "value") and isinstance(getattr(value, "value"), str):
        return (str(getattr(value, "value")).strip(),)
    if isinstance(value, Iterable):
        parts: list[str] = []
        for item in value:
            parts.extend(_flatten_text(item))
        return tuple(part for part in parts if part)
    return (str(value).strip(),)


def _flatten_values(value: object) -> tuple[object, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        return (value,)
    if isinstance(value, Iterable):
        return tuple(value)
    return (value,)


def _first_text(value: object) -> str:
    flattened = _flatten_text(value)
    return flattened[0] if flattened else ""


def _mapping_get(tags: object, key: str) -> object | None:
    if tags is None:
        return None
    getter = getattr(tags, "get", None)
    if callable(getter):
        try:
            return getter(key)
        except Exception:
            pass
    try:
        return tags[key]  # type: ignore[index]
    except Exception:
        return None


def _apic_priority(frame: APIC) -> tuple[int, str]:
    frame_type = getattr(frame, "type", 99)
    desc = getattr(frame, "desc", "") or ""
    return (0 if frame_type == 3 else 1, desc)


def _seconds_to_lrc_tag(seconds: float) -> str:
    minutes = int(seconds // 60)
    rest = seconds - minutes * 60
    whole_seconds = int(rest)
    hundredths = int(round((rest - whole_seconds) * 100))
    if hundredths == 100:
        whole_seconds += 1
        hundredths = 0
    return f"{minutes:02d}:{whole_seconds:02d}.{hundredths:02d}"


def _timestamp_to_seconds(timestamp: object | None) -> float:
    if timestamp is None:
        return 0.0
    return float(timestamp) / 1000.0


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
