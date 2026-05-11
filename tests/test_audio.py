from __future__ import annotations

from types import SimpleNamespace

from mutagen.id3 import APIC, SYLT, USLT

import lyrics_editor.audio as audio_module
from lyrics_editor.lrc import lyrics_preview
from lyrics_editor.models import LyricLine, Lyrics


class _FakeEasyAudio:
    def __init__(self) -> None:
        self.tags = {
            "title": ["Song"],
            "artist": ["Artist"],
            "album": ["Album"],
        }
        self.info = SimpleNamespace(length=123.45)


class _FakeID3Tags:
    def __init__(self) -> None:
        self._frames = {
            "SYLT": [
                SYLT(
                    encoding=3,
                    lang="eng",
                    format=1,
                    type=1,
                    desc="",
                    text=[(1000, "hello"), (1200, "world")],
                )
            ],
            "USLT": [USLT(encoding=3, lang="eng", desc="", text="[00:01.00]hello\n[00:01.00]你好")],
            "APIC": [APIC(encoding=3, mime="image/jpeg", type=3, desc="cover", data=b"cover-bytes")],
        }

    def getall(self, key):
        return list(self._frames.get(key, []))

    def delall(self, key):
        self._frames.pop(key, None)

    def add(self, frame):
        self._frames.setdefault("USLT", []).append(frame)


class _FakeMP3(audio_module.MP3):
    def __init__(self) -> None:
        self.tags = _FakeID3Tags()
        self.saved = False
        self.info = SimpleNamespace(length=123.45)

    def add_tags(self):
        if self.tags is None:
            self.tags = _FakeID3Tags()

    def save(self):
        self.saved = True


def test_read_metadata_extracts_embedded_lyrics_and_cover(monkeypatch, tmp_path):
    audio_path = tmp_path / "song.mp3"
    audio_path.write_bytes(b"")
    easy_audio = _FakeEasyAudio()
    mp3_audio = _FakeMP3()

    def fake_file(path, easy=False):
        assert path == audio_path
        return easy_audio if easy else mp3_audio

    monkeypatch.setattr(audio_module, "File", fake_file)

    track = audio_module.read_metadata(audio_path)

    assert track.title == "Song"
    assert track.artist_text == "Artist"
    assert track.album == "Album"
    assert track.duration == 123.45
    assert track.cover_data == b"cover-bytes"
    assert track.cover_mime == "image/jpeg"
    assert track.embedded_lyrics is not None
    assert track.embedded_lyrics.words[0].text == "hello"
    assert track.embedded_lyrics.words[0].start == 1.0
    assert "[00:01.00] hello" in lyrics_preview(track.embedded_lyrics, max_lines=None)


def test_write_embedded_lyrics_updates_mp3_uslt(monkeypatch, tmp_path):
    audio_path = tmp_path / "song.mp3"
    audio_path.write_bytes(b"")
    mp3_audio = _FakeMP3()

    monkeypatch.setattr(audio_module, "File", lambda path: mp3_audio)

    lyrics = Lyrics(
        source="test",
        title="Song",
        artist="Artist",
        lines=(LyricLine(start=1.0, text="hello", translation="你好"),),
    )

    audio_module.write_embedded_lyrics(audio_path, lyrics, show_translation=True)

    assert mp3_audio.saved is True
    frames = mp3_audio.tags.getall("USLT")
    assert len(frames) == 1
    assert "[00:01.00]hello" in frames[0].text
    assert "[00:01.00]你好" in frames[0].text
