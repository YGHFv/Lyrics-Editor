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

### 2026-05-11 - Read embedded media assets and support embedded lyric saving

Expanded the editor so it can read embedded lyrics and cover art from local audio files, preview full lyrics with optional translation lines, and write lyrics back into supported audio formats.

Changed:

- Added embedded-lyrics detection to audio metadata loading.
- Added embedded cover-art extraction for the desktop UI.
- Added an embedded lyrics provider so tagged lyrics can participate in search and preview.
- Added preview translation toggles and save-time translation toggles in the desktop UI.
- Added direct embedded lyric writing for supported audio formats.
- Made the preview panel render the full lyric body instead of only a short snippet.
- Added tests for embedded metadata reading, translation merging, preview toggling, and MP3 lyric writing.
- Added `Pillow` as a dependency for cover-art rendering.

Verification:

- `python -m pytest -q` passed with 16 tests.
- `python -m ruff check .` passed.
- `python -c "import lyrics_editor.ui; print('ui import ok')"` succeeded.
- `python -m lyrics_editor.cli gui --help` succeeded.

### 2026-05-11 - Add GUI watch mode for live debugging

Added a lightweight development mode so the desktop app can restart automatically when source files change.

Changed:

- Added a `--watch` option to the `gui` command.
- Spawned the Tkinter app in a child process and monitored `src/` plus `pyproject.toml` for changes.
- Restarted the GUI automatically after file edits to speed up iterative debugging.

Verification:

- `python -m pytest -q` passed with 16 tests.
- `python -m ruff check .` passed.
- `python -m lyrics_editor.cli gui --help` showed the new `--watch` option.

### 2026-05-11 - Increase the default desktop window size

Raised the initial GUI window size so the layout fits more comfortably on first launch.

Changed:

- Increased the minimum window size.
- Switched the default size to a screen-aware larger geometry.
- Kept the layout responsive so the window can still be resized down when needed.

Verification:

- `python -m pytest -q` passed with 16 tests.
- `python -m ruff check src/lyrics_editor/ui.py` passed.
- `python -c "from lyrics_editor.ui import LyricsEditorApp; print('ui ok')"` succeeded.

### 2026-05-11 - Compact source selectors and show timestamps in preview

Tightened the source selector layout and changed lyric previews to render timestamped lines so embedded lyrics are easier to read.

Changed:

- Repacked the source checkboxes into a compact two-column layout.
- Shortened the visible source labels to reduce wrapping.
- Changed lyric preview rendering to include time tags on each line.
- Collapsed exact duplicate rendered preview lines to reduce repeated embedded lyric text.

Verification:

- `python -m pytest -q` passed with 16 tests.
- `python -m ruff check .` passed.
- `python -c "from lyrics_editor.lrc import lyrics_preview; print('ok')"` succeeded.

### 2026-05-11 - Fix source row layout and adapt embedded word-level lyrics

Fixed the root grid weights so the source selector row keeps its height, and taught embedded lyric loading and previewing to handle word-level `SYLT` lyrics correctly.

Changed:

- Moved the main content row to the weighted grid slot so the options area is no longer squeezed.
- Marked embedded `SYLT` frames as word-level lyrics instead of flattening them into repeated line text.
- Rendered word-level lyrics in previews with timestamps so each token keeps its timing.
- Allowed word-level lyrics to count as synced content for the preview and save paths.
- Added a regression test that reads a real `SYLT` frame and verifies timestamped preview output.

Verification:

- `python -m pytest -q` passed with 16 tests.
- `python -m ruff check .` passed.
- `python -c "from lyrics_editor.audio import read_metadata; print('audio ok')"` succeeded.

### 2026-05-11 - Add specific NetEase and QQ Music sources

Expanded the online search sources so the UI can show and query specific Chinese music platforms instead of only generic LRCLIB-style results.

Changed:

- Added a NetEase Cloud Music provider with best-effort search and lyric fetching.
- Added a QQ Music provider with best-effort search and lyric fetching.
- Put the source selector back into a single horizontal row.
- Updated provider labels so the source list shows `网易云` and `QQ音乐` explicitly.
- Added tests covering provider registration and source naming.

Verification:

- `python -m pytest -q` passed with 19 tests.
- `python -m ruff check .` passed.

### 2026-05-11 - Default the desktop app to maximized window mode

Changed the editor to open maximized by default so the full workspace is visible immediately on launch.

Changed:

- Switched the startup window state to maximized when the platform supports it.
- Kept the earlier geometry fallback for environments that do not support zoomed windows.

Verification:

- `python -m pytest -q` passed with 16 tests.
- `python -m ruff check src/lyrics_editor/ui.py` passed.
- `python -c "from lyrics_editor.ui import LyricsEditorApp; print('ui ok')"` succeeded.
