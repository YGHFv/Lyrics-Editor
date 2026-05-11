from lyrics_editor.models import Lyrics, TrackMetadata
from lyrics_editor.providers.catalog import search_candidates
from lyrics_editor.providers.local import SidecarLyricsProvider


def test_sidecar_provider_reads_lrc_and_text(tmp_path):
    audio = tmp_path / "song.mp3"
    audio.write_bytes(b"")
    lrc = tmp_path / "song.lrc"
    lrc.write_text("[00:01.00]hello\n", encoding="utf-8")
    txt = tmp_path / "song.txt"
    txt.write_text("plain lyric", encoding="utf-8")

    provider = SidecarLyricsProvider()
    results = provider.search(TrackMetadata(path=audio, title="Song", artists=("Artist",)))

    assert len(results) == 2
    assert results[0].lines
    assert results[1].plain_text == "plain lyric"


def test_search_candidates_deduplicates_results(monkeypatch, tmp_path):
    track = TrackMetadata(path=tmp_path / "song.mp3", title="Song", artists=("Artist",))

    class StubProvider:
        def __init__(self, name: str, lyrics: list[Lyrics]) -> None:
            self.name = name
            self._lyrics = lyrics

        def search(self, _track: TrackMetadata, limit: int = 10) -> list[Lyrics]:
            return self._lyrics[:limit]

    shared = Lyrics(source="StubA", title="Song", artist="Artist", plain_text="same text")
    unique = Lyrics(source="StubB", title="Song", artist="Artist", plain_text="other text")

    def fake_build_provider(name: str):
        if name == "first":
            return StubProvider("first", [shared, unique])
        if name == "second":
            return StubProvider("second", [shared])
        raise AssertionError(name)

    monkeypatch.setattr("lyrics_editor.providers.catalog.build_provider", fake_build_provider)

    ranked = search_candidates(track, provider_names=["first", "second"])

    assert len(ranked) == 2
    assert ranked[0].lyrics.plain_text in {"same text", "other text"}
