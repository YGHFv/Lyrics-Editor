from __future__ import annotations

from lyrics_editor.models import TrackMetadata


def build_search_track(
    track: TrackMetadata,
    *,
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
) -> TrackMetadata:
    return TrackMetadata(
        path=track.path,
        title=_clean_text(title) or track.title,
        artists=_parse_artists(artist) if artist is not None else track.artists,
        album=_clean_text(album) or track.album,
        duration=track.duration,
    )


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _parse_artists(value: str | None) -> tuple[str, ...]:
    text = _clean_text(value)
    if not text:
        return ()
    normalized = text.replace("；", ";").replace("、", ";").replace("/", ";")
    return tuple(part.strip() for part in normalized.split(";") if part.strip())

