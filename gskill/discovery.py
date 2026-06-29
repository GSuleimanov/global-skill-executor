"""Scan a base directory for AI configs and the skills inside them.

Single responsibility: turn a directory on disk into Skill/ConfigHit records.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .providers import PROVIDERS, Provider


@dataclass(frozen=True)
class Skill:
    """One runnable skill discovered on disk."""

    name: str           # display name (dir name or file stem)
    path: Path          # the SKILL.md / rule file
    provider: str       # provider key
    base: Path          # the base dir this was discovered under
    description: str = ""

    @property
    def uid(self) -> str:
        """Stable identity used for selection persistence and lookup."""
        return f"{self.base}::{self.provider}::{self.name}"


@dataclass(frozen=True)
class ConfigHit:
    """A provider config found under a base dir, with its skills."""

    provider: Provider
    config_dir: Path
    skills: tuple[Skill, ...]


def _read_description(path: Path) -> str:
    """Best-effort one-line description from frontmatter or first heading."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    for line in text.splitlines():
        s = line.strip()
        if s.lower().startswith("description:"):
            return s.split(":", 1)[1].strip().strip("'\"")
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()
        if s:
            return s[:80]
    return ""


def _skill_name(match: Path, glob: str) -> str:
    # For "skills/*/SKILL.md" the name is the parent dir; otherwise the stem.
    if match.name.upper() == "SKILL.MD":
        return match.parent.name
    return match.stem


def discover(base: Path) -> list[ConfigHit]:
    """Find every provider config and its skills under ``base``."""
    base = base.expanduser().resolve()
    hits: list[ConfigHit] = []
    for provider in PROVIDERS:
        for dir_name in provider.config_dirs:
            config_dir = base / dir_name
            if not config_dir.is_dir():
                continue
            skills: list[Skill] = []
            seen: set[Path] = set()
            for glob in provider.skill_globs:
                for match in sorted(config_dir.glob(glob)):
                    if not match.is_file() or match in seen:
                        continue
                    seen.add(match)
                    skills.append(
                        Skill(
                            name=_skill_name(match, glob),
                            path=match,
                            provider=provider.key,
                            base=base,
                            description=_read_description(match),
                        )
                    )
            hits.append(ConfigHit(provider, config_dir, tuple(skills)))
            break  # one config dir per provider per base
    return hits


def all_skills(hits: list[ConfigHit]) -> list[Skill]:
    return [s for h in hits for s in h.skills]
