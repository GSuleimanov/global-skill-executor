"""Multi-step orchestration for weak local (Ollama) models.

Single responsibility: turn one skill run into a chain of small, role-scoped
Ollama calls so a small model produces high-quality output.

Best practices applied:
  * Decompose the task into atomic steps (a planner call).
  * Run each step as a *separate* call with a specific role and a tiny context —
    only the goal + a short running summary of prior steps (never the full
    transcript) so context stays small and the model stays focused.
  * Review every step's output and allow one corrective retry.
  * Compress each step result into 1-2 sentences before passing it forward,
    so context never bloats.
  * Synthesize the final deliverable from the full step transcript at the end
    (the one place it's worth spending context).
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Group
from rich.live import Live
from rich.text import Text

from . import ui
from .discovery import Skill

MAX_STEPS = 6
SUMMARY_SENTENCES = 2

# Role presets: a system framing prepended to each call. Kept terse on purpose.
_ROLES = {
    "planner": (
        "You are a planner. Break the task into 3-6 atomic, ordered steps. "
        "Each step must be independently executable. Output ONLY a numbered "
        "list, one step per line, no preamble, no explanation."
    ),
    "executor": (
        "You are a focused worker. Do EXACTLY the current step and nothing "
        "else. Be concrete and complete. Do not restate the task or the plan."
    ),
    "reviewer": (
        "You are a strict reviewer. If the output fully and correctly does the "
        "step, reply with the single word APPROVE. Otherwise reply with a short "
        "bullet list of concrete corrections. Do not rewrite the output."
    ),
    "summarizer": (
        f"You compress text. Summarize the result in at most {SUMMARY_SENTENCES} "
        "sentences, keeping concrete decisions, names and values. No preamble."
    ),
    "synthesizer": (
        "You are an editor. Combine the step results into the single, complete "
        "final deliverable for the goal. Produce only the deliverable."
    ),
}


def _ollama(model: str, role: str, user: str, cwd: Path) -> str:
    """One stateless Ollama call with a role framing. Returns stdout text."""
    prompt = f"{_ROLES[role]}\n\n{user}"
    proc = subprocess.run(
        ["ollama", "run", model, prompt],
        cwd=str(cwd), capture_output=True, text=True,
    )
    return proc.stdout.strip()


def _parse_steps(text: str) -> list[str]:
    steps: list[str] = []
    for line in text.splitlines():
        m = re.match(r"\s*(?:\d+[.)]|[-*])\s+(.*)", line)
        if m and m.group(1).strip():
            steps.append(m.group(1).strip())
    return steps[:MAX_STEPS]


@dataclass
class _Step:
    text: str
    status: str = "pending"   # pending | running | done
    phase: str = ""           # current sub-activity while running
    summary: str = ""         # brief result once done


@dataclass
class _Progress:
    """Live, in-place view of the step pipeline."""

    steps: list[_Step] = field(default_factory=list)
    note: str = ""

    def render(self) -> Group:
        rows: list[Text] = []
        for i, s in enumerate(self.steps, 1):
            if s.status == "done":
                line = Text(f"  ✓ {i}. {_short(s.text, 50)}", style=ui.GREEN)
                if s.summary:
                    line.append(f"  — {_short(s.summary, 70)}", style=ui.GRAY)
            elif s.status == "running":
                line = Text(f"  ⟳ {i}. {_short(s.text, 50)}", style=f"bold {ui.BLUE}")
                if s.phase:
                    line.append(f"  · {s.phase}…", style=ui.ORANGE)
            else:
                line = Text(f"  · {i}. {_short(s.text, 50)}", style=ui.GRAY)
            rows.append(line)
        if self.note:
            rows.append(Text(f"  {self.note}", style=ui.GRAY))
        return Group(*rows)


def _short(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _goal(skill: Skill, context: str, user_context: str) -> str:
    try:
        body = skill.path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        body = ""
    usr = (f"\n\nAdditional context for this run:\n{user_context.strip()}\n"
           if user_context.strip() else "")
    ctx = f"\n\nPrior related context:\n{context}\n" if context.strip() else ""
    return (
        f"GOAL — execute the skill '{skill.name}':\n"
        f"--- SKILL ---\n{body}\n--- END SKILL ---{usr}{ctx}"
    )


def run(skill: Skill, model: str, *, cwd: Path, context: str = "",
        user_context: str = "") -> tuple[int, str]:
    """Run the full multi-step pipeline. Returns ``(exit_code, markdown)``."""
    goal = _goal(skill, context, user_context)
    prog = _Progress(note="Planning steps…")

    running_summary = ""          # short context carried between steps
    transcript: list[str] = []    # full outputs, used only for final synthesis

    with Live(prog.render(), console=ui.console, refresh_per_second=8,
              transient=False) as live:
        plan_raw = _ollama(model, "planner", goal, cwd)
        step_texts = _parse_steps(plan_raw) or \
            [f"Complete the goal for skill '{skill.name}'."]
        prog.steps = [_Step(t) for t in step_texts]
        prog.note = ""
        live.update(prog.render())

        for i, st in enumerate(prog.steps):
            step = st.text
            st.status, st.phase = "running", "executing"
            live.update(prog.render())

            ctx = (f"{goal}\n\nProgress so far:\n{running_summary or '(none)'}"
                   f"\n\nCURRENT STEP: {step}")
            out = _ollama(model, "executor", ctx, cwd)

            st.phase = "reviewing"
            live.update(prog.render())
            review = _ollama(model, "reviewer",
                             f"STEP: {step}\n\nOUTPUT:\n{out}", cwd)
            if not review.strip().upper().startswith("APPROVE"):
                st.phase = "revising"
                live.update(prog.render())
                out = _ollama(model, "executor",
                              f"{ctx}\n\nPREVIOUS ATTEMPT:\n{out}\n\n"
                              f"REVIEWER CORRECTIONS:\n{review}\n\nRedo the step.", cwd)

            st.phase = "summarizing"
            live.update(prog.render())
            summary = _ollama(model, "summarizer", out, cwd) or out[:280]

            st.status, st.phase, st.summary = "done", "", summary
            live.update(prog.render())
            running_summary += f"- Step {i + 1}: {summary}\n"
            transcript.append(f"### Step {i + 1}: {step}\n{out}")

        prog.note = "Synthesizing final result…"
        live.update(prog.render())
        final = _ollama(model, "synthesizer",
                        f"{goal}\n\nSTEP RESULTS:\n" + "\n\n".join(transcript), cwd)
        prog.note = ""
        live.update(prog.render())

    steps = step_texts

    markdown = (
        f"_Multi-step local run · {len(steps)} steps · model {model}_\n\n"
        f"## Plan\n{running_summary}\n"
        f"## Final\n{final or '(no output)'}\n\n"
        f"<details><summary>Step transcript</summary>\n\n"
        + "\n\n".join(transcript) + "\n</details>\n"
    )
    print("\n" + markdown)
    return 0, markdown
