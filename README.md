# ⚡ gskill — Global Skill Executor

Discover the AI-assistant skills scattered across your machine (`.claude`,
`.cursor`, `.gemini`, `.windsurf`, …), pick which ones to keep, register extra
project directories, and **run any skill** through Claude, Cursor, or a local
Ollama model — from anywhere.

## Install (global)

```bash
# recommended: isolated global install
pipx install /Users/hosen/Gems/global-skill-executor

# or a plain user install
pip install --user /Users/hosen/Gems/global-skill-executor
```

Now `gskill` is on your PATH everywhere.

## Usage

```bash
gskill                      # interactive: scan → select skills → add dirs → run
gskill ls                   # show configs, project aliases, enabled skills
gskill add ~/work/my-repo   # register a project dir (gets a short alias)
gskill run longread                         # run by name (prompts for engine/model)
gskill run longread -e claude -m claude-opus-4-8
gskill run longread -e local  -m llama3
gskill run longread --relative              # cd into the skill's project first
gskill run longread -p my-repo              # disambiguate by project alias
```

- **Engine** (`-e`): `claude` · `cursor` · `local` (Ollama). If omitted you're
  asked, defaulting to your last choice.
- **Model** (`-m`): if omitted you pick from the engine's catalog
  (Ollama models are discovered live via `ollama list`).
- **`--relative` / `-r`**: run from the skill's own project directory.
  Without it, the skill runs in your current directory (global).

## How it's organized (one job per module)

| Module | Responsibility |
|--------|----------------|
| `providers.py`  | Catalog of known AI configs & where their skills live |
| `discovery.py`  | Scan a directory → `ConfigHit` / `Skill` records |
| `registry.py`   | Persist projects, skill on/off, last engine/model |
| `models.py`     | Per-engine model catalogs (+ live Ollama discovery) |
| `runners.py`    | Build & execute the engine command |
| `selection.py`  | Interactive prompts (questionary) |
| `ui.py`         | Rich rendering (tables, banner, spinners) |
| `cli.py`        | Argument parsing & orchestration only |

State lives in `~/.config/gskill/registry.json`.
