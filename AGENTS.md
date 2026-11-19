# Project rules

Every agent session reads this file first. Keep it short: every line here costs context in every session.

## Project
- What it is: Python library for working with the SpatioTemporal Asset Catalog (STAC) specification, as a uv workspace of a core package plus per-extension packages.
- Language and tools: Python 3.10+, uv workspace, pytest, ruff, mypy
- Run the tests: `uv run pytest tests` (core); for a single extension use `uv run pytest extensions/<name>/tests`

## Workflow
This project uses four steps. Each step runs in its own new session.
1. `/grill` writes `SPEC.md`.
2. `/slice` writes `PLAN.md`.
3. `/build-slice <N>` builds one slice and commits it.
4. `/verify <N>` checks it and ticks the box in `PLAN.md`.

`SPEC.md` and `PLAN.md` describe the current change and are the memory of this project; git keeps earlier ones. For a new change, run `/grill` again. Conversations are disposable.

## Rules
- Never commit API keys, passwords or `.env` files.
- One slice per session. Commit after each slice.
- A change of direction goes into `SPEC.md` first, committed as `spec: <what changed>`.
- Do not add a dependency without saying why.
- <add your own conventions here>
