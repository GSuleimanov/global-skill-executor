"""Interactive prompts (questionary). Single responsibility: ask the user."""
from __future__ import annotations

from pathlib import Path

import questionary
from questionary import Choice, Separator

from .discovery import Skill
from .registry import Registry

# Color scheme for the fuzzy pickers.
_STYLE = questionary.Style([
    ("separator", "fg:#888888 italic"),   # project group headers
    ("qmark", "fg:#d75fff bold"),
    ("pointer", "fg:#d75fff bold"),
    ("highlighted", "fg:#d75fff bold"),
    ("selected", "fg:#5fd700"),
    ("answer", "fg:#5fd700 bold"),
])


def _filterable(message: str, choices, default=None):
    return questionary.select(
        message, choices=choices, default=default, style=_STYLE,
        use_search_filter=True, use_jk_keys=False,
        instruction="(type to filter, ↑↓ to move, enter to select)",
    ).ask()


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
    return questionary.select(message, choices=options, default=default,
                              style=_STYLE).ask()


def pick_filterable(message: str, options: list[str],
                    default: str | None = None) -> str | None:
    """Single select with type-to-filter (used for model lists, etc.)."""
    return _filterable(message, options, default)


def pick_skill(skills: list[Skill]) -> Skill | None:
    """Fuzzy picker, grouped by project with colored group headers."""
    by_project: dict[str, list[Skill]] = {}
    for s in skills:
        by_project.setdefault(s.base.name, []).append(s)

    choices: list = []
    index: dict[int, Skill] = {}
    counter = 0
    for project in sorted(by_project):
        choices.append(Separator(f"  ▸ {project}"))
        for s in sorted(by_project[project], key=lambda x: x.name):
            title = f"    {s.name}  —  {s.description or s.provider}"
            choices.append(Choice(title=title, value=counter))
            index[counter] = s
            counter += 1

    picked = _filterable("Pick a skill:", choices)
    if picked is None:
        return None
    return index[picked]
