# pengbot99 — working notes

## Commits

Do not add a `Co-Authored-By:` trailer to commit messages. No `Generated with`
footers either. This is an upstream repository maintained by someone else; the
commit log stays as it would be without any of this.

## Comments and comment structure

Code should be self-documenting, to the best extent possible. Comments should be
sparse, and not document the obvious. If the code needs comments, you may be
writing code that could be simplified. Sparse is about count, not length: a few
comments that orient a reader, not a remark at every site — and one of them may
run to a paragraph where the reason is real.

If the solution is best left as it is, a short comment that explains it is
welcomed.

**A comment states a present property of the code or the platform, and one this
repo can check.** That is the whole test. Write what a reader of the line cannot
deduce from it: a behaviour that makes the obvious code wrong, the constraint a
shape exists to satisfy, which of two readings of a value is meant.

Never in a comment:

- **Progress, tasks, plans or project decisions.** No task numbers, no "the plan
  asks for this", no "per the decision record". Those live outside this repo and
  describe how the work is organised, not what the code does. A reason worth
  keeping is worth stating on its own; if it cannot be, it is not the code's
  business. The citations live in `CLAUDE.local.md`, which is not committed.
- **The past — of the code, of the data, or of a decision.** No "used to be", no
  "split from", no "rows written before the rename", no "we decided". History
  goes out of date silently: nothing fails, nobody notices, and the next reader
  trusts it. State the present property instead — the fixture *is* an edge case
  the live game never ran.
- **The future.** No "this goes away once the schedule changes", no "the next
  task will want it". Scope is a present fact and may be written down —
  "schedule logic only; the bot is another module" — but a timeline is a
  prediction, and a comment that outlives one lies.
- **Another repo's internals, or an appeal to its docs.** the game's own data
  dumps, another repo's endpoints — nothing here can notice when those stop
  being true. State the contract this module owns instead.
- **First person.** "We" is either the authors, which is decision narration, or
  the code, which has a name.
- **A verdict where a mechanism belongs.** "That library is the wrong shape"
  gives the next reader nothing to act on. Name the thing they would otherwise
  reach for, then the property that rules it out: "Not `Format.RelativeTime`,
  the obvious candidate: it reads the clock itself and memoises on its
  arguments, so the string it returns is frozen at the first call".

Two things that look like violations and are not. **An absence may be
documented** — "no retries, no caching; this is not a queue" — because what a
thing deliberately does not do is a present fact about it. And **a comment may
say where to change something**: "this is the only place that names a group",
"delete this constant to hand the decision back to the caller". That is a
pointer, not a plan.

## Layout

- `py/pengbot99/` — the package. `gameschedule.py` is the game's own schedule
  model, `gameevents.py` turns it into the bot's Event lists, and
  `schedule_controller.py` builds every manager of a profile from its files;
  the rest is the Discord bot. `schedule.py`, `miniprix.py`, `secret_league.py`
  and `choicerace.py` are the earlier fitted model: importable and tested,
  used by nothing else.
- `py/pengbot99/data/` — the game's schedule files dumped to JSON, shipped as
  package data. `CONFIG_PATH` in the `.env` overrides them at runtime with a
  directory of the same shape. `event_default/` is the complete set of
  schedule files; every other `event_<name>/` folder is a profile holding only
  what differs, picked with `--profile` or `ScheduleProfile(env, name)`.
  `StageList.json` and `server_events.csv` sit at the root and belong to no
  profile.
- `tests/fixtures/` — test data for the fitted model, not shippable content.
  Several fixtures encode edge cases that never ran in the live game. They
  stay out of the package.

## Facts not to re-derive

- **The Discord client library is an optional dependency** (`pengbot99[bot]`).
  `gameschedule`, `gameevents`, `schedule_controller`, `events`, `schedule`
  and `miniprix` must import without it — `tests/test_import_boundary.py`
  enforces that in a subprocess.
- **`schedule_controller.ScheduleProfile` is the only assembly path.** It
  builds every manager of a profile from the profile's files, and
  `ScheduleController` registers profiles and delegates reads to the active
  one; `bot.py` builds the controller and holds no wiring of its own. A
  second path that reassembles the managers from `gameevents` is the failure
  this shape exists to prevent. `gameschedule.py` reads no `.env`, no clock
  and logs nothing; `ScheduleProfile` reads no `.env` either — it is handed a
  parsed env, and an empty one reads the packaged data.
- **Without a `CONFIG_PATH` every file comes from the package**, resolved
  through `importlib.resources`, so `utils.get_schedule_dir` may return
  something that is not a path: read it through `utils.open_data_file` and
  `utils.has_data_file`, never `os.path`.
- **The repository is not ruff-clean.** `ruff check .` reports pre-existing
  findings across `tests/` and parts of the bot. Do not fix them as a side
  effect of unrelated work; check the files you touched instead.
- **The tests are the contract** and pass unmodified. If a change requires
  editing `tests/test_gameschedule.py`, `tests/test_gameevents.py`,
  `tests/test_schedule.py` or `tests/test_miniprix.py`, that is a signal
  about the change, not about the tests.
