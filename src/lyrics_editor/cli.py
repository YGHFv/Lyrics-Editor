from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from lyrics_editor.align.asr import FasterWhisperTranscriber
from lyrics_editor.align.timeline import align_lyrics_to_transcript
from lyrics_editor.audio import iter_audio_files, read_metadata
from lyrics_editor.lrc import lyrics_from_lrc, lyrics_preview, to_lrc
from lyrics_editor.providers.catalog import search_candidates

app = typer.Typer(help="Local music lyrics matcher and timeline editor.")
console = Console()


@app.command()
def inspect(path: Path) -> None:
    """Read audio metadata."""
    track = read_metadata(path)
    table = Table(title=str(path))
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Title", track.title or "")
    table.add_row("Artist", track.artist_text or "")
    table.add_row("Album", track.album or "")
    table.add_row("Duration", f"{track.duration:.2f}s" if track.duration else "")
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
) -> None:
    """Search online lyrics for one local audio file."""
    track = read_metadata(path)
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
) -> None:
    """Search the best synced lyrics and save it as LRC."""
    track = read_metadata(path)
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
        console.print(f"[yellow]No lyrics found:[/] {path}")
        raise typer.Exit(code=1)

    best = candidates[0]
    if not best.lyrics.lines and not best.lyrics.synced_text:
        console.print("[yellow]Best candidate has no synced lyrics. Nothing saved.[/]")
        _print_candidates(candidates)
        raise typer.Exit(code=1)

    target = output or path.with_suffix(".lrc")
    target.write_text(to_lrc(best.lyrics), encoding="utf-8")
    console.print(f"[green]Saved[/] {target}  score={best.score}")


@app.command()
def choose(
    path: Path,
    output: Path | None = None,
    limit: int = 10,
    preview_lines: int = 3,
    index: int | None = None,
    providers: str | None = None,
) -> None:
    """Preview candidates and let you pick one manually."""
    track = read_metadata(path)
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
        console.print(f"[yellow]No lyrics found:[/] {path}")
        raise typer.Exit(code=1)

    _print_candidates(candidates, preview_lines=preview_lines)
    chosen_index = index
    if chosen_index is None:
        chosen_index = typer.prompt("Choose candidate index", type=int, default=0)

    if chosen_index < 0 or chosen_index >= len(candidates):
        console.print(f"[red]Invalid candidate index:[/] {chosen_index}")
        raise typer.Exit(code=1)

    chosen = candidates[chosen_index]
    if not chosen.lyrics.lines and not chosen.lyrics.synced_text:
        console.print("[yellow]Chosen candidate has no synced lyrics. Nothing saved.[/]")
        console.print(f"Preview: {lyrics_preview(chosen.lyrics, max_lines=preview_lines)}")
        raise typer.Exit(code=1)

    target = output or path.with_suffix(".lrc")
    target.write_text(to_lrc(chosen.lyrics), encoding="utf-8")
    console.print(
        f"[green]Saved[/] {target}  score={chosen.score}  choice={chosen_index}"
    )


@app.command()
def scan(root: Path, save: bool = False, limit: int = 10, providers: str | None = None) -> None:
    """Scan a file or directory, optionally saving best matched LRC files."""
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
            console.print(f"[yellow]No lyrics found:[/] {path}")
            continue
        best = candidates[0]
        console.print(f"{path} -> {best.lyrics.title} / {best.lyrics.artist} score={best.score}")
        if save and (best.lyrics.lines or best.lyrics.synced_text):
            target = path.with_suffix(".lrc")
            target.write_text(to_lrc(best.lyrics), encoding="utf-8")
            console.print(f"  [green]saved[/] {target}")


@app.command()
def repair(
    audio_path: Path,
    lyrics_path: Path,
    output: Path | None = None,
    model_size: str = "medium",
) -> None:
    """Repair an LRC timeline with ASR transcript timestamps."""
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
    console.print(f"[green]Saved repaired LRC[/] {target}")
    if repaired.words:
        console.print(f"[cyan]Captured word timings:[/] {len(repaired.words)} words")


@app.command()
def gui() -> None:
    """Open the desktop interface."""
    try:
        from lyrics_editor.ui import run_app
    except ImportError as exc:
        console.print(f"[red]GUI unavailable:[/] {exc}")
        raise typer.Exit(code=1) from exc

    run_app()


def _print_candidates(candidates) -> None:
    table = Table(title="Lyrics candidates")
    table.add_column("#", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Source")
    table.add_column("Title")
    table.add_column("Artist")
    table.add_column("Synced")
    table.add_column("Preview")
    table.add_column("Reasons")
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
