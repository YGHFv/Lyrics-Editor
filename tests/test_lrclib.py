from lyrics_editor.models import TrackMetadata
from lyrics_editor.providers.lrclib import LrclibProvider


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_lrclib_provider_retries_with_multiple_queries(monkeypatch):
    calls: list[dict[str, str]] = []
    responses = [
        _FakeResponse([]),
        _FakeResponse(
            [
                {
                    "id": 1,
                    "trackName": "Song",
                    "artistName": "Artist",
                    "albumName": "Album",
                    "duration": 180,
                    "plainLyrics": "line",
                    "syncedLyrics": None,
                }
            ]
        ),
    ]

    def fake_get(url, params=None, timeout=None):
        del url, timeout
        calls.append(dict(params))
        return responses[len(calls) - 1]

    monkeypatch.setattr("lyrics_editor.providers.lrclib.requests.get", fake_get)

    provider = LrclibProvider()
    results = provider.search(
        TrackMetadata(
            path=__file__,
            title="Song",
            artists=("Artist",),
            album="Album",
            duration=180.0,
        )
    )

    assert len(results) == 1
    assert calls[0]["query"] == "Artist Song"
    assert calls[1]["track_name"] == "Song"

