from __future__ import annotations

from pathlib import Path
from typing import Protocol

from lyrics_editor.models import TranscriptSegment, WordTiming


class Transcriber(Protocol):
    def transcribe(self, path: Path) -> tuple[TranscriptSegment, ...]:
        """Return recognized text segments for an audio file."""


class FasterWhisperTranscriber:
    def __init__(self, model_size: str = "medium", device: str = "auto") -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is not installed. Install with: pip install -e .[asr]"
            ) from exc

        self.model = WhisperModel(model_size, device=device)

    def transcribe(self, path: Path) -> tuple[TranscriptSegment, ...]:
        segments, _info = self.model.transcribe(str(path), word_timestamps=True)
        output: list[TranscriptSegment] = []
        for segment in segments:
            words = tuple(
                WordTiming(start=word.start, end=word.end, text=word.word)
                for word in (segment.words or ())
            )
            output.append(
                TranscriptSegment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip(),
                    words=words,
                )
            )
        return tuple(output)

