"""Find git repos under a root and discover AI configs inside them.

Single responsibility: locate repo roots cheaply, then defer to discovery.
Strategy: walk top-down, stop descending at each repo boundary, and prune
heavy/hidden directories so we never traverse caches or dependency trees.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from .discovery import ConfigHit, discover

# Directories we never descend into (heavy or irrelevant to config discovery).
_PRUNE = {
    "node_modules", "Library", "venv", ".venv", "__pycache__", "dist",
    "build", ".cache", "vendor", "target", ".tox", "site-packages",
    "Applications", ".Trash", "Pictures", "Movies", "Music",
}


def find_repos(root: Path, max_depth: int = 6) -> Iterator[Path]:
    """Yield git-repo roots under ``root`` without descending into them."""
    root = root.expanduser().resolve()
    base_depth = len(root.parts)
    for dirpath, dirnames, _ in os.walk(root, topdown=True):
        here = Path(dirpath)
        if ".git" in dirnames or (here / ".git").exists():
            yield here
            dirnames[:] = []          # don't recurse into a repo
            continue
        if len(here.parts) - base_depth >= max_depth:
            dirnames[:] = []          # depth cap
            continue
        # prune heavy dirs and hidden dirs (configs are checked by name later)
        dirnames[:] = [
            d for d in dirnames
            if d not in _PRUNE and not d.startswith(".")
        ]


def scan(root: Path, max_depth: int = 6) -> list[tuple[Path, list[ConfigHit]]]:
    """Return (repo_root, config_hits) for repos that hold AI configs."""
    results: list[tuple[Path, list[ConfigHit]]] = []
    for repo in find_repos(root, max_depth):
        hits = [h for h in discover(repo) if h.skills]
        if hits:
            results.append((repo, hits))
    return results
