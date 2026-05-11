from __future__ import annotations

from rapidfuzz import fuzz

from lyrics_editor.align.text import normalize_text
from lyrics_editor.models import LyricCandidate, Lyrics, TrackMetadata


def rank_candidates(track: TrackMetadata, lyrics: list[Lyrics]) -> list[LyricCandidate]:
    candidates = [_score_candidate(track, item) for item in lyrics]
    return sorted(candidates, key=lambda item: item.score, reverse=True)


def _score_candidate(track: TrackMetadata, lyrics: Lyrics) -> LyricCandidate:
    reasons: list[str] = []
    score = 0.0

    title_score = fuzz.token_sort_ratio(
        normalize_text(track.display_title), normalize_text(lyrics.title)
    )
    score += title_score * 0.45
    reasons.append(f"title={title_score:.0f}")

    if track.artist_text and lyrics.artist:
        artist_score = fuzz.token_sort_ratio(
            normalize_text(track.artist_text), normalize_text(lyrics.artist)
        )
        score += artist_score * 0.35
        reasons.append(f"artist={artist_score:.0f}")
    else:
        score += 20
        reasons.append("artist=unknown")

    if track.duration and lyrics.duration:
        delta = abs(track.duration - lyrics.duration)
        duration_score = max(0.0, 100.0 - delta * 8.0)
        score += duration_score * 0.20
        reasons.append(f"duration_delta={delta:.1f}s")
    else:
        score += 10
        reasons.append("duration=unknown")

    if lyrics.lines:
        score += 5
        reasons.append("synced")

    return LyricCandidate(lyrics=lyrics, score=round(score, 2), reasons=tuple(reasons))

