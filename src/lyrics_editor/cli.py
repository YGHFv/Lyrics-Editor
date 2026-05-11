from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from lyrics_editor.align.asr import FasterWhisperTranscriber
from lyrics_editor.align.timeline import align_lyrics_to_transcript
from lyrics_editor.audio import iter_audio_files, read_metadata
from lyrics_editor.lrc import lyrics_from_lrc, lyrics_preview, to_lrc
from lyrics_editor.searching import build_search_track
from lyrics_editor.providers.catalog import search_candidates

app = typer.Typer(help="本地音乐歌词匹配与时间轴编辑工具。")
console = Console()


@app.command()
def inspect(path: Path) -> None:
    """读取音频元数据。"""
    track = read_metadata(path)
    table = Table(title=str(path))
    table.add_column("字段")
    table.add_column("值")
    table.add_row("标题", track.title or "")
    table.add_row("歌手", track.artist_text or "")
    table.add_row("专辑", track.album or "")
    table.add_row("时长", f"{track.duration:.2f}s" if track.duration else "")
    console.print(table)


def _parse_provider_names(provider_names: str | None) -> list[str] | None:
    if provider_names is None:
        return None
    names = [name.strip() for name in provider_names.split(",") if name.strip()]
    return names or None


@app.command()
def search(
    path: Path,
    limit: int = 10,
    preview_lines: int = 3,
    providers: str | None = None,
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
) -> None:
    """搜索单个本地音频文件的在线歌词。"""
    track = build_search_track(read_metadata(path), title=title, artist=artist, album=album)
    try:
        candidates = search_candidates(
            track,
            limit=limit,
            provider_names=_parse_provider_names(providers),
        )
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc
    _print_candidates(candidates, preview_lines=preview_lines)


@app.command()
def match(
    path: Path,
    output: Path | None = None,
    limit: int = 10,
    providers: str | None = None,
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
) -> None:
    """搜索最合适的同步歌词并保存为 LRC。"""
    track = build_search_track(read_metadata(path), title=title, artist=artist, album=album)
    try:
        candidates = search_candidates(
            track,
            limit=limit,
            provider_names=_parse_provider_names(providers),
        )
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc
    if not candidates:
        console.print(f"[yellow]未找到歌词：[/] {path}")
        raise typer.Exit(code=1)

    best = candidates[0]
    if not best.lyrics.lines and not best.lyrics.synced_text:
        console.print("[yellow]最佳候选没有同步歌词，未保存。[/]")
        _print_candidates(candidates)
        raise typer.Exit(code=1)

    target = output or path.with_suffix(".lrc")
    target.write_text(to_lrc(best.lyrics), encoding="utf-8")
    console.print(f"[green]已保存[/] {target}  得分={best.score}")


@app.command()
def choose(
    path: Path,
    output: Path | None = None,
    limit: int = 10,
    preview_lines: int = 3,
    index: int | None = None,
    providers: str | None = None,
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
) -> None:
    """预览候选歌词并手动选择一个。"""
    track = build_search_track(read_metadata(path), title=title, artist=artist, album=album)
    try:
        candidates = search_candidates(
            track,
            limit=limit,
            provider_names=_parse_provider_names(providers),
        )
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc
    if not candidates:
        console.print(f"[yellow]未找到歌词：[/] {path}")
        raise typer.Exit(code=1)

    _print_candidates(candidates, preview_lines=preview_lines)
    chosen_index = index
    if chosen_index is None:
        chosen_index = typer.prompt("请选择候选序号", type=int, default=0)

    if chosen_index < 0 or chosen_index >= len(candidates):
        console.print(f"[red]候选序号无效：[/] {chosen_index}")
        raise typer.Exit(code=1)

    chosen = candidates[chosen_index]
    if not chosen.lyrics.lines and not chosen.lyrics.synced_text:
        console.print("[yellow]所选候选没有同步歌词，未保存。[/]")
        console.print(f"预览：{lyrics_preview(chosen.lyrics, max_lines=preview_lines)}")
        raise typer.Exit(code=1)

    target = output or path.with_suffix(".lrc")
    target.write_text(to_lrc(chosen.lyrics), encoding="utf-8")
    console.print(
        f"[green]已保存[/] {target}  得分={chosen.score}  选择={chosen_index}"
    )


