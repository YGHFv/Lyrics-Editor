from lyrics_editor.lrc import parse_lrc, to_lrc
from lyrics_editor.models import LyricLine, Lyrics


def test_parse_lrc_multiple_time_tags():
    lines = parse_lrc("[00:01.00][00:02.50]hello\n[00:03.00]world")

    assert [line.start for line in lines] == [1.0, 2.5, 3.0]
    assert lines[0].text == "hello"
    assert lines[1].end == 3.0


def test_to_lrc_formats_hundredths():
    lyrics = Lyrics(
        source="test",
        title="Song",
        artist="Artist",
        lines=(LyricLine(start=65.345, text="line"),),
    )

    assert "[01:05.34]line" in to_lrc(lyrics)

