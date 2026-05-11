from __future__ import annotations

import ctypes
import io
import queue
import platform
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover - optional dependency guard
    Image = ImageTk = None

from lyrics_editor.audio import iter_audio_files, read_metadata, write_embedded_lyrics
from lyrics_editor.lrc import lyrics_preview, to_lrc
from lyrics_editor.models import LyricCandidate, TrackMetadata
from lyrics_editor.providers.catalog import available_provider_names, search_candidates
from lyrics_editor.searching import build_search_track

PROVIDER_LABELS = {
    "embedded": "内嵌",
    "sidecar": "本地",
    "netease": "网易云",
    "qqmusic": "QQ音乐",
    "lrclib": "LRCLIB",
    "lyrics_ovh": "Lyrics.ovh",
}


class LyricsEditorApp(tk.Tk):
    def __init__(self) -> None:
        _enable_windows_hidpi()
        super().__init__()
        self.title("歌词编辑器")
        self.minsize(1280, 760)

        self.folder_var = tk.StringVar()
        self.status_var = tk.StringVar(value="请选择一个文件夹以扫描本地音乐文件。")
        self.search_title_var = tk.StringVar()
        self.search_artist_var = tk.StringVar()
        self.search_album_var = tk.StringVar()
        self.auto_search_var = tk.BooleanVar(value=True)
        self.show_translation_var = tk.BooleanVar(value=False)
        self.save_translation_var = tk.BooleanVar(value=False)
        self.save_to_audio_var = tk.BooleanVar(value=False)
        self.limit_var = tk.IntVar(value=10)
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
        self._cover_photo = None

        self._apply_look_and_feel()
        self._build_ui()
        self._set_initial_window_size()
        self.after(100, self._poll_queue)

    def _apply_look_and_feel(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "xpnative" in style.theme_names():
            style.theme_use("xpnative")
        else:
            style.theme_use("clam")

        base = tkfont.nametofont("TkDefaultFont")
        base.configure(family="Segoe UI", size=10)
        heading = tkfont.nametofont("TkHeadingFont")
        heading.configure(family="Segoe UI", size=10, weight="bold")
        self._mono_font = tkfont.nametofont("TkFixedFont")
        self._mono_font.configure(family="Consolas", size=10)
        self.option_add("*Font", base)
        self.option_add("*TCombobox*Listbox.Font", base)
        self.tk.call("tk", "scaling", self.winfo_fpixels("1i") / 72.0)

        self.configure(background="#f5f6f8")
        style.configure("TFrame", background="#f5f6f8")
        style.configure("TLabel", background="#f5f6f8")
        style.configure("TButton", padding=(10, 5))
        style.configure("TCheckbutton", background="#f5f6f8")
        style.configure("TLabelframe", background="#f5f6f8", padding=8)
        style.configure("TLabelframe.Label", background="#f5f6f8", font=heading)
        style.configure("Treeview", rowheight=28, font=base)
        style.configure("Treeview.Heading", font=heading)
        style.map("Treeview", background=[("selected", "#dce8ff")])

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        controls = ttk.Frame(self, padding=10)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        ttk.Button(controls, text="打开文件夹", command=self._pick_folder).grid(
            row=0, column=0, padx=(0, 8)
        )
        folder_entry = ttk.Entry(controls, textvariable=self.folder_var)
        folder_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(controls, text="加载", command=self._load_folder).grid(row=0, column=2)

        options = ttk.Frame(self, padding=(10, 0, 10, 6))
        options.grid(row=1, column=0, sticky="ew")
        options.columnconfigure(0, weight=1)

        provider_box = ttk.LabelFrame(options, text="歌词来源", padding=8)
        provider_box.grid(row=0, column=0, sticky="ew")
        provider_grid = ttk.Frame(provider_box)
        provider_grid.grid(row=0, column=0, sticky="w")
        for column in range(len(available_provider_names())):
            provider_grid.columnconfigure(column, weight=0)
        for index, name in enumerate(available_provider_names()):
            ttk.Checkbutton(
                provider_grid,
                text=PROVIDER_LABELS.get(name, name),
                variable=self.provider_vars[name],
            ).grid(row=0, column=index, padx=(0, 12), sticky="w")

        ttk.Checkbutton(
            options,
            text="选中歌曲时自动搜索",
            variable=self.auto_search_var,
        ).grid(row=0, column=1, sticky="e")

        search_opts = ttk.Frame(options)
        search_opts.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Label(search_opts, text="数量").grid(row=0, column=0, padx=(0, 6))
        ttk.Spinbox(search_opts, from_=1, to=50, textvariable=self.limit_var, width=5).grid(
            row=0, column=1, padx=(0, 16)
        )
        toggle_box = ttk.Frame(options)
        toggle_box.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Checkbutton(
            toggle_box,
            text="预览显示翻译",
            variable=self.show_translation_var,
            command=self._refresh_preview,
        ).grid(row=0, column=0, padx=(0, 16), sticky="w")
        ttk.Checkbutton(
            toggle_box,
            text="保存时包含翻译",
            variable=self.save_translation_var,
        ).grid(row=0, column=1, padx=(0, 16), sticky="w")
        ttk.Checkbutton(
            toggle_box,
            text="直接写入音频文件",
            variable=self.save_to_audio_var,
            command=self._update_output_default,
        ).grid(row=0, column=2, sticky="w")

        main = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        main.grid(row=2, column=0, sticky="nsew")

        left = ttk.Frame(main, padding=(10, 0, 6, 10))
        right = ttk.Frame(main, padding=(6, 0, 10, 10))
        main.add(left, weight=3)
        main.add(right, weight=4)

        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        ttk.Label(left, text="歌曲列表").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.track_tree = ttk.Treeview(
            left,
            columns=("title", "artist", "duration"),
            show="headings",
            selectmode="browse",
        )
        self.track_tree.heading("title", text="标题")
        self.track_tree.heading("artist", text="歌手")
        self.track_tree.heading("duration", text="时长")
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
        ttk.Button(track_actions, text="搜索", command=self._start_search).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(track_actions, text="保存最佳", command=self._save_best).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(track_actions, text="保存所选", command=self._save_selected).pack(
            side="left"
        )

        right.rowconfigure(3, weight=1)
        right.columnconfigure(0, weight=1)

        search_meta = ttk.LabelFrame(right, text="搜索信息", padding=8)
        search_meta.grid(row=0, column=0, sticky="ew")
        search_meta.columnconfigure(1, weight=1)
        search_fields = [
            ("标题", self.search_title_var),
            ("歌手", self.search_artist_var),
            ("专辑", self.search_album_var),
        ]
        for row, (label, var) in enumerate(search_fields):
            ttk.Label(search_meta, text=label).grid(row=row, column=0, sticky="w", pady=1)
            ttk.Entry(search_meta, textvariable=var).grid(row=row, column=1, sticky="ew", pady=1)
        ttk.Button(search_meta, text="重置", command=self._reset_search_fields).grid(
            row=0, column=2, rowspan=3, padx=(8, 0), sticky="ns"
        )

        meta = ttk.LabelFrame(right, text="当前选择", padding=8)
        meta.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        meta.columnconfigure(1, weight=1)
        meta.columnconfigure(2, weight=0)
        self.meta_title = tk.StringVar(value="-")
        self.meta_artist = tk.StringVar(value="-")
        self.meta_album = tk.StringVar(value="-")
        self.meta_duration = tk.StringVar(value="-")
        self.meta_source = tk.StringVar(value="-")
        self.meta_score = tk.StringVar(value="-")
        fields = [
            ("标题", self.meta_title),
            ("歌手", self.meta_artist),
            ("专辑", self.meta_album),
            ("时长", self.meta_duration),
            ("来源", self.meta_source),
            ("得分", self.meta_score),
        ]
        for row, (label, var) in enumerate(fields):
            ttk.Label(meta, text=label).grid(row=row, column=0, sticky="w", pady=1)
            ttk.Label(meta, textvariable=var).grid(row=row, column=1, sticky="w", pady=1)
        self.cover_label = ttk.Label(meta, text="无封面", anchor="center")
        self.cover_label.grid(row=0, column=2, rowspan=len(fields), sticky="nsew", padx=(12, 0))

        candidates_box = ttk.LabelFrame(right, text="候选歌词", padding=8)
        candidates_box.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        candidates_box.columnconfigure(0, weight=1)
        self.candidate_tree = ttk.Treeview(
            candidates_box,
            columns=("score", "source", "title", "artist", "synced"),
            show="headings",
            selectmode="browse",
            height=7,
        )
        for column, title, width in [
            ("score", "得分", 90),
            ("source", "来源", 120),
            ("title", "标题", 220),
            ("artist", "歌手", 180),
            ("synced", "同步", 80),
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

        preview_frame = ttk.LabelFrame(right, text="预览", padding=8)
        preview_frame.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        self.preview = tk.Text(preview_frame, wrap="word", height=16, relief="flat")
        self.preview.configure(font=self._mono_font, background="#fbfbfc", foreground="#1f2937")
        preview_scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview.yview)
        self.preview.configure(yscrollcommand=preview_scroll.set)
        self.preview.grid(row=0, column=0, sticky="nsew")
        preview_scroll.grid(row=0, column=1, sticky="ns")

        output_box = ttk.Frame(right)
        output_box.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        output_box.columnconfigure(1, weight=1)
        ttk.Label(output_box, text="输出").grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(output_box, textvariable=self.output_var).grid(
            row=0, column=1, sticky="ew", padx=(0, 8)
        )
        ttk.Button(output_box, text="使用同名文件", command=self._set_sidecar_output).grid(
            row=0, column=2, padx=(0, 8)
        )
        ttk.Button(output_box, text="浏览", command=self._pick_output).grid(row=0, column=3)

        status = ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(10, 4))
        status.grid(row=3, column=0, sticky="ew")

    def _pick_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择音乐文件夹")
        if folder:
            self.folder_var.set(folder)
            self._load_folder()

    def _load_folder(self) -> None:
        folder = Path(self.folder_var.get().strip())
        if not folder.exists():
            messagebox.showerror("歌词编辑器", "请选择有效的文件夹。")
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
        self.status_var.set(f"已从 {folder} 加载 {len(self._audio_items)} 个音频文件")
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
        self._set_search_fields(track)
        self.meta_title.set(track.display_title)
        self.meta_artist.set(track.artist_text or "")
        self.meta_album.set(track.album or "")
        self.meta_duration.set(f"{track.duration:.2f}s" if track.duration else "")
        self._update_cover_art(track)
        self._update_output_default()
        if track.embedded_lyrics is not None:
            self._show_lyrics(track.embedded_lyrics)
        else:
            self.preview.delete("1.0", "end")
        self.status_var.set(f"已选中 {track.path.name}")
        if self.auto_search_var.get():
            self._start_search()

    def _start_search(self) -> None:
        if self._search_running:
            return
        track = self._build_search_track()
        if track is None:
            messagebox.showinfo("歌词编辑器", "请先选择一首歌。")
            return

        provider_names = [name for name, flag in self.provider_vars.items() if flag.get()]
        if not provider_names:
            messagebox.showinfo("歌词编辑器", "请至少勾选一个来源。")
            return

        self._search_running = True
        self._search_token += 1
        token = self._search_token
        self.status_var.set(f"正在搜索 {track.display_title}...")
        self._show_preview_text("正在搜索歌词……")

        thread = threading.Thread(
            target=self._search_worker,
            args=(token, track, provider_names, self.limit_var.get()),
            daemon=True,
        )
        thread.start()

    def _search_worker(
        self,
        token: int,
        track: TrackMetadata,
        provider_names: list[str],
        limit: int,
    ) -> None:
        try:
            candidates = search_candidates(
                track,
                limit=limit,
                provider_names=provider_names,
            )
            self._search_queue.put(("result", token, candidates))
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
                    self._apply_candidates(candidates)
                elif kind == "error":
                    exc = payload[0]
                    self.status_var.set(f"搜索失败：{exc}")
                    self._show_preview_text(f"搜索失败：\n{exc}")
                self._search_running = False
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _apply_candidates(self, candidates: list[LyricCandidate]) -> None:
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
                    "yes"
                    if (candidate.lyrics.lines or candidate.lyrics.words or candidate.lyrics.synced_text)
                    else "no",
                ),
            )
        self.meta_source.set(candidates[0].lyrics.source if candidates else "-")
        self.meta_score.set(f"{candidates[0].score:.2f}" if candidates else "-")
        self.status_var.set(
            f"已找到 {len(candidates)} 个候选，使用 {len([1 for flag in self.provider_vars.values() if flag.get()])} 个来源"
        )
        if candidates:
            self.candidate_tree.selection_set("0")
            self.candidate_tree.focus("0")
            self._show_candidate(candidates[0])
        else:
            self._show_preview_text("未找到歌词。")

    def _on_candidate_select(self, _event: object) -> None:
        selection = self.candidate_tree.selection()
        if not selection:
            return
        index = int(selection[0])
        if 0 <= index < len(self._candidate_items):
            self._show_candidate(self._candidate_items[index])

    def _show_candidate(self, candidate: LyricCandidate) -> None:
        self.meta_source.set(candidate.lyrics.source)
        self.meta_score.set(f"{candidate.score:.2f}")
        self._show_lyrics(candidate.lyrics)

    def _show_lyrics(self, lyrics) -> None:
        preview = lyrics_preview(
            lyrics,
            max_lines=None,
            max_chars=None,
            show_translation=self.show_translation_var.get(),
        )
        if not preview:
            preview = to_lrc(lyrics, show_translation=self.show_translation_var.get())
        self._show_preview_text(preview or "暂无可显示内容。")

    def _show_preview_text(self, text: str) -> None:
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.see("1.0")

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
            messagebox.showinfo("歌词编辑器", "请先搜索歌词。")
            return
        self._save_candidate(self._candidate_items[0])

    def _save_selected(self) -> None:
        candidate = self._selected_candidate()
        if candidate is None:
            messagebox.showinfo("歌词编辑器", "请先搜索歌词。")
            return
        self._save_candidate(candidate)

    def _save_candidate(self, candidate: LyricCandidate) -> None:
        output = Path(self.output_var.get().strip())
        if not output:
            messagebox.showerror("歌词编辑器", "请选择输出路径。")
            return
        if not candidate.lyrics.lines and not candidate.lyrics.words and not candidate.lyrics.synced_text:
            messagebox.showinfo("歌词编辑器", "所选候选没有可保存的歌词。")
            return
        if self.save_to_audio_var.get():
            if output.suffix.lower() not in {
                ".aac",
                ".aiff",
                ".alac",
                ".ape",
                ".flac",
                ".m4a",
                ".mp3",
                ".ogg",
                ".opus",
                ".wav",
                ".wma",
            }:
                messagebox.showerror("歌词编辑器", "请先选择一个支持写入歌词的音频文件。")
                return
            write_embedded_lyrics(
                output,
                candidate.lyrics,
                show_translation=self.save_translation_var.get(),
            )
        else:
            output.write_text(
                to_lrc(candidate.lyrics, show_translation=self.save_translation_var.get()),
                encoding="utf-8",
            )
        self.status_var.set(f"已保存 {output}")
        messagebox.showinfo("歌词编辑器", f"已保存歌词到 {output}")

    def _pick_output(self) -> None:
        if self.save_to_audio_var.get():
            filename = filedialog.asksaveasfilename(
                title="选择音频文件",
                filetypes=[
                    ("音频文件", "*.mp3 *.m4a *.flac *.ogg *.opus *.wma *.aac *.wav *.ape *.aiff"),
                    ("所有文件", "*.*"),
                ],
            )
        else:
            filename = filedialog.asksaveasfilename(
                title="另存歌词",
                defaultextension=".lrc",
                filetypes=[("LRC 文件", "*.lrc"), ("所有文件", "*.*")],
            )
        if filename:
            self.output_var.set(filename)

    def _set_sidecar_output(self) -> None:
        if self._selected_track_path is None:
            return
        if self.save_to_audio_var.get():
            self.output_var.set(str(self._selected_track_path))
        else:
            self.output_var.set(str(self._selected_track_path.with_suffix(".lrc")))

    def _set_search_fields(self, track: TrackMetadata) -> None:
        self.search_title_var.set(track.title or track.display_title)
        self.search_artist_var.set(track.artist_text or "")
        self.search_album_var.set(track.album or "")

    def _reset_search_fields(self) -> None:
        if self._selected_track is not None:
            self._set_search_fields(self._selected_track)

    def _build_search_track(self) -> TrackMetadata | None:
        if self._selected_track is None:
            return None
        return build_search_track(
            self._selected_track,
            title=self.search_title_var.get(),
            artist=self.search_artist_var.get(),
            album=self.search_album_var.get(),
        )

    def _refresh_preview(self) -> None:
        candidate = self._selected_candidate()
        if candidate is not None:
            self._show_candidate(candidate)
            return
        if self._selected_track and self._selected_track.embedded_lyrics is not None:
            self._show_lyrics(self._selected_track.embedded_lyrics)

    def _update_output_default(self) -> None:
        if self._selected_track_path is None:
            return
        if self.save_to_audio_var.get():
            self.output_var.set(str(self._selected_track_path))
        else:
            self.output_var.set(str(self._selected_track_path.with_suffix(".lrc")))

    def _update_cover_art(self, track: TrackMetadata) -> None:
        if Image is None or ImageTk is None or not track.cover_data:
            self._cover_photo = None
            self.cover_label.configure(image="", text="无封面")
            return
        try:
            image = Image.open(io.BytesIO(track.cover_data))
            image.thumbnail((160, 160))
            self._cover_photo = ImageTk.PhotoImage(image)
            self.cover_label.configure(image=self._cover_photo, text="")
            self.cover_label.image = self._cover_photo
        except Exception:
            self._cover_photo = None
            self.cover_label.configure(image="", text="封面无法显示")

    def _set_initial_window_size(self) -> None:
        self.update_idletasks()
        try:
            self.state("zoomed")
            return
        except tk.TclError:
            pass
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = min(1680, max(1280, screen_w - 80))
        height = min(980, max(760, screen_h - 120))
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")


def _enable_windows_hidpi() -> None:
    if platform.system() != "Windows":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def run_app() -> None:
    app = LyricsEditorApp()
    app.mainloop()
