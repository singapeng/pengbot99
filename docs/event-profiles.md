# Event Profiles (schedule config overlays)

## Goal

Replace the current "one branch per event" scheduling strategy with a
single-branch, folder-based system where the default schedule lives in
`config/default/` and each tracked event has its own small profile folder
holding only the differences from default.

This removes the need to switch branches (and manage a full `config/` copy
per event) whenever a new event starts.

## Status

- [x] Step 1: restructure config into `config/default/`, feature-flag
      constants, profile-aware loader (CSV fallback + constants overlay),
      `--profile` startup argument.
- [x] `queen` profile migrated.
- [x] `team_battle` profile migrated.
- [ ] Migrate the remaining event branches (meteor, machine shuffle,
      mini world tour) to profile folders.

## Structure

Under the existing `CONFIG_PATH` directory:

```
config/
  default/                   # baseline schedule, always present
  queen/                     # first event profile: only deltas vs default
    slot2_schedule_weekend.csv
    constants.dat
  team_battle/               # migrated from branch v1.7_team_battle
    slot2_schedule.csv
    slot2_schedule_weekend.csv
    constants.dat
  meteor/                    # event profile: only deltas vs default
    ...
  machine_shuffle/
    ...
```

## Loading rules

- A profile is selected at startup via a CLI argument, e.g.
  `python -m pengbot99.bot --profile meteor`. Defaults to `default`.
- The loader composes `default/` then overlays the event folder:
  - A CSV present in the event folder replaces the whole default file
    (no per-row merge); `schedule.load_schedule` falls back to `default`
    when the file is absent from the profile folder.
  - A CSV absent from the event folder is inherited from default.
  - `constants.dat` is merged per-key: constants present in the event
    folder override default by name; all others are inherited.
- Event folders must not restate data identical to default.

## Feature flags via constants

Currently, optional features are activated by the *presence* of certain
constants, expressed by commenting/uncommenting lines in `constants.dat`
(e.g. `SECRET_LEAGUE_INTERVALS`, `SHUFFLE_MINIPRIX_LINE_UP_OFFSET`).

This is fragile with a merge model: with value-override semantics an event
cannot express "this feature is off in this profile" when default has it on.

We will move to explicit feature-flag constants so every gated feature has
a value in `default`, and an event overrides the value (including "off")
rather than omitting the key:

- Introduce `..._ENABLED=0/1` style flags for gated features.
- Remove the comment/uncomment convention.
- Update `bot.py` to read the flags instead of checking key presence.

Resolution: offset constants for disabled features (e.g.
`SHUFFLE_MINIPRIX_LINE_UP_OFFSET`) stay defined in `default`; the flag is
the only gate, which composes cleanly with the override-merge model.

## Out of scope

The following files are not part of the schedule config and are left as-is:

- `explain.dat` (loaded separately via `EXPLAIN_FILE`)
- `misa.csv`
- `.msg_struct`

## Loader validation

If an event folder contains a CSV whose name does not match any default CSV
name, the loader emits a warning via `utils.log_profile_csv_warnings()`
(the file may be silently ignored by callers, which is a dangerous failure
mode with inherit-from-default).

## Migration of CONFIG_PATH

`CONFIG_PATH` still points at a directory that now contains `default/` and
the event profile folders; no new env var is needed.