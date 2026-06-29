"""Rich-based presentation helpers. Single responsibility: looks, not logic."""
from __future__ import annotations

import time
from collections.abc import Iterable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .discovery import ConfigHit

console = Console()


def banner() -> None:
    title = Text()
    title.append("⚡ ", style="bold yellow")
    title.append("Global Skill Executor", style="bold magenta")
    title.append("  ·  run AI skills anywhere", style="dim")
    console.print(Panel(title, border_style="magenta", padding=(0, 2)))


def spinner(message: str, seconds: float = 0.6) -> None:
    """Tiny animated status used between steps."""
    with console.status(f"[cyan]{message}", spinner="dots"):
        time.sleep(seconds)


def configs_table(label: str, hits: Iterable[ConfigHit]) -> None:
    table = Table(title=f"AI configs in {label}", title_style="bold cyan",
                  border_style="bright_black", expand=False)
    table.add_column("", justify="center")
    table.add_column("Provider", style="bold")
    table.add_column("Config dir", style="dim")
    table.add_column("Skills", justify="right", style="green")
    any_row = False
    for hit in hits:
        any_row = True
        table.add_row(
            hit.provider.icon,
            hit.provider.label,
            str(hit.config_dir),
            str(len(hit.skills)),
        )
    if not any_row:
        console.print(f"[yellow]No known AI configs found in {label}.")
        return
    console.print(table)


def projects_table(projects: dict[str, str]) -> None:
    if not projects:
        console.print("[dim]No registered projects yet.")
        return
    table = Table(title="Project aliases", title_style="bold cyan",
                  border_style="bright_black")
    table.add_column("Alias", style="bold yellow")
    table.add_column("Path", style="dim")
    for alias, path in projects.items():
        table.add_row(alias, path)
    console.print(table)


def info(msg: str) -> None:
    console.print(f"[cyan]ℹ[/cyan] {msg}")


def ok(msg: str) -> None:
    console.print(f"[green]✓[/green] {msg}")


def warn(msg: str) -> None:
    console.print(f"[yellow]![/yellow] {msg}")


def error(msg: str) -> None:
    console.print(f"[red]✗[/red] {msg}")
