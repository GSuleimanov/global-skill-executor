"""Model catalogs per engine. Single responsibility: know the model lists."""
from __future__ import annotations

import json
import shutil
import subprocess

# Engine keys used throughout the app.
ENGINES = ("claude", "cursor", "local")

# Static fallbacks. Latest Claude models first.
_CLAUDE = ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5"]
_CURSOR = ["auto", "claude-opus-4-8", "claude-sonnet-4-6", "gpt-5"]


def available_models(engine: str) -> list[str]:
    """Return selectable models for an engine, discovering local ones live."""
    if engine == "claude":
        return list(_CLAUDE)
    if engine == "cursor":
        return list(_CURSOR)
    if engine == "local":
        return _ollama_models()
    return []


def _ollama_models() -> list[str]:
    if not shutil.which("ollama"):
        return []
    try:
        out = subprocess.run(
            ["ollama", "list", "--format", "json"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip().startswith(("[", "{")):
            data = json.loads(out.stdout)
            rows = data if isinstance(data, list) else data.get("models", [])
            return [r["name"] for r in rows if "name" in r]
    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError):
        pass
    # Fallback: parse the plain table output.
    try:
        out = subprocess.run(["ollama", "list"], capture_output=True,
                             text=True, timeout=10)
        lines = out.stdout.strip().splitlines()[1:]  # drop header
        return [ln.split()[0] for ln in lines if ln.strip()]
    except (subprocess.SubprocessError, IndexError):
        return []


def default_model(engine: str) -> str | None:
    models = available_models(engine)
    return models[0] if models else None
