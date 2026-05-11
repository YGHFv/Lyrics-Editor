# Lyrics Editor Project Log

## Working Rule

Before making project changes, read this file first to understand the current outline, decisions, and change history.
After making project changes, append a new entry under `Change Log` describing what changed, why it changed, and how it was verified.

## Project Outline

Lyrics Editor is a local music lyrics toolkit. It scans local audio files, reads metadata, matches online lyrics, writes LRC files, and provides a path toward ASR-assisted timeline repair and word-level lyrics.

### Core Goals

- Match local music files with online lyrics.
- Save synchronized lyrics beside local audio files.
- Repair lyric timelines with recognized text from audio.
- Preserve word-level timings when an ASR engine provides them.
- Keep the core reusable for a future desktop UI.

### Current Architecture

- `src/lyrics_editor/audio.py`: audio file discovery and metadata reading.
- `src/lyrics_editor/lrc.py`: LRC parsing and serialization.
- `src/lyrics_editor/models.py`: shared data models.
- `src/lyrics_editor/matcher.py`: candidate lyric ranking.
- `src/lyrics_editor/providers/`: online and local lyrics provider interfaces and implementations.
- `src/lyrics_editor/align/`: text normalization, ASR adapters, and timeline alignment.
- `src/lyrics_editor/cli.py`: command-line interface.
- `src/lyrics_editor/ui.py`: Tkinter desktop interface.
- `tests/`: focused tests for parsing, text normalization, providers, and timeline repair.

### Near-Term Roadmap

- Add more lyrics providers, such as QQ Music, NetEase Cloud Music, and Kugou.
- Add manual candidate selection and preview.
- Export enhanced LRC, word-level LRC, SRT, and ASS.
- Improve ASR-to-lyrics alignment with dynamic programming over lyric lines and transcript segments.
- Build a desktop UI for drag-and-drop matching and timeline editing.

## Change Log

### 2026-05-11 - Initial project scaffold

Created the first usable Python project scaffold.

Changed:

- Added packaging configuration in `pyproject.toml`.
- Added CLI commands: `inspect`, `search`, `match`, `scan`, and `repair`.
- Added audio metadata reading with `mutagen`.
- Added LRCLIB online lyrics provider.
- Added LRC parsing and writing.
- Added lyrics candidate scoring with `rapidfuzz`.
- Added ASR abstraction and `faster-whisper` adapter.
- Added ASR-assisted timeline repair that maps lyric lines to transcript segments.
- Added tests for LRC parsing, text normalization, and timeline repair.
- Added `.gitignore`.
- Added README with setup, usage, and roadmap.

Verification:

- `python -m pytest -q` passed with 6 tests.
- `python -m ruff check .` passed.
- `lyrics-editor --help` and `lyrics-editor repair --help` worked after editable install.

### 2026-05-11 - Add project outline and change log

Created this root-level `PROJECT_LOG.md` file as the canonical place for project outline, decisions, roadmap, and change history.

Changed:

- Added the working rule that future modifications should read this file first and append a change entry afterward.
- Documented current architecture and near-term roadmap.
- Backfilled the initial scaffold change record.

Verification:

- File was added with Markdown structure only; no runtime behavior changed.

### 2026-05-11 - Prepare GitHub synchronization

Prepared the project for synchronization through GitHub CLI.

Changed:

- Installed GitHub CLI with `winget install --id GitHub.cli`.
- Verified Git is available locally.
- Checked GitHub CLI authentication status.
- Confirmed GitHub CLI is installed at `C:\Program Files\GitHub CLI\gh.exe`.
- Initialized the local Git repository.
- Renamed the default branch to `main`.
- Created the initial local commit.

Notes:

- GitHub CLI is not authenticated yet, so remote repository creation and push require `gh auth login` before `gh repo create`.

Verification:

- `git --version` returned `2.49.0.windows.1`.
- Git global user name and email are configured.
- `gh auth status` reported that no GitHub host is logged in.
- `git commit -m "Initial scaffold for lyrics editor"` created commit `a12bc7d`.

### 2026-05-11 - Add manual candidate selection and lyric preview

Improved the lyrics matching workflow so candidates can be previewed and chosen manually.

Changed:

- Added `lyrics_preview()` to render a short preview from synced or plain lyrics text.
- Added a `choose` CLI command to list candidates, preview them, and save a manually selected result.
- Extended `search` output with a preview column.
- Preserved plain text alongside synced lyrics in the LRCLIB provider so previews work for both cases.
- Added tests for preview formatting.

Verification:

- `python -m pytest -q` passed with 8 tests.
- `python -m ruff check .` passed.
- `lyrics-editor --help` showed the new `choose` command.

### 2026-05-11 - Expand lyrics sources and add desktop UI

Expanded the matching pipeline to use multiple sources and added a Tkinter desktop interface.

Changed:

- Added `SidecarLyricsProvider` for local `.lrc` and `.txt` sidecar lyrics files.
- Added `LyricsOvhProvider` for plain-text online lyrics from `api.lyrics.ovh`.
- Added `search_candidates()` orchestration so multiple providers can be queried together.
- Added candidate deduplication across providers.
- Added `lyrics-editor gui` and a `lyrics-editor-gui` entry point.
- Added a Tkinter interface for browsing local audio files, choosing active providers, previewing candidates, and saving results.
- Added tests for sidecar source loading and provider deduplication.

Verification:

- `python -m pytest -q` passed with 10 tests.
- `python -m ruff check .` passed.
- `lyrics-editor --help` showed the new `gui` command.
- `Get-Command lyrics-editor-gui` resolved to the installed executable.

### 2026-05-11 - Localize the app to Chinese

Unified the user-facing application language to Chinese.

Changed:

- Translated CLI help text, command descriptions, table headers, prompts, and status messages.
- Translated desktop UI window title, buttons, labels, dialogs, and progress messages.
- Kept internal code identifiers unchanged so the logic stays stable.

Verification:

- `python -m pytest -q` passed with 10 tests.
- `python -m ruff check .` passed.
- `lyrics-editor --help` displayed Chinese help text and command descriptions.
- `lyrics-editor gui --help` displayed a Chinese command description.

### 2026-05-11 - Improve lyrics search and desktop readability

Improved search success rates for imperfect tags and made the desktop UI easier to read on Windows.

Changed:

- Added manual search overrides for title, artist, and album in CLI search/match/choose commands.
- Added editable search fields to the desktop UI so users can correct metadata before searching.
- Expanded LRCLIB lookup with multiple query forms and fallback attempts.
- Enabled Windows DPI awareness and applied a cleaner Tk/ttk visual style.
- Added tests for manual search overrides and LRCLIB query fallback.
- Updated README to explain manual search overrides and the new search fields.

Verification:

- `python -m pytest -q` passed with 12 tests.
- `python -m ruff check .` passed.
- `lyrics-editor --help` still showed the Chinese command list.
