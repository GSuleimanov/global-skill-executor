"""Rich-based presentation helpers. Single responsibility: looks, not logic.

Palette: blue (primary), green (success), orange (accent/warn), gray (dim),
white (default text). No purple, no banner.
"""
from __future__ import annotations

import time
from collections.abc import Iterable

from rich.console import Console
from rich.table import Table

from .discovery import ConfigHit

console = Console()

BLUE = "blue"
GREEN = "green"
ORANGE = "dark_orange"
GRAY = "grey50"


def spinner(message: str, seconds: float = 0.4) -> None:
    """Tiny status used between steps."""
    with console.status(f"[{BLUE}]{message}", spinner="line"):
        time.sleep(seconds)


def configs_table(label: str, hits: Iterable[ConfigHit]) -> None:
    table = Table(title=f"AI configs in {label}", title_style=f"bold {BLUE}",
                  border_style=GRAY, expand=False)
    table.add_column("Provider", style="bold white")
    table.add_column("Config dir", style=GRAY)
    table.add_column("Skills", justify="right", style=GREEN)
    any_row = False
    for hit in hits:
        any_row = True
        table.add_row(hit.provider.label, str(hit.config_dir), str(len(hit.skills)))
    if not any_row:
        console.print(f"[{ORANGE}]No known AI configs found in {label}.")
        return
    console.print(table)


def projects_table(projects: dict[str, str]) -> None:
    if not projects:
        console.print(f"[{GRAY}]No registered projects yet.")
        return
    table = Table(title="Project aliases", title_style=f"bold {BLUE}",
                  border_style=GRAY)
    table.add_column("Alias", style=f"bold {GREEN}")
    table.add_column("Path", style=GRAY)
    for alias, path in projects.items():
        table.add_row(alias, path)
    console.print(table)


def info(msg: str) -> None:
    console.print(f"[{BLUE}]i[/{BLUE}] {msg}")


def ok(msg: str) -> None:
    console.print(f"[{GREEN}]+[/{GREEN}] {msg}")


def warn(msg: str) -> None:
    console.print(f"[{ORANGE}]![/{ORANGE}] {msg}")


def error(msg: str) -> None:
    console.print(f"[red]x[/red] {msg}")
