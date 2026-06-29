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
from pathlib import Path

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


def _goal(skill: Skill, context: str) -> str:
    try:
        body = skill.path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        body = ""
    ctx = f"\n\nPrior related context:\n{context}\n" if context.strip() else ""
    return (
        f"GOAL — execute the skill '{skill.name}':\n"
        f"--- SKILL ---\n{body}\n--- END SKILL ---{ctx}"
    )


def run(skill: Skill, model: str, *, cwd: Path, context: str = "") -> tuple[int, str]:
    """Run the full multi-step pipeline. Returns ``(exit_code, markdown)``."""
    goal = _goal(skill, context)

    ui.info("Planning steps…")
    plan_raw = _ollama(model, "planner", goal, cwd)
    steps = _parse_steps(plan_raw) or [f"Complete the goal for skill '{skill.name}'."]
    ui.info(f"{len(steps)} step(s) planned.")

    running_summary = ""          # short context carried between steps
    transcript: list[str] = []    # full outputs, used only for final synthesis

    for i, step in enumerate(steps, 1):
        ui.info(f"Step {i}/{len(steps)}: {step}")
        ctx = f"{goal}\n\nProgress so far:\n{running_summary or '(none)'}\n\nCURRENT STEP: {step}"
        out = _ollama(model, "executor", ctx, cwd)

        review = _ollama(model, "reviewer",
                         f"STEP: {step}\n\nOUTPUT:\n{out}", cwd)
        if not review.strip().upper().startswith("APPROVE"):
            ui.warn(f"Step {i} needs revision; retrying once.")
            out = _ollama(model, "executor",
                          f"{ctx}\n\nPREVIOUS ATTEMPT:\n{out}\n\n"
                          f"REVIEWER CORRECTIONS:\n{review}\n\nRedo the step.", cwd)

        summary = _ollama(model, "summarizer", out, cwd) or out[:280]
        running_summary += f"- Step {i}: {summary}\n"
        transcript.append(f"### Step {i}: {step}\n{out}")

    ui.info("Synthesizing final result…")
    final = _ollama(model, "synthesizer",
                    f"{goal}\n\nSTEP RESULTS:\n" + "\n\n".join(transcript), cwd)

    markdown = (
        f"_Multi-step local run · {len(steps)} steps · model {model}_\n\n"
        f"## Plan\n{running_summary}\n"
        f"## Final\n{final or '(no output)'}\n\n"
        f"<details><summary>Step transcript</summary>\n\n"
        + "\n\n".join(transcript) + "\n</details>\n"
    )
    print(markdown)
    return 0, markdown
