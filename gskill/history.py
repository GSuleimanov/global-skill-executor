"""Run summaries: persist each run, prune stale ones, match prior context.

Single responsibility: the on-disk summary store and its matching rules.

Summary file format (stable contract — other AI calls rely on it):

    Line 1:  # <skill-title>
    Line 2:  date: YYYY-MM-DD | engine: <e> | model: <m> | project: <p> | relative: <bool>
    Line 3:  brief: <one-line description used for context matching>
    Line 4:  (blank)
    >=5:     ## Result
             <captured output>

Files are named ``YYYY-MM-DD-<skill-slug>.md`` so the date is visible and
multiple runs of the same skill on the same day overwrite (latest wins).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .discovery import Skill

_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
HISTORY_DIR = _CONFIG_HOME / "gskill" / "history"
MAX_AGE_DAYS = 3

# Words ignored when matching descriptions.
_STOP = {"the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "with",
         "skill", "use", "using", "this", "that", "your", "you", "it"}


@dataclass(frozen=True)
class Summary:
    path: Path
    title: str
    day: date
    brief: str

    def read(self) -> str:
        try:
            return self.path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    return s.strip("-") or "skill"


def _file_date(path: Path) -> date | None:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})-", path.name)
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None


def prune(today: date | None = None) -> int:
    """Delete summaries older than MAX_AGE_DAYS. Returns number removed."""
    today = today or date.today()
    if not HISTORY_DIR.exists():
        return 0
    removed = 0
    for path in HISTORY_DIR.glob("*.md"):
        d = _file_date(path) or date.fromtimestamp(path.stat().st_mtime)
        if (today - d).days > MAX_AGE_DAYS:
            try:
                path.unlink()
                removed += 1
            except OSError:
                pass
    return removed


def save(skill: Skill, engine: str, model: str, *, relative: bool,
         output: str, when: datetime | None = None) -> Path:
    when = when or datetime.now()
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    path = HISTORY_DIR / f"{when:%Y-%m-%d}-{slugify(skill.name)}.md"
    brief = (skill.description or "").replace("\n", " ").strip() or "(no description)"
    header = (
        f"# {skill.name}\n"
        f"date: {when:%Y-%m-%d} | engine: {engine} | model: {model} | "
        f"project: {skill.base.name} | relative: {str(relative).lower()}\n"
        f"brief: {brief}\n\n"
        f"## Result\n"
    )
    path.write_text(header + output.rstrip() + "\n", encoding="utf-8")
    return path


def parse(path: Path) -> Summary | None:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if not lines:
        return None
    title = lines[0].lstrip("# ").strip()
    brief = ""
    if len(lines) >= 3 and lines[2].lower().startswith("brief:"):
        brief = lines[2].split(":", 1)[1].strip()
    day = _file_date(path) or date.fromtimestamp(path.stat().st_mtime)
    return Summary(path=path, title=title, day=day, brief=brief)


def recent(today: date | None = None) -> list[Summary]:
    today = today or date.today()
    if not HISTORY_DIR.exists():
        return []
    out: list[Summary] = []
    for path in sorted(HISTORY_DIR.glob("*.md"), reverse=True):
        s = parse(path)
        if s and (today - s.day).days <= MAX_AGE_DAYS:
            out.append(s)
    return out


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower())
            if w not in _STOP and len(w) > 2}


def matches(skill: Skill) -> list[Summary]:
    """Prior summaries relevant to ``skill`` by title, else by description."""
    want_title = skill.name.strip().lower()
    want_tokens = _tokens(skill.description)
    hits: list[Summary] = []
    for s in recent():
        if s.title.strip().lower() == want_title:
            hits.append(s)
        elif want_tokens and len(want_tokens & _tokens(s.brief)) >= 2:
            hits.append(s)
    return hits


def render_context(summaries: list[Summary], max_chars: int = 4000) -> str:
    """Compact block of prior runs to inject into a prompt."""
    if not summaries:
        return ""
    parts = ["## Prior related runs (most recent first)"]
    for s in summaries:
        body = s.read()
        if len(body) > max_chars:
            body = body[:max_chars] + "\n…(truncated)…"
        parts.append(body)
    return "\n\n".join(parts)
