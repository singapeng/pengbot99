# pengbot99 — working notes

## Commits

Do not add a `Co-Authored-By:` trailer to commit messages. No `Generated with`
footers either. This is an upstream repository maintained by someone else; the
commit log stays as it would be without any of this.

## Layout

- `py/pengbot99/` — the package. `schedule.py`, `miniprix.py` and `events.py`
  are the schedule logic, and `managers.py` assembles them; the rest is the
  Discord bot.
- `py/pengbot99/data/` — dumps of game content, shipped as package data.
  `CONFIG_PATH` in the `.env` overrides them at runtime.
- `tests/fixtures/` — test data, not shippable content. Several fixtures encode
  edge cases that never ran in the live game. They stay out of the package.

## Project, plans and tasks

Lives under `~/projects/fzd/`.

## Facts not to re-derive

- **The Discord client library is an optional dependency** (`pengbot99[bot]`).
  `schedule`, `miniprix`, `events` and `managers` must import without it —
  `tests/test_import_boundary.py` enforces that in a subprocess.
- **`managers.build_managers` is the only assembly path.** `Pengbot.__init__`
  calls it and logs what comes back; it holds no wiring of its own. A second
  path that reassembles the managers from `load_schedule` and the constants is
  the failure this was extracted to prevent. Nothing in `managers.py` may read
  a `.env`, read the clock or log — note that `choicerace.init_99_manager`
  reads a `.env` when handed no `env`, so it is always handed one.
- **The repository is not ruff-clean.** `ruff check .` reports pre-existing
  findings across `tests/` and parts of the bot. Do not fix them as a side
  effect of unrelated work; check the files you touched instead.
- **The tests are the contract** and pass unmodified. If a change requires
  editing `tests/test_schedule.py` or `tests/test_miniprix.py`, that is a
  signal about the change, not about the tests.
