# Project rules

Every agent session reads this file first. Keep it short: every line here costs context in every session.

## Project
- What it is: PySTAC is a Python library for reading and writing SpatioTemporal Asset Catalogs (STAC).
- Language and tools: Python, uv, Sphinx for docs.
- Run the tests: `uv run pytest`

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
