"""Catalog of known AI assistant configs and where their skills live.

Single responsibility: describe *what* an AI config looks like on disk.
No scanning logic here — see discovery.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Provider:
    """A known AI assistant and the layout of its on-disk config."""

    key: str                       # stable id, e.g. "claude"
    label: str                     # human label, e.g. "Claude Code"
    icon: str                      # emoji shown in the UI
    config_dirs: tuple[str, ...]   # candidate config dir names in a base dir
    # glob patterns (relative to a matched config dir) that locate skills.
    # The skill's display name is taken from the matched directory or file stem.
    skill_globs: tuple[str, ...] = field(default_factory=tuple)


# Order matters only for display.
PROVIDERS: tuple[Provider, ...] = (
    Provider(
        key="claude",
        label="Claude Code",
        icon="🟣",
        config_dirs=(".claude",),
        skill_globs=("skills/*/SKILL.md", "skills/*.md"),
    ),
    Provider(
        key="cursor",
        label="Cursor",
        icon="🟦",
        config_dirs=(".cursor",),
        skill_globs=("rules/*.mdc", "rules/*.md", "skills/*/SKILL.md"),
    ),
    Provider(
        key="windsurf",
        label="Windsurf",
        icon="🌊",
        config_dirs=(".windsurf",),
        skill_globs=("rules/*.md", "workflows/*.md"),
    ),
    Provider(
        key="continue",
        label="Continue",
        icon="▶️",
        config_dirs=(".continue",),
        skill_globs=("prompts/*.md", "rules/*.md"),
    ),
    Provider(
        key="aider",
        label="Aider",
        icon="🛠️",
        config_dirs=(".aider",),
        skill_globs=("conventions/*.md",),
    ),
    Provider(
        key="copilot",
        label="GitHub Copilot",
        icon="🐙",
        config_dirs=(".github",),
        skill_globs=("copilot-instructions.md", "prompts/*.md"),
    ),
    Provider(
        key="gemini",
        label="Gemini",
        icon="✨",
        config_dirs=(".gemini",),
        skill_globs=("commands/*.toml", "skills/*/SKILL.md"),
    ),
    Provider(
        key="codeium",
        label="Codeium",
        icon="💠",
        config_dirs=(".codeium",),
        skill_globs=("rules/*.md",),
    ),
)


def by_key(key: str) -> Provider | None:
    return next((p for p in PROVIDERS if p.key == key), None)
