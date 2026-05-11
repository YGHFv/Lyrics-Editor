from __future__ import annotations

from pathlib import Path

from lyrics_editor.lrc import lyrics_from_lrc
from lyrics_editor.models import Lyrics, TrackMetadata


class SidecarLyricsProvider:
    name = "Sidecar"

    def __init__(self, extensions: tuple[str, ...] = (".lrc", ".txt")) -> None:
        self.extensions = extensions

    def search(self, track: TrackMetadata, limit: int = 10) -> list[Lyrics]:
        candidates: list[Lyrics] = []
        for path in self._candidate_paths(track.path):
            if not path.exists() or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore").strip()
            if not text:
                continue

            suffix = path.suffix.lower()
            if suffix == ".lrc":
                candidates.append(
                    lyrics_from_lrc(
                        source=self.name,
                        title=track.display_title,
                        artist=track.artist_text or "",
                        album=track.album,
                        duration=track.duration,
                        text=text,
                        provider_id=str(path),
                    )
                )
            else:
                candidates.append(
                    Lyrics(
                        source=self.name,
                        title=track.display_title,
                        artist=track.artist_text or "",
                        album=track.album,
                        duration=track.duration,
                        plain_text=text,
                        provider_id=str(path),
                    )
                )
        return candidates[:limit] if limit > 0 else candidates

    def _candidate_paths(self, audio_path: Path) -> tuple[Path, ...]:
        stem = audio_path.with_suffix("")
        paths = [stem.with_suffix(ext) for ext in self.extensions]
        paths.extend(
            [
                audio_path.with_name(f"{audio_path.stem}.lyrics.lrc"),
                audio_path.with_name(f"{audio_path.stem}.lyrics.txt"),
            ]
        )
        return tuple(dict.fromkeys(paths))
