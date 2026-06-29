"""Persistent state: registered project dirs, skill enable/disable, aliases.

Single responsibility: load/save the JSON store. No UI, no scanning.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
STORE_PATH = _CONFIG_HOME / "gskill" / "registry.json"


@dataclass
class Registry:
    # alias -> absolute base dir path (string)
    projects: dict[str, str] = field(default_factory=dict)
    # skill uid -> enabled?  (absent = enabled by default)
    enabled: dict[str, bool] = field(default_factory=dict)
    # last engine/model the user chose, reused as defaults
    last_engine: str = ""
    last_model: dict[str, str] = field(default_factory=dict)  # engine -> model

    # --- skills ---------------------------------------------------------
    def is_enabled(self, uid: str) -> bool:
        return self.enabled.get(uid, True)

    def set_enabled(self, uid: str, value: bool) -> None:
        self.enabled[uid] = value

    # --- projects -------------------------------------------------------
    def add_project(self, base: Path) -> str:
        base = base.expanduser().resolve()
        alias = self._unique_alias(base)
        self.projects[alias] = str(base)
        return alias

    def _unique_alias(self, base: Path) -> str:
        # reuse existing alias if already registered
        for alias, path in self.projects.items():
            if path == str(base):
                return alias
        name = base.name or "root"
        if name not in self.projects:
            return name
        i = 2
        while f"{name}-{i}" in self.projects:
            i += 1
        return f"{name}-{i}"

    def resolve(self, alias_or_path: str) -> Path | None:
        if alias_or_path in self.projects:
            return Path(self.projects[alias_or_path])
        p = Path(alias_or_path).expanduser()
        return p if p.exists() else None


def load() -> Registry:
    if STORE_PATH.exists():
        try:
            data = json.loads(STORE_PATH.read_text())
            return Registry(**{k: data[k] for k in data if k in Registry().__dict__})
        except (json.JSONDecodeError, TypeError):
            pass
    return Registry()


def save(reg: Registry) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(asdict(reg), indent=2))
