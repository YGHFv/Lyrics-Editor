from lyrics_editor.align.timeline import align_lyrics_to_transcript
from lyrics_editor.models import LyricLine, Lyrics, TranscriptSegment, WordTiming


def test_align_lyrics_to_transcript_repairs_line_times():
    lyrics = Lyrics(
        source="test",
        title="Song",
        artist="Artist",
        lines=(
            LyricLine(start=1.0, text="hello world"),
            LyricLine(start=5.0, text="good night"),
        ),
    )
    transcript = (
        TranscriptSegment(start=1.5, end=2.0, text="hello world"),
        TranscriptSegment(
            start=4.5,
            end=5.5,
            text="good night",
            words=(WordTiming(start=4.5, end=5.0, text="good"),),
        ),
    )

    repaired = align_lyrics_to_transcript(lyrics, transcript)

    assert [line.start for line in repaired.lines] == [1.5, 4.5]
    assert repaired.lines[0].end == 4.5
    assert repaired.words[0].text == "good"

