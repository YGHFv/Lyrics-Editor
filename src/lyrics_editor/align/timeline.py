from __future__ import annotations

from rapidfuzz import fuzz

from lyrics_editor.align.text import normalize_text
from lyrics_editor.models import LyricLine, Lyrics, TranscriptSegment, WordTiming


def align_lyrics_to_transcript(
    lyrics: Lyrics,
    transcript: tuple[TranscriptSegment, ...],
    *,
    min_score: float = 55.0,
) -> Lyrics:
    """Repair line timestamps by matching lyric lines to ASR transcript segments."""
    if not lyrics.lines or not transcript:
        return lyrics

    repaired: list[LyricLine] = []
    collected_words: list[WordTiming] = []
    search_from = 0

    for line in lyrics.lines:
        match_index, score = _best_segment_index(line.text, transcript, search_from)
        if match_index is None or score < min_score:
            repaired.append(line)
            continue

        segment = transcript[match_index]
        repaired.append(LyricLine(start=segment.start, end=segment.end, text=line.text))
        collected_words.extend(segment.words)
        search_from = match_index + 1

    repaired = _fill_line_ends(repaired)
    return Lyrics(
        source=lyrics.source,
        title=lyrics.title,
        artist=lyrics.artist,
        album=lyrics.album,
        duration=lyrics.duration,
        synced_text=None,
        plain_text=lyrics.plain_text,
        lines=tuple(repaired),
        words=tuple(collected_words),
        provider_id=lyrics.provider_id,
        metadata={**lyrics.metadata, "timeline_repaired_by": "asr"},
    )


def _best_segment_index(
    lyric_text: str,
    transcript: tuple[TranscriptSegment, ...],
    search_from: int,
) -> tuple[int | None, float]:
    normalized_line = normalize_text(lyric_text)
    if not normalized_line:
        return None, 0.0

    best_index: int | None = None
    best_score = 0.0
    for index in range(search_from, len(transcript)):
        segment_text = normalize_text(transcript[index].text)
        if not segment_text:
            continue
        score = max(
            fuzz.ratio(normalized_line, segment_text),
            fuzz.partial_ratio(normalized_line, segment_text),
        )
        if score > best_score:
            best_index = index
            best_score = float(score)
    return best_index, best_score


def _fill_line_ends(lines: list[LyricLine]) -> tuple[LyricLine, ...]:
    output: list[LyricLine] = []
    for index, line in enumerate(lines):
        next_start = lines[index + 1].start if index + 1 < len(lines) else line.end
        output.append(LyricLine(start=line.start, end=next_start, text=line.text))
    return tuple(output)

