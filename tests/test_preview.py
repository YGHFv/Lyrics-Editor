from lyrics_editor.lrc import lyrics_preview
from lyrics_editor.models import Lyrics


def test_lyrics_preview_uses_plain_text_when_unsynced():
    lyrics = Lyrics(
        source="test",
        title="Song",
        artist="Artist",
        plain_text="first line\nsecond line\nthird line\nfourth line",
    )

    assert lyrics_preview(lyrics, max_lines=2) == "first line | second line"


def test_lyrics_preview_truncates_long_output():
    lyrics = Lyrics(
        source="test",
        title="Song",
        artist="Artist",
        plain_text="x" * 200,
    )

    assert lyrics_preview(lyrics, max_chars=40).endswith("…")

