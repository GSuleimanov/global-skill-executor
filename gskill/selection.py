"""Interactive prompts (questionary). Single responsibility: ask the user."""
from __future__ import annotations

from pathlib import Path

import questionary
from questionary import Choice

from .discovery import Skill
from .registry import Registry


def select_skills(skills: list[Skill], reg: Registry) -> None:
    """Checkbox UI to enable/disable skills; mutates the registry in place."""
    if not skills:
        return
    choices = [
        Choice(
            title=f"{s.name}  —  {s.description or s.provider}",
            value=s.uid,
            checked=reg.is_enabled(s.uid),
        )
        for s in skills
    ]
    picked = questionary.checkbox(
        "Select the skills to keep enabled (space to toggle, enter to confirm):",
        choices=choices,
    ).ask()
    if picked is None:  # user aborted
        return
    picked_set = set(picked)
    for s in skills:
        reg.set_enabled(s.uid, s.uid in picked_set)


def ask_directory(message: str) -> Path | None:
    answer = questionary.path(message, only_directories=True).ask()
    if not answer:
        return None
    return Path(answer).expanduser()


def confirm(message: str, default: bool = True) -> bool:
    return bool(questionary.confirm(message, default=default).ask())


def pick_one(message: str, options: list[str], default: str | None = None) -> str | None:
    return questionary.select(message, choices=options, default=default).ask()
