from lyrics_editor.lrc import lyrics_preview, parse_lrc, to_lrc
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


def test_parse_lrc_merges_translation_lines():
    lines = parse_lrc("[00:01.00]hello\n[00:01.00]你好")

    assert len(lines) == 1
    assert lines[0].text == "hello"
    assert lines[0].translation == "你好"


def test_lyrics_preview_can_toggle_translation():
    lyrics = Lyrics(
        source="test",
        title="Song",
        artist="Artist",
        lines=(LyricLine(start=1.0, text="hello", translation="你好"),),
    )

    assert lyrics_preview(lyrics, max_lines=None, show_translation=False) == "[00:01.00] hello"
    assert "你好" in lyrics_preview(lyrics, max_lines=None, show_translation=True)
