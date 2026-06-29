"""Entry point & command wiring. Single responsibility: orchestration only."""
from __future__ import annotations

import argparse
from pathlib import Path

from . import models, registry, runners, selection, ui
from .discovery import Skill, all_skills, discover


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #
def _enabled_skills(reg: registry.Registry) -> list[Skill]:
    """All enabled skills across home + every registered project."""
    bases = [Path.home()] + [Path(p) for p in reg.projects.values()]
    seen: set[str] = set()
    result: list[Skill] = []
    for base in bases:
        for s in all_skills(discover(base)):
            if s.uid in seen or not reg.is_enabled(s.uid):
                continue
            seen.add(s.uid)
            result.append(s)
    return result


def _choose_engine(reg: registry.Registry, requested: str | None) -> str | None:
    if requested:
        return requested
    avail = [e for e in models.ENGINES if runners.engine_available(e)] or list(models.ENGINES)
    default = reg.last_engine if reg.last_engine in avail else avail[0]
    return selection.pick_one("Run with which engine?", avail, default=default)


def _choose_model(reg: registry.Registry, engine: str, requested: str | None) -> str | None:
    if requested:
        return requested
    avail = models.available_models(engine)
    if not avail:
        ui.warn(f"No models discovered for '{engine}'.")
        return None
    default = reg.last_model.get(engine) or models.default_model(engine)
    return selection.pick_one(f"Pick a model for {engine}:", avail, default=default)


def _execute(reg: registry.Registry, skill: Skill, engine: str | None,
             model: str | None, relative: bool) -> int:
    engine = _choose_engine(reg, engine)
    if not engine:
        return 1
    model = _choose_model(reg, engine, model)
    if not model:
        return 1
    reg.last_engine = engine
    reg.last_model[engine] = model
    registry.save(reg)

    ui.info(f"Running [bold]{skill.name}[/bold] via [cyan]{engine}[/cyan] "
            f"({model}) in [dim]{skill.base if relative else Path.cwd()}[/dim]")
    try:
        return runners.run(skill, engine, model, relative=relative)
    except RuntimeError as exc:
        ui.error(str(exc))
        return 1


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_interactive(reg: registry.Registry, _args) -> int:
    ui.banner()

    # 1. Home directory configs + skill selection.
    ui.spinner("Scanning home directory")
    home_hits = discover(Path.home())
    ui.configs_table("~ (home)", home_hits)
    selection.select_skills(all_skills(home_hits), reg)
    registry.save(reg)

    # 2. Register additional project directories.
    while selection.confirm("Add another directory with AI configs?", default=False):
        d = selection.ask_directory("Directory path:")
        if not d or not d.is_dir():
            ui.warn("Not a directory; skipping.")
            continue
        ui.spinner(f"Scanning {d}")
        hits = discover(d)
        ui.configs_table(str(d), hits)
        if not any(h.skills for h in hits):
            ui.warn("No skills found there.")
            continue
        alias = reg.add_project(d)
        ui.ok(f"Registered as alias '[yellow]{alias}[/yellow]'")
        selection.select_skills(all_skills(hits), reg)
        registry.save(reg)

    # 3. Show aliases.
    ui.projects_table(reg.projects)

    # 4. Optionally run a skill.
    if selection.confirm("Run a skill now?", default=True):
        skills = _enabled_skills(reg)
        if not skills:
            ui.warn("No enabled skills to run.")
            return 0
        labels = [f"{s.name}  ·  {s.provider}  ·  {s.base.name}" for s in skills]
        pick = selection.pick_one("Which skill?", labels)
        if pick is None:
            return 0
        skill = skills[labels.index(pick)]
        relative = selection.confirm(
            "Run from the skill's own project (relative)?", default=True)
        return _execute(reg, skill, None, None, relative)
    return 0


def cmd_list(reg: registry.Registry, _args) -> int:
    ui.banner()
    ui.configs_table("~ (home)", discover(Path.home()))
    ui.projects_table(reg.projects)
    skills = _enabled_skills(reg)
    ui.info(f"{len(skills)} enabled skill(s): "
            + ", ".join(s.name for s in skills) if skills else "No enabled skills.")
    return 0


def cmd_add(reg: registry.Registry, args) -> int:
    d = Path(args.directory).expanduser()
    if not d.is_dir():
        ui.error(f"Not a directory: {d}")
        return 1
    hits = discover(d)
    ui.configs_table(str(d), hits)
    alias = reg.add_project(d)
    registry.save(reg)
    ui.ok(f"Registered '[yellow]{alias}[/yellow]' → {d}")
    return 0


def cmd_run(reg: registry.Registry, args) -> int:
    skills = _enabled_skills(reg)
    matches = [s for s in skills if s.name == args.skill]
    if args.project:
        base = reg.resolve(args.project)
        if base:
            base = base.resolve()
            matches = [s for s in matches if s.base == base]
    if not matches:
        ui.error(f"No enabled skill named '{args.skill}'"
                 + (f" in project '{args.project}'." if args.project else "."))
        return 1
    if len(matches) > 1:
        labels = [f"{s.name} · {s.provider} · {s.base.name}" for s in matches]
        pick = selection.pick_one("Multiple matches; pick one:", labels)
        if pick is None:
            return 1
        skill = matches[labels.index(pick)]
    else:
        skill = matches[0]
    return _execute(reg, skill, args.engine, args.model, args.relative)


# --------------------------------------------------------------------------- #
# Argument parsing
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gskill",
        description="Discover and run AI-assistant skills from anywhere.",
    )
    sub = p.add_subparsers(dest="command")

    sub.add_parser("ls", help="List configs, projects and enabled skills")

    p_add = sub.add_parser("add", help="Register a project directory")
    p_add.add_argument("directory")

    p_run = sub.add_parser("run", help="Run a skill by name")
    p_run.add_argument("skill")
    p_run.add_argument("--project", "-p", help="Restrict to a project alias/path")
    p_run.add_argument("--engine", "-e", choices=models.ENGINES)
    p_run.add_argument("--model", "-m")
    p_run.add_argument("--relative", "-r", action="store_true",
                       help="Run from the skill's own project dir (else cwd/global)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reg = registry.load()
    dispatch = {
        None: cmd_interactive,
        "ls": cmd_list,
        "add": cmd_add,
        "run": cmd_run,
    }
    try:
        return dispatch[args.command](reg, args)
    except KeyboardInterrupt:
        ui.warn("Aborted.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
