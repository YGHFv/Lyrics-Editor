from __future__ import annotations

from collections.abc import Iterable

from lyrics_editor.matcher import rank_candidates
from lyrics_editor.models import LyricCandidate, Lyrics, TrackMetadata
from lyrics_editor.providers.local import SidecarLyricsProvider
from lyrics_editor.providers.lrclib import LrclibProvider
from lyrics_editor.providers.lyrics_ovh import LyricsOvhProvider

DEFAULT_PROVIDER_NAMES = ("sidecar", "lrclib", "lyrics_ovh")


def available_provider_names() -> tuple[str, ...]:
    return DEFAULT_PROVIDER_NAMES


def search_candidates(
    track: TrackMetadata,
    *,
    limit: int = 10,
    provider_names: Iterable[str] | None = None,
) -> list[LyricCandidate]:
    providers = [build_provider(name) for name in _normalize_provider_names(provider_names)]
    collected: list[Lyrics] = []
    errors: list[str] = []
    for provider in providers:
        try:
            collected.extend(provider.search(track, limit=limit))
        except Exception as exc:
            errors.append(f"{provider.name}: {exc}")
    if not collected and errors:
        raise RuntimeError("All lyrics providers failed: " + "; ".join(errors))
    return rank_candidates(track, _dedupe_lyrics(collected))


def build_provider(name: str):
    key = name.strip().lower()
    if key in {"sidecar", "local"}:
        return SidecarLyricsProvider()
    if key in {"lrclib", "lrc-lib"}:
        return LrclibProvider()
    if key in {"lyrics_ovh", "lyrics.ovh", "lyricsohv", "lyricsovh"}:
        return LyricsOvhProvider()
    raise ValueError(f"Unknown lyrics provider: {name}")


def _normalize_provider_names(provider_names: Iterable[str] | None) -> tuple[str, ...]:
    if provider_names is None:
        return DEFAULT_PROVIDER_NAMES
    names = tuple(name for name in provider_names if name.strip())
    return names or DEFAULT_PROVIDER_NAMES


def _dedupe_lyrics(items: list[Lyrics]) -> list[Lyrics]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[Lyrics] = []
    for item in items:
        text = item.synced_text or item.plain_text or "\n".join(line.text for line in item.lines)
        key = (item.title.lower(), item.artist.lower(), text[:200])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
