from __future__ import annotations

from lyrics_editor.models import TrackMetadata
from lyrics_editor.providers.catalog import build_provider, available_provider_names


class _FakeResponse:
    def __init__(self, payload, text: str | None = None):
        self._payload = payload
        self.text = text if text is not None else ""

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_catalog_exposes_specific_sources():
    assert available_provider_names()[:4] == ("embedded", "sidecar", "netease", "qqmusic")
    assert build_provider("netease").name == "网易云音乐"
    assert build_provider("qqmusic").name == "QQ音乐"


def test_netease_provider_returns_named_source(monkeypatch):
    provider = build_provider("netease")
    track = TrackMetadata(path=__file__, title="Song", artists=("Artist",))

    responses = [
        _FakeResponse(
            {
                "result": {
                    "songs": [
                        {
                            "id": 1,
                            "name": "Song",
                            "ar": [{"name": "Artist"}],
                            "al": {"name": "Album"},
                            "dt": 180000,
                        }
                    ]
                }
            }
        ),
        _FakeResponse(
            {
                "lrc": {"lyric": "[00:01.00]hello"},
                "tlyric": {"lyric": "[00:01.00]你好"},
            }
        ),
    ]
    calls = []

    def fake_get(url, params=None, timeout=None):
        del timeout
        calls.append((url, dict(params or {})))
        return responses[len(calls) - 1]

    provider.session.get = fake_get

    results = provider.search(track, limit=1)

    assert results
    assert results[0].source == "网易云音乐"
    assert results[0].lines[0].translation == "你好"
    assert "api/search/get/web" in calls[0][0]


def test_qqmusic_provider_returns_named_source(monkeypatch):
    provider = build_provider("qqmusic")
    track = TrackMetadata(path=__file__, title="Song", artists=("Artist",))

    responses = [
        _FakeResponse(
            {
                "data": {
                    "song": {
                        "list": [
                            {
                                "songmid": "mid-1",
                                "songname": "Song",
                                "singer": [{"name": "Artist"}],
                                "albumname": "Album",
                                "interval": 180,
                            }
                        ]
                    }
                }
            }
        ),
        _FakeResponse({"lyric": "[00:01.00]hello"}),
    ]
    calls = []

    def fake_get(url, params=None, timeout=None):
        del timeout
        calls.append((url, dict(params or {})))
        return responses[len(calls) - 1]

    provider.session.get = fake_get

    results = provider.search(track, limit=1)

    assert results
    assert results[0].source == "QQ音乐"
    assert results[0].lines[0].text == "hello"
    assert "client_search_cp" in calls[0][0]
