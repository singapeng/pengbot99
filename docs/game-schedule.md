# Game schedule (the game's own model)

## Goal

Compute every schedule the bot reports the way F-Zero 99 computes it, from the
game's own schedule files, so that no rotation offset ever needs to be fitted
again: Grand Prix leagues, Secret League, Mini-Prix and Classic Mini-Prix track
selections (public and private), 99-race track pairs with Mystery tracks, and
the Team Battle, Pro-Tracks and Classic track pairs.

## Status

- [x] `gameschedule.py`: the game's algorithm, a function of the Unix clock
      and two data files.
- [x] `gameevents.py`: Event lists for the bot, in its own vocabulary.
- [x] Profiles rebuilt from the game's files; the fitted CSV rotations and
      offset constants are gone from `config/`.
- [x] `/lineup` command for Team Battle, Pro-Tracks and Classic track pairs.
- [x] Minute-by-minute cross-check against the fitted model for every
      profile (see "Validation").

## How the game schedules

The game reads two files and evaluates everything locally against the
NTP-synced clock. There is no server query, no stored state and no history.

- `GameScheduleV1`: the list of game modes (leagues, rotation order, rotation
  interval, mirror patterns), the weekday interval table (which set runs for
  how many minutes), the track-pair tables (`TrackSchedule` for 99 races and
  Team Battle, `HardTrackSchedule` for Pro-Tracks, `ClassicTrackSchedule` for
  Classic), the Mystery track windows (`MysteryTrackSchedule`) and the Secret
  League windows (`MysteryPrixSchedule`).
- `WeekendSchedule`: the weekend interval table, which days are "weekend",
  and optionally a list of weekend events (`WeekendSchedules`, each with its
  own interval table, modes and Secret League windows) with a calendar
  (`Schedule`) of when each one is in force.

The slot in force at a time is read off the interval table at
`(minutes since epoch) mod (cycle length)`. The position of a mode in its
rotation is **the number of minutes that mode has been active since the Unix
epoch, assuming the current tables had always been in force**, with weeks
counted from Sunday. Every rotation derives from that counter:

| what | formula |
|---|---|
| Grand Prix league | `RotationOrder[(counter / RotationInterval) mod len]` |
| Mini-Prix selection | `Leagues[counter mod 43]`, mirror pattern `[counter mod 9]` |
| Classic Mini-Prix | `Leagues[counter mod 29]` |
| Team Battle / Pro-Tracks / Classic pair | `Sets[(counter + Offset) mod n]` (Team Battle has `Offset 6`) |
| Secret League | the Grand Prix counter falls in a `MysteryPrixSchedule` window |
| 99 races | `TrackSchedule.Sets[(minutes since epoch) mod 34]`, plain wall clock |
| Mystery track | `(minutes since epoch) mod 205` in one of six 2-minute windows |
| private lobby | wall clock on the same tables, unless the public schedule runs the mode, in which case the public lineup |

Because the counter assumes the current tables, every drop with different
durations shifts every rotation at once. That is the "new offset per event"
the fitted model needed; the game needs none, and neither does the bot now.

## Data files

Each profile folder under `CONFIG_PATH` holds the JSON dump of the two BYML
files, and optionally `constants.dat`:

```
config/
  StageList.json                  # the leagues' track lists (MiniPrix001 ...)
  event_default/
    GameScheduleV1.json           # romfs default: 10/20-minute cycle
    WeekendSchedule.json          # romfs default, with the weekend-event calendar
    constants.dat                 # WEEKEND_SCHEDULE_ID=auto
  event_meteor/
    GameScheduleV1.json           # the BCAT drop of the event: 5/15-minute cycle
    WeekendSchedule.json
  event_queen/
    constants.dat                 # WEEKEND_SCHEDULE_ID=QueenLeagueWeekend
```

A profile without a file inherits it from `event_default`. The weekend event a
profile runs is set by `WEEKEND_SCHEDULE_ID`:

- `auto` (the default): follow the calendar of the `WeekendSchedule` file, as
  the game does. The romfs calendar lists every weekend event of 2026.
- a `WeekendScheduleID` (`KnightLeagueWeekend`, `Teams`, `MachineShuffle`,
  `WorldTourWeek`, ...): run that event on every weekend, whatever the date.
- `none`: ignore the calendar.

To add a weekend event the calendar lacks, either add a row to `Schedule` in
`WeekendSchedule.json` or pin the event in a profile and switch to it on the
date through `EVENT_SCHEDULE_FILE`. To add a new drop, dump its two files into
a new profile folder.

## Modules

- `gameschedule.py`: the model. `Schedule` is one `GameScheduleV1` with one
  weekend table in force; `ScheduleData` holds the files and picks the
  `Schedule` in force at a time from the calendar. Pure: no clock, no
  environment, no logging.
- `gameevents.py`: managers that turn the model into `events.Event` lists:
  `SlotScheduleManager` (Grand Prix, Mini-Prix and special event slots, with
  Secret League replacements), `MysteryTrackManager`, `NinetyNineManager`,
  `MiniPrixLineupManager` (public or private) and `TrackPairManager`
  (Team Battle, Pro-Tracks, Classic; public or private).
- `schedule_controller.py`: builds the managers of a profile from its files.

The legacy fitted model (`schedule.py`, `miniprix.py`, `secret_league.py`,
`choicerace.py`) stays importable and tested; the bot no longer uses it.

## Validation

The model was compared minute by minute with the fitted CSV model for every
profile over the week each event last ran, using the fitted offsets as the
reference. Agreement:

| profile | mode and league | Secret League | Mini-Prix selection and mirror | Classic Mini-Prix | private Mini-Prix | 99 pairs |
|---|---|---|---|---|---|---|
| default (Oct 13-19) | 100% | 100% | 100% | 100% | 100% | 100% |
| meteor (Oct 19-26) | 100% | none in both | 100% | 100% | 100% | 100% |
| queen (Sep 16-22) | 100% | 100% | 100% | 100% | 100% | 100% |
| knight (Jul 22-28) | 100% | 100% | | | | |
| mini_world_tour (Sep 28-Oct 5) | 100% | 100% | 100% | 100% | 100% | 100% |
| festival_world_tour (Dec 15-21) | 100% | none in both | 100% | 100% | 100% | |
| team_battle (Sep 9-15) | see below | 100% | 100% | 100% | 100% | 100% |
| machine_shuffle (Oct 7-13) | 100% | 100% | weekdays 100%, weekend see below | 100% | 100% | 100% |

Three disagreements with the fitted model remain, all on data the game's files
state plainly:

- **Team Battle weekend specials.** The game's `Teams` event runs Team Battle
  in every special slot. The fitted model rotated Team Battle, Pro-Tracks and
  Classic in the :10 slot.
- **Machine Shuffle weekend Mini-Prix.** The game's `MachineShuffle` event
  schedules plain `MiniPrixRotation` slots, so the selection continues the
  weekday counter. The fitted model used a separate offset for the weekend
  that lands five selections later, while its mirror pattern agreed with the
  counter. One observed weekend selection settles it.
- **Secret League Weekend.** The game's `MysteryLeagueWeekend` replaces every
  other Grand Prix on the weekend (each league runs twice, the first as Secret
  League). The fitted model reused the weekday intervals there.
