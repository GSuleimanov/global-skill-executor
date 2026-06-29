"""Execute a skill through an engine. Single responsibility: build & run cmd."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .discovery import Skill

# CLI binaries each engine needs.
_BINARIES = {"claude": "claude", "cursor": "cursor-agent", "local": "ollama"}


def engine_available(engine: str) -> bool:
    return shutil.which(_BINARIES.get(engine, "")) is not None


def build_prompt(skill: Skill) -> str:
    """Wrap the skill file content into an executable instruction prompt."""
    try:
        body = skill.path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        body = ""
    return (
        f"You are executing the skill '{skill.name}'. "
        f"Follow its instructions below and carry out the task end to end.\n\n"
        f"--- SKILL: {skill.name} ---\n{body}\n--- END SKILL ---"
    )


def build_command(engine: str, model: str, prompt: str) -> list[str]:
    if engine == "claude":
        return ["claude", "-p", prompt, "--model", model]
    if engine == "cursor":
        cmd = ["cursor-agent", "-p", prompt]
        if model and model != "auto":
            cmd += ["--model", model]
        return cmd
    if engine == "local":
        return ["ollama", "run", model, prompt]
    raise ValueError(f"unknown engine: {engine}")


def run(skill: Skill, engine: str, model: str, *, relative: bool) -> int:
    """Run the skill. ``relative`` => cwd is the skill's project base.

    Returns the subprocess exit code.
    """
    if not engine_available(engine):
        raise RuntimeError(
            f"'{_BINARIES[engine]}' is not installed or not on PATH."
        )
    cwd = skill.base if relative else Path.cwd()
    prompt = build_prompt(skill)
    cmd = build_command(engine, model, prompt)
    proc = subprocess.run(cmd, cwd=str(cwd))
    return proc.returncode