@app.command()
def scan(root: Path, save: bool = False, limit: int = 10, providers: str | None = None) -> None:
    """扫描文件或目录，可选自动保存最佳匹配的 LRC。"""
    for path in iter_audio_files(root):
        track = read_metadata(path)
        try:
            candidates = search_candidates(
                track,
                limit=limit,
                provider_names=_parse_provider_names(providers),
            )
        except RuntimeError as exc:
            console.print(f"[red]{exc}[/]")
            continue
        if not candidates:
            console.print(f"[yellow]未找到歌词：[/] {path}")
            continue
        best = candidates[0]
        console.print(f"{path} -> {best.lyrics.title} / {best.lyrics.artist} 得分={best.score}")
        if save and (best.lyrics.lines or best.lyrics.synced_text):
            target = path.with_suffix(".lrc")
            target.write_text(to_lrc(best.lyrics), encoding="utf-8")
            console.print(f"  [green]已保存[/] {target}")


@app.command()
def repair(
    audio_path: Path,
    lyrics_path: Path,
    output: Path | None = None,
    model_size: str = "medium",
) -> None:
    """使用 ASR 转写时间戳修正 LRC 时间轴。"""
    track = read_metadata(audio_path)
    raw_lrc = lyrics_path.read_text(encoding="utf-8-sig")
    lyrics = lyrics_from_lrc(
        source="local",
        title=track.display_title,
        artist=track.artist_text or "",
        album=track.album,
        duration=track.duration,
        text=raw_lrc,
    )
    transcript = FasterWhisperTranscriber(model_size=model_size).transcribe(audio_path)
    repaired = align_lyrics_to_transcript(lyrics, transcript)

    target = output or lyrics_path.with_name(f"{lyrics_path.stem}.repaired.lrc")
    target.write_text(to_lrc(repaired), encoding="utf-8")
    console.print(f"[green]已保存修正后的 LRC[/] {target}")
    if repaired.words:
        console.print(f"[cyan]已保留逐字时间戳：[/] {len(repaired.words)} 个词")


@app.command()
def gui(watch: bool = False) -> None:
    """打开桌面界面。"""
    try:
        from lyrics_editor.ui import run_app
    except ImportError as exc:
        console.print(f"[red]界面不可用：[/] {exc}")
        raise typer.Exit(code=1) from exc

    if watch:
        _run_gui_with_watch()
        return
    run_app()


def _run_gui_with_watch() -> None:
    watch_roots = [Path("src"), Path("pyproject.toml")]
    snapshot = _snapshot_files(watch_roots)
    console.print("[cyan]开发模式已启动：[/] 代码变化后会自动重启界面。按 Ctrl+C 退出。")
    while True:
        process = subprocess.Popen(
            [sys.executable, "-c", "from lyrics_editor.ui import run_app; run_app()"]
        )
        try:
            while process.poll() is None:
                time.sleep(0.8)
                current = _snapshot_files(watch_roots)
                if current != snapshot:
                    snapshot = current
                    console.print("[yellow]检测到代码变更，正在重启界面...[/]")
                    process.terminate()
                    process.wait(timeout=5)
                    break
            else:
                break
        except KeyboardInterrupt:
            process.terminate()
            process.wait(timeout=5)
            raise typer.Exit()


def _snapshot_files(paths: list[Path]) -> dict[str, tuple[int, int]]:
    snapshot: dict[str, tuple[int, int]] = {}
    for path in paths:
        if path.is_file():
            stat = path.stat()
            snapshot[str(path)] = (int(stat.st_mtime_ns), int(stat.st_size))
            continue
        if path.is_dir():
            for file in path.rglob("*.py"):
                stat = file.stat()
                snapshot[str(file)] = (int(stat.st_mtime_ns), int(stat.st_size))
    return snapshot


def _print_candidates(candidates) -> None:
    table = Table(title="候选歌词")
    table.add_column("序号", justify="right")
    table.add_column("得分", justify="right")
    table.add_column("来源")
    table.add_column("标题")
    table.add_column("歌手")
    table.add_column("同步")
    table.add_column("预览")
    table.add_column("原因")
    for index, candidate in enumerate(candidates):
        table.add_row(
            str(index),
            f"{candidate.score:.2f}",
            candidate.lyrics.source,
            candidate.lyrics.title,
            candidate.lyrics.artist,
            "yes" if candidate.lyrics.lines else "no",
            lyrics_preview(candidate.lyrics),
            ", ".join(candidate.reasons),
        )
    console.print(table)


if __name__ == "__main__":
    app()
