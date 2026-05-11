from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from lyrics_editor.audio import iter_audio_files, read_metadata
from lyrics_editor.lrc import lyrics_preview, to_lrc
from lyrics_editor.models import LyricCandidate, TrackMetadata
from lyrics_editor.providers.catalog import available_provider_names, search_candidates


class LyricsEditorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Lyrics Editor")
        self.geometry("1280x760")
        self.minsize(1100, 680)

        self.folder_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Choose a folder to scan local music files.")
        self.auto_search_var = tk.BooleanVar(value=True)
        self.limit_var = tk.IntVar(value=10)
        self.preview_lines_var = tk.IntVar(value=3)
        self.output_var = tk.StringVar()

        self.provider_vars = {
            name: tk.BooleanVar(value=True) for name in available_provider_names()
        }

        self._audio_items: list[TrackMetadata] = []
        self._candidate_items: list[LyricCandidate] = []
        self._selected_track: TrackMetadata | None = None
        self._selected_track_path: Path | None = None
        self._search_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._search_token = 0
        self._search_running = False

        self._build_ui()
        self.after(100, self._poll_queue)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        controls = ttk.Frame(self, padding=10)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        ttk.Button(controls, text="Open Folder", command=self._pick_folder).grid(
            row=0, column=0, padx=(0, 8)
        )
        folder_entry = ttk.Entry(controls, textvariable=self.folder_var)
        folder_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(controls, text="Load", command=self._load_folder).grid(row=0, column=2)

        options = ttk.Frame(self, padding=(10, 0, 10, 6))
        options.grid(row=1, column=0, sticky="ew")
        options.columnconfigure(0, weight=1)

        provider_box = ttk.LabelFrame(options, text="Providers", padding=8)
        provider_box.grid(row=0, column=0, sticky="ew")
        for index, name in enumerate(available_provider_names()):
            ttk.Checkbutton(
                provider_box,
                text=name,
                variable=self.provider_vars[name],
            ).grid(row=0, column=index, padx=(0, 12), sticky="w")

        ttk.Checkbutton(
            options,
            text="Auto search on track select",
            variable=self.auto_search_var,
        ).grid(row=0, column=1, sticky="e")

        search_opts = ttk.Frame(options)
        search_opts.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Label(search_opts, text="Limit").grid(row=0, column=0, padx=(0, 6))
        ttk.Spinbox(search_opts, from_=1, to=50, textvariable=self.limit_var, width=5).grid(
            row=0, column=1, padx=(0, 16)
        )
        ttk.Label(search_opts, text="Preview lines").grid(row=0, column=2, padx=(0, 6))
        ttk.Spinbox(
            search_opts, from_=1, to=10, textvariable=self.preview_lines_var, width=5
        ).grid(row=0, column=3)

        main = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        main.grid(row=2, column=0, sticky="nsew")

        left = ttk.Frame(main, padding=(10, 0, 6, 10))
        right = ttk.Frame(main, padding=(6, 0, 10, 10))
        main.add(left, weight=3)
        main.add(right, weight=4)

        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        ttk.Label(left, text="Tracks").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.track_tree = ttk.Treeview(
            left,
            columns=("title", "artist", "duration"),
            show="headings",
            selectmode="browse",
        )
        self.track_tree.heading("title", text="Title")
        self.track_tree.heading("artist", text="Artist")
        self.track_tree.heading("duration", text="Duration")
        self.track_tree.column("title", width=220, anchor="w")
        self.track_tree.column("artist", width=180, anchor="w")
        self.track_tree.column("duration", width=90, anchor="center")
        track_scroll = ttk.Scrollbar(left, orient="vertical", command=self.track_tree.yview)
        self.track_tree.configure(yscrollcommand=track_scroll.set)
        self.track_tree.grid(row=1, column=0, sticky="nsew")
        track_scroll.grid(row=1, column=1, sticky="ns")
        self.track_tree.bind("<<TreeviewSelect>>", self._on_track_select)

        track_actions = ttk.Frame(left)
        track_actions.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(track_actions, text="Search", command=self._start_search).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(track_actions, text="Save Best", command=self._save_best).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(track_actions, text="Save Selected", command=self._save_selected).pack(
            side="left"
        )

        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        meta = ttk.LabelFrame(right, text="Selection", padding=8)
        meta.grid(row=0, column=0, sticky="ew")
        meta.columnconfigure(1, weight=1)
        self.meta_title = tk.StringVar(value="-")
        self.meta_artist = tk.StringVar(value="-")
        self.meta_album = tk.StringVar(value="-")
        self.meta_duration = tk.StringVar(value="-")
        self.meta_source = tk.StringVar(value="-")
        self.meta_score = tk.StringVar(value="-")
        fields = [
            ("Title", self.meta_title),
            ("Artist", self.meta_artist),
            ("Album", self.meta_album),
            ("Duration", self.meta_duration),
            ("Source", self.meta_source),
            ("Score", self.meta_score),
        ]
        for row, (label, var) in enumerate(fields):
            ttk.Label(meta, text=label).grid(row=row, column=0, sticky="w", pady=1)
            ttk.Label(meta, textvariable=var).grid(row=row, column=1, sticky="w", pady=1)

        candidates_box = ttk.LabelFrame(right, text="Candidates", padding=8)
        candidates_box.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        candidates_box.columnconfigure(0, weight=1)
        self.candidate_tree = ttk.Treeview(
            candidates_box,
            columns=("score", "source", "title", "artist", "synced"),
            show="headings",
            selectmode="browse",
            height=7,
        )
        for column, title, width in [
            ("score", "Score", 90),
            ("source", "Source", 120),
            ("title", "Title", 220),
            ("artist", "Artist", 180),
            ("synced", "Synced", 80),
        ]:
            self.candidate_tree.heading(column, text=title)
            self.candidate_tree.column(column, width=width, anchor="w")
        candidate_scroll = ttk.Scrollbar(
            candidates_box, orient="vertical", command=self.candidate_tree.yview
        )
        self.candidate_tree.configure(yscrollcommand=candidate_scroll.set)
        self.candidate_tree.grid(row=0, column=0, sticky="ew")
        candidate_scroll.grid(row=0, column=1, sticky="ns")
        self.candidate_tree.bind("<<TreeviewSelect>>", self._on_candidate_select)

        preview_frame = ttk.LabelFrame(right, text="Preview", padding=8)
        preview_frame.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        self.preview = tk.Text(preview_frame, wrap="word", height=16, relief="flat")
        preview_scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview.yview)
        self.preview.configure(yscrollcommand=preview_scroll.set)
        self.preview.grid(row=0, column=0, sticky="nsew")
        preview_scroll.grid(row=0, column=1, sticky="ns")

        output_box = ttk.Frame(right)
        output_box.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        output_box.columnconfigure(1, weight=1)
        ttk.Label(output_box, text="Output").grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(output_box, textvariable=self.output_var).grid(
            row=0, column=1, sticky="ew", padx=(0, 8)
        )
        ttk.Button(output_box, text="Use Sidecar", command=self._set_sidecar_output).grid(
            row=0, column=2, padx=(0, 8)
        )
        ttk.Button(output_box, text="Browse", command=self._pick_output).grid(row=0, column=3)

        status = ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(10, 4))
        status.grid(row=3, column=0, sticky="ew")

    def _pick_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choose a music folder")
        if folder:
            self.folder_var.set(folder)
            self._load_folder()

    def _load_folder(self) -> None:
        folder = Path(self.folder_var.get().strip())
        if not folder.exists():
            messagebox.showerror("Lyrics Editor", "Choose a valid folder.")
            return

        self._audio_items = [read_metadata(path) for path in iter_audio_files(folder)]
        self.track_tree.delete(*self.track_tree.get_children())
        for metadata in self._audio_items:
            self.track_tree.insert(
                "",
                "end",
                iid=str(metadata.path),
                values=(
                    metadata.display_title,
                    metadata.artist_text or "",
                    f"{metadata.duration:.2f}s" if metadata.duration else "",
                ),
            )
        self.status_var.set(f"Loaded {len(self._audio_items)} audio files from {folder}")
        if self._audio_items:
            first = self._audio_items[0]
            self.track_tree.selection_set(str(first.path))
            self.track_tree.focus(str(first.path))
            self.track_tree.see(str(first.path))
            self._select_track(first)

    def _on_track_select(self, _event: object) -> None:
        selection = self.track_tree.selection()
        if not selection:
            return
        selected_path = Path(selection[0])
        for metadata in self._audio_items:
            if metadata.path == selected_path:
                self._select_track(metadata)
                break

    def _select_track(self, track: TrackMetadata) -> None:
        self._selected_track = track
        self._selected_track_path = track.path
        self.meta_title.set(track.display_title)
        self.meta_artist.set(track.artist_text or "")
        self.meta_album.set(track.album or "")
        self.meta_duration.set(f"{track.duration:.2f}s" if track.duration else "")
        self.output_var.set(str(track.path.with_suffix(".lrc")))
        self.status_var.set(f"Selected {track.path.name}")
        if self.auto_search_var.get():
            self._start_search()

    def _start_search(self) -> None:
        if self._search_running:
            return
        track = self._selected_track
        if track is None:
            messagebox.showinfo("Lyrics Editor", "Select a track first.")
            return

        provider_names = [name for name, flag in self.provider_vars.items() if flag.get()]
        if not provider_names:
            messagebox.showinfo("Lyrics Editor", "Select at least one provider.")
            return

        self._search_running = True
        self._search_token += 1
        token = self._search_token
        self.status_var.set(f"Searching {track.display_title}...")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", "Searching lyrics...")

        thread = threading.Thread(
            target=self._search_worker,
            args=(token, track, provider_names, self.limit_var.get(), self.preview_lines_var.get()),
            daemon=True,
        )
        thread.start()

    def _search_worker(
        self,
        token: int,
        track: TrackMetadata,
        provider_names: list[str],
        limit: int,
        preview_lines: int,
    ) -> None:
        try:
            candidates = search_candidates(
                track,
                limit=limit,
                provider_names=provider_names,
            )
            self._search_queue.put(("result", token, candidates, preview_lines))
        except Exception as exc:  # pragma: no cover - background thread
            self._search_queue.put(("error", token, exc))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, token, *payload = self._search_queue.get_nowait()
                if token != self._search_token:
                    continue
                if kind == "result":
                    candidates = payload[0]
                    preview_lines = payload[1]
                    self._apply_candidates(candidates, preview_lines)
                elif kind == "error":
                    exc = payload[0]
                    self.status_var.set(f"Search failed: {exc}")
                    self.preview.delete("1.0", "end")
                    self.preview.insert("1.0", f"Search failed:\n{exc}")
                self._search_running = False
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _apply_candidates(
        self, candidates: list[LyricCandidate], preview_lines: int
    ) -> None:
        self._candidate_items = candidates
        self.candidate_tree.delete(*self.candidate_tree.get_children())
        for index, candidate in enumerate(candidates):
            self.candidate_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    f"{candidate.score:.2f}",
                    candidate.lyrics.source,
                    candidate.lyrics.title,
                    candidate.lyrics.artist,
                    "yes" if candidate.lyrics.lines else "no",
                ),
            )
        self.meta_source.set(candidates[0].lyrics.source if candidates else "-")
        self.meta_score.set(f"{candidates[0].score:.2f}" if candidates else "-")
        self.status_var.set(
            f"Found {len(candidates)} candidate(s) using {len([1 for flag in self.provider_vars.values() if flag.get()])} provider(s)"
        )
        if candidates:
            self.candidate_tree.selection_set("0")
            self.candidate_tree.focus("0")
            self._show_candidate(candidates[0], preview_lines)
        else:
            self.preview.delete("1.0", "end")
            self.preview.insert("1.0", "No lyrics found.")

    def _on_candidate_select(self, _event: object) -> None:
        selection = self.candidate_tree.selection()
        if not selection:
            return
        index = int(selection[0])
        if 0 <= index < len(self._candidate_items):
            self._show_candidate(self._candidate_items[index], self.preview_lines_var.get())

    def _show_candidate(self, candidate: LyricCandidate, preview_lines: int) -> None:
        self.meta_source.set(candidate.lyrics.source)
        self.meta_score.set(f"{candidate.score:.2f}")
        self.preview.delete("1.0", "end")
        preview = lyrics_preview(candidate.lyrics, max_lines=preview_lines, max_chars=5000)
        self.preview.insert("1.0", preview or to_lrc(candidate.lyrics))

    def _selected_candidate(self) -> LyricCandidate | None:
        selection = self.candidate_tree.selection()
        if not selection:
            return self._candidate_items[0] if self._candidate_items else None
        index = int(selection[0])
        if 0 <= index < len(self._candidate_items):
            return self._candidate_items[index]
        return None

    def _save_best(self) -> None:
        if not self._candidate_items:
            messagebox.showinfo("Lyrics Editor", "Search lyrics first.")
            return
        self._save_candidate(self._candidate_items[0])

    def _save_selected(self) -> None:
        candidate = self._selected_candidate()
        if candidate is None:
            messagebox.showinfo("Lyrics Editor", "Search lyrics first.")
            return
        self._save_candidate(candidate)

    def _save_candidate(self, candidate: LyricCandidate) -> None:
        output = Path(self.output_var.get().strip())
        if not output:
            messagebox.showerror("Lyrics Editor", "Choose an output path.")
            return
        if not candidate.lyrics.lines and not candidate.lyrics.synced_text:
            messagebox.showinfo("Lyrics Editor", "Chosen candidate has no lyrics to save.")
            return
        output.write_text(to_lrc(candidate.lyrics), encoding="utf-8")
        self.status_var.set(f"Saved {output}")
        messagebox.showinfo("Lyrics Editor", f"Saved lyrics to {output}")

    def _pick_output(self) -> None:
        filename = filedialog.asksaveasfilename(
            title="Save lyrics as",
            defaultextension=".lrc",
            filetypes=[("LRC files", "*.lrc"), ("All files", "*.*")],
        )
        if filename:
            self.output_var.set(filename)

    def _set_sidecar_output(self) -> None:
        if self._selected_track_path is None:
            return
        self.output_var.set(str(self._selected_track_path.with_suffix(".lrc")))


def run_app() -> None:
    app = LyricsEditorApp()
    app.mainloop()
