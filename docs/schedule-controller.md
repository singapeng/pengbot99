# Schedule controller (runtime schedule profile management)

## Goal

Streamline switching between schedule profiles **without restarting the bot**.

The experimental implementation on `experimental_flip` proved timers can flip
between the normal and Meteor/Mini World Tour schedules, but it hardcodes one
toggle, two schedules, and the trigger logic. We want a flexible, reusable model
instead:

- preload as many schedule profiles as we wish,
- unload schedules we no longer need,
- make as many switch operations as we want, in any order,
- trigger switches through **any** means (bot command, timer task, future API
  call), not just timers.

For now the trigger is deliberately out of scope: this document defines the
object model that any trigger will drive.

## Background

### Current architecture

`Pengbot` (in `py/pengbot99/bot.py`) is a god-object holder of every schedule
manager, built once from the `--profile` startup flag:

- **slot-1 world** (99 races): `slot1mgr`, `r99_mgr`.
- **slot-2 world** (Grand Prix / special events): `slot2mgr`, `cmp_mgr`,
  `mp_mgr` (public), `pmp_mgr`, `pcmp_mgr` (private), and per-profile shuffle
  managers `smp_mgr`, `psmp_mgr`.

`bot.py` consumers read managers dynamically via the module-global `pb`
(`pb.slot2mgr`, `pb.mp_mgr`, ...), so most code already resolves managers at
call time. One exception: `Explainer` captures `pb.slot2mgr` at startup, so it
would keep serving a stale schedule after a switch.

### What actually varies per profile

Looking at the `config/event_<name>` folders:

- **slot-1/99-race data never varies** between profiles: `slot1_schedule.csv`
  and `ninetynine_schedule.csv` exist only in `event_default` and every profile
  inherits the identical files. `r99_mgr` also holds mutable query state
  (`ChoiceRaceManager.first_event_start`) used for glitch-cycle correction;
  swapping it would reset that cache.
- **slot-2 data and constants vary per profile**: `slot2_schedule*.csv` and the
  constants overlay (offsets, `SHUFFLE_ENABLED`, `SECRET_LEAGUE_ENABLED`, ...).

`experimental_flip` already shifted exactly the slot-2 set (and kept slot-1
fixed), which matches this reality.

### What `experimental_flip` got wrong (that we are avoiding)

- One hardcoded toggle (`flip_mwt`) swapping a single fixed pair of manager
  sets; no way to stack more schedules.
- The flip dates/times embedded in a Discord task, coupling schedule state to a
  concrete trigger.
- Manual `_off_*`/active attribute juggling in the `Pengbot` object.

## Proposed model

The model lives in its own module (e.g. `py/pengbot99/schedule_controller.py`),
**independent from the Discord bot**: no `discord`/`bot.py` imports, fully
unit-testable. `bot.py` gets thinner, keeping only wiring.

### `ScheduleProfile` — one loaded schedule profile

Owns the **slot 2 schedule** for one event profile, built as a coherent set so
internal bindings stay consistent (miniprix managers bind to their own
`slot2mgr`):

```
ScheduleProfile
  name                       # e.g. 'meteor', 'queen'
  slot2mgr, cmp_mgr, mp_mgr,
  pmp_mgr, pcmp_mgr,         # private managers bind to this schedule's publics
  smp_mgr, psmp_mgr          # present per SHUFFLE_ENABLED
  is_shuffle_on()
```

Built from the profile folder via existing loading (`utils.load_config(profile=name)`,
`schedule.load_schedule`, with fallback to `event_default`). Construction logic
is **moved out of `bot.py`** and reused here so every schedule is built the same
way.

### `ScheduleController` — the registry + active schedule

Owns the shared **slot 1 schedule** and a registry of loaded `ScheduleProfile`s;
exactly one schedule is active at any time:

```
ScheduleController
  slot1mgr, r99_mgr          # global, built once, never swapped
  load(name)                 # build + register a ScheduleProfile
  unload(name)               # free a schedule (semantics: TBD, see below)
  switch(name)               # lazy-load if needed, then activate
  name / active              # currently active schedule
  list()                     # loaded schedules
  __getattr__ / descriptor   # delegate unknown attrs to the active ScheduleProfile
```

The delegation is what lets every existing `<mgr>` read keep working: reads
resolve against whatever schedule is active at the moment of the call.

### Lifecycle semantics

- **Startup**: the `--profile` schedule is loaded and made active (unchanged
  behaviour). Optional extra profiles may be preloaded eagerly.
- **`switch(name)`**: activates an already-loaded schedule, or lazy-loads it on
  demand (decided). Atomic at the read level (single assignment); concurrent
  readers see either the old or the new schedule, never a partial swap.
- **`load(name)`**: build and register a schedule without activating it, for
  preloading ahead of a switch.
- **`unload(name)`**: open question.
  - Whether unloading the **active** schedule is allowed (auto-switch to a
    fallback first?) is undecided and will be revisited during bot integration.
  - While uncertain, simplest option: forbid unloading the active schedule.

## Integration with `bot.py` (when implemented)

- `pb = ScheduleController(...)` replaces `Pengbot(...)`. All `pb.<mgr>` reads
  keep working via delegation, and now reflect the active schedule at read time.
- `Explainer` must be changed to read the active `slot2mgr` lazily (hold the
  controller, not a snapshot).
- The trigger layer (slash command, timer) calls `controller.switch(name)`, then
  refreshes the posted Discord schedule/miniprix messages as needed. That
  refresh is trigger responsibility, not the controller's.
- Move the schedule-construction logic out of `bot.py` into the new module; keep
  `bot.py` to wiring only.

## Design decisions & open items

| Item | Status |
| --- | --- |
| One `ScheduleProfile` = the slot-2 world only | Decided (slot-1 stays global; avoids resetting `r99_mgr` state) |
| `switch()` lazy-loads unloaded profiles | Decided |
| Model independent from the Discord bot, own module | Decided |
| Construction logic moved out of `bot.py` | Decided |
| `Explainer` reads active manager lazily | Required integration change |
| `unload()` semantics / unloading the active schedule | Open, revisit at integration |
| Naming of the module/classes | `schedule_controller.py`, `ScheduleController` |

## Future directions

- **API access to multiple schedules**: a future API may let users access any
  loaded schedule profile, not only the active one. The registry keeps all loaded
  schedules around, so exposing read access to non-active schedules is a natural
  extension; the model should not assume only one schedule ever needs to be
  consulted.
- Slot-1 scheduling may someday vary per event; if that happens, the shared
  global scope can be revisited (a `ScheduleProfile` would then own
  `slot1mgr`/`r99_mgr` too).
- Trigger examples to design when scope widens: `switch` slash command with
  autocomplete over loaded schedules, and a config-driven timer task.