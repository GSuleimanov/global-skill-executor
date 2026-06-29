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
gskill                      # fuzzy-pick a skill (grouped by project) → provider → model
gskill setup                # onboard: scan home, select skills, add dirs
gskill scan [dir]           # find git repos with AI configs and register them
gskill ls                   # show configs, project aliases, enabled skills
gskill add ~/work/my-repo   # register a project dir (gets a short alias)
gskill run longread                         # run by name (prompts for engine/model)
gskill run longread -e claude -m claude-opus-4-8
gskill run longread -e local  -m llama3
gskill run longread --relative              # cd into the skill's project first
gskill run longread -p my-repo              # disambiguate by project alias
gskill run longread -c "write about Rust async, ~800 words"   # extra context
```

### The default picker (`gskill`)

1. **Pick a skill** — all enabled skills, grouped by project (group headers in a
   distinct color). Just start typing to filter the list; ↑↓ to move, enter to select.
2. **Pick a provider** — Claude Code · Cursor Agent · Local model (Ollama/other).
3. **Pick a model** — for local models the full `ollama list` is shown and is
   type-to-filter too; for Claude/Cursor you pick from the catalog.
4. **Relative or global** — run from the skill's own project, or your current dir.

- **Engine** (`-e`): `claude` · `cursor` · `local` (Ollama). If omitted you're
  asked, defaulting to your last choice.
- **Model** (`-m`): if omitted you pick from the engine's catalog
  (Ollama models are discovered live via `ollama list`).
- **Context** (`-c`): ad-hoc input/instructions for this run, injected as an
  "Additional context" section in the prompt. The interactive picker also asks
  for it (enter to skip).
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

## Run summaries (auto-context)

Every run is captured to `~/.config/gskill/history/` as
`YYYY-MM-DD-<skill-slug>.md`. On the next run gskill finds **prior related
summaries** (same skill title, or ≥2 overlapping words in the brief) and feeds
them to the model as context. Summaries **older than 3 days are pruned** on
every `gskill` invocation.

The format is fixed so other AI calls can navigate it cheaply:

```markdown
# <skill-title>
date: YYYY-MM-DD | engine: <e> | model: <m> | project: <p> | relative: <bool>
brief: <one-line description — matched against future runs>

## Result
<captured output>
```

- **Line 1** = title, **line 3** = `brief:` description (the match keys).
- Files are `YYYY-MM-DD-N-<slug>.md` where **N** is the run number that day
  (across all skills) — every run is kept, nothing is overwritten.

## Local models: multi-step quality pipeline

Local (Ollama) runs don't do a single shot — a weak model gets the best chance
via decomposition ([`local_workflow.py`](gskill/local_workflow.py)):

1. **Plan** — a planner call breaks the task into 3-6 atomic steps.
2. **Execute** — each step runs as a *separate* role-scoped call with a tiny
   context: only the goal + a short running summary of prior steps.
3. **Review** — every step output is checked; one corrective retry on failure.
4. **Compress** — each result is summarized to ~2 sentences before being passed
   forward, so context never bloats.
5. **Synthesize** — the final deliverable is assembled from the full transcript.

Claude/Cursor runs remain single-shot (they don't need the scaffolding).
