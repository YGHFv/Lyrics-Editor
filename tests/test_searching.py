from lyrics_editor.searching import build_search_track
from lyrics_editor.models import TrackMetadata


def test_build_search_track_uses_manual_overrides(tmp_path):
    audio = tmp_path / "song.mp3"
    audio.write_bytes(b"")
    track = TrackMetadata(
        path=audio,
        title="Auto Title",
        artists=("Auto Artist",),
        album="Auto Album",
        duration=180.0,
    )

    search_track = build_search_track(
        track,
        title="Manual Title",
        artist="Artist One / Artist Two",
        album="Manual Album",
    )

    assert search_track.title == "Manual Title"
    assert search_track.artists == ("Artist One", "Artist Two")
    assert search_track.album == "Manual Album"
    assert search_track.duration == 180.0
