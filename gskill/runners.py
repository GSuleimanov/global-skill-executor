"""Execute a skill through an engine. Single responsibility: build & run cmd."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .discovery import Skill

# CLI binaries each engine needs.
_BINARIES = {"claude": "claude", "cursor": "cursor-agent", "local": "ollama"}


def engine_available(engine: str) -> bool:
    return shutil.which(_BINARIES.get(engine, "")) is not None


def build_prompt(skill: Skill, context: str = "") -> str:
    """Wrap the skill file content into an executable instruction prompt.

    ``context`` is an optional block of prior related runs to inform the model.
    """
    try:
        body = skill.path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        body = ""
    ctx = f"\n\n{context}\n" if context.strip() else ""
    return (
        f"You are executing the skill '{skill.name}'. "
        f"Follow its instructions below and carry out the task end to end."
        f"{ctx}\n"
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


def run(skill: Skill, engine: str, model: str, *, relative: bool,
        context: str = "") -> tuple[int, str]:
    """Run the skill, echoing output live while capturing it.

    ``relative`` => cwd is the skill's project base, else the current dir.
    Returns ``(exit_code, captured_output)``.
    """
    if not engine_available(engine):
        raise RuntimeError(
            f"'{_BINARIES[engine]}' is not installed or not on PATH."
        )
    cwd = skill.base if relative else Path.cwd()
    prompt = build_prompt(skill, context)
    cmd = build_command(engine, model, prompt)
    proc = subprocess.Popen(
        cmd, cwd=str(cwd), stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    captured: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        captured.append(line)
    proc.wait()
    return proc.returncode, "".join(captured)
