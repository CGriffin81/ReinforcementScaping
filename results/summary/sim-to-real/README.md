# sim-to-real

The calibration gate's cases (env contract §7: XP/hr, gp/hr and duration within ±20%), each case's latest server runs against sim-v1.2, re-simulated by `scripts/sim_to_real.py` (Caleb, 2026-11-12, `m002-sim-to-real`). `scripts/figures.py` makes the report's tables from these files.

| | |
|---|---|
| Command | `uv run python scripts/sim_to_real.py` |
| Git SHA | `a98530127401648fdd74a86279cb91741c397eec` |
| Sim | `sim-v1.2` (the commit descends from it: True) |
| Made | 2026-11-12T11:42:39-06:00 |
| Sources | 69 files of `results/calibration/` (their SHA-256 in `config.json`) |

## Per family (gated metrics; sim over server)

| family | cases | XP/hr | output/hr | duration | within_gate | outside | speed_check | measured |
|---|---|---|---|---|---|---|---|---|
| Gathering (woodcutting, mining, fishing) | 42 | 0.84 to 1.11 | 0.66 to 1.11 | 0.89 to 1.19 | 125 of 126 | fish_shrimp, band 1 (items_per_hour 0.66) | 3 of 3 | 2026-10-31 to 2026-11-06 |
| Barbarian fishing | 3 | 1.00 to 1.03 | 1.00 to 1.03 |  | 12 of 12 |  | 1 of 1 | 2026-11-08 to 2026-11-08 |
| Processing (smelting, smithing, cooking, firemaking, burying) | 34 | 0.90 to 1.15 |  | 0.92 to 1.15 | 102 of 102 |  |  | 2026-11-07 to 2026-11-07 |
| Crafting | 14 | 1.00 | 0.91 to 1.00 | 1.00 to 1.10 | 53 of 53 |  | 14 of 14 | 2026-11-09 to 2026-11-09 |
| Herblore | 9 | 1.00 | 1.00 | 1.00 | 33 of 33 |  | 9 of 9 | 2026-11-09 to 2026-11-09 |
| Thieving (pickpocketing) | 8 | 0.91 to 1.14 | 0.75 to 1.14 |  | 15 of 16 | pickpocket_heroes, band 81 (gp_per_hour 0.75) |  | 2026-11-06 to 2026-11-07 |
| Agility (courses) | 7 | 0.80 to 1.02 |  |  | 6 of 7 | barbarian course laps, band 15 (xp_per_hour 0.80) | 3 of 3 | 2026-11-08 to 2026-11-08 |
| Runecrafting (at the ruins) | 9 |  |  | 0.84 to 1.02 | 17 of 17 |  | 17 of 17 | 2026-11-09 to 2026-11-09 |
| Runecrafting (through the Abyss) | 30 |  | 0.99 to 1.23 | 0.91 to 1.06 | 39 of 40 | hitpoints lost in the outer ring (Defence 20) (hp_lost 1.23) | 1 of 1 | 2026-11-08 to 2026-11-09 |
| Combat (melee, ranged, magic) | 31 | 0.87 to 1.31 | 0.87 to 1.61 | 0.85 to 1.48 | 84 of 93 | magic Black Knight (valuable loot), band 1 (kills_per_hour 1.52); magic Poison spider (none loot), band 31 (kills_per_hour 1.61); magic Poison spider (none loot), band 31 (xp_per_hour 1.31); melee Abyssal leech (none loot), band 61 (ticks 1.48); melee Abyssal walker (none loot), band 91 (ticks 1.23); melee Experiment (none loot), band 91 (kills_per_hour 1.20); melee Experiment (none loot), band 91 (xp_per_hour 1.20); ranged Abyssal demon (valuable loot), band 91 (kills_per_hour 1.29); ranged Abyssal demon (valuable loot), band 91 (xp_per_hour 1.29) | 4 of 4 | 2026-11-08 to 2026-11-09 |
| Travel | 49 |  |  | 0.42 to 1.21 | 47 of 49 | Varrock east bank to Al Kharid, paying the toll (check set) (ticks 0.42); out of the Abyss from its north (abyss set) (ticks 1.21) | 20 of 20 | 2026-11-01 to 2026-11-09 |

## Combat's drop tables (OQ-20 (a))

| family | monsters | kills | items_fit | not_fitting | sim_never_gp_per_kill_max |
|---|---|---|---|---|---|
| Combat's drop tables | 9 | 1305 | 371 of 374 | Black Knight: Bones; Chaos druid: Bones; Moss giant: Big bones | 0.0 |

## How the cases were chosen

- **The server's side** is each case's last measurement among the files its family lists (`FAMILIES` in
  `scripts/sim_to_real.py`), from the git-ignored `results/calibration/`, at 50 ms ticks. The server's code was frozen
  at upstream from Oct 31; the fork's own rule changes went on to Nov 9 (CLAUDE.md lists them). Where the decision
  log found one touched a family's measurements, it re-measured them (combat's sets after the region fix,
  2026-11-08), and the runs here are those re-measurements.
- **The sim's side** is each runner's own sim function, called on sim-v1.2 from the same start, with 200 seeds
  (one run where the sim is deterministic: Herblore, the timed families). The server's rates are each runner's own.
- **Gathering** from 14:40 on Oct 31, when the ambient bots went off. **Processing:** the run after its four fixes,
  firemaking's step-off run and iron's 8-run file. **Combat:** the fit sets (the ranker's top by XP, no looting) and
  check sets (its top by gp, valuable loot) for melee, ranged and magic as the decision log's last re-checks have
  them, OQ-35's poison spiders and the Abyss's fights; its gp/hr is gated by its parts (OQ-20 (a): the drop tables,
  and kills/hr). **Travel:** the fit, check, shortcut and Abyss sets, one run a trip. **The Abyss:** the outer ring per
  obstacle, the teleport and the rifts (the `--pass` and `--rifts` runs), the hitpoints from the runs that set their
  Defence (a fit at 40, a check at 20), and each rune's whole crossing.
- **Left out:** the 600 ms reruns (the speed check's own table), earlier re-simulations, runs the decision log
  superseded, chaos's crossings (`abyss_rc_chaos` isn't an option), and measurements that fitted the sim's inputs
  rather than test an option: Agility's course entries and spike pit, the shortcuts' own crossings, the travel
  constants, the essence pouches and the Abyss's failed tries.
- **Fitted and checked:** the calibration measured each family's overheads on the server and fitted the sim to them,
  so many cases agree partly by construction. Combat's fit and check sets, and travel's fit and check sets, keep the
  two apart; elsewhere the cases are the ones the overheads were fitted on, at several bands.

## Files

- `cases.csv`: one row per case and metric, gated or not, with the server runs' file and date, sim over server as calibrated then, and a note;
- `drops.csv`: per monster probed, the items whose server count falls in the sim's central 99%;
- `speed_check.csv`: each speed-check case at 50 and 600 ms ticks, both on the server (OQ-21);
- `config.json`: the provenance and each source file's SHA-256.
