# Agent Interaction

## Metadata

- Interaction ID: m001-server-fork-and-control-bridge
- Timestamp CST: 2026-10-05 ~21:54:00 CST (estimated: the previous commit `38a25f1` was at 21:53:14, and this prompt's first fetch finished at 21:56)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS
- Commit: fork `2d22dda` and `1591c87` (branch `rl`); main repo: the commit that adds this record

## Full Prompt

> Make the modifications in a separate fork.

Context: this answers the question at the end of the previous turn: "should our
server changes live as patch files in this repo (my recommendation, so
everything you review is in one place) or in a separate fork of the server?"
It is also the go-ahead for the week-1 server work proposed there: making the
tick speed configurable, a minimal bridge, GE price logging, and the Python
project skeleton.

## Response Summary

### Fork

- Upstream is on GitLab, so GitHub can't fork it directly. Instead I created
  `CGriffin81/2009scape-rl` (private) and pushed the **full** upstream history to
  it: un-shallowed the clone (3,028 commits, 102 MB), renamed the GitLab remote
  to `upstream`, and set `origin` to the fork.
- The first push failed with GitHub `GH008`: the history references 12 LFS
  objects GitHub didn't have, and GitHub rejects pushes with missing LFS
  objects. I checked the GitHub Free LFS quota (10 GiB storage and bandwidth),
  then ran `git lfs fetch --all upstream` and `git lfs push --all origin`
  (43 objects, 367 MB). After that `master` pushed.
- Branch `rl` holds our work, and `master` stays equal to upstream `bea45a9e`.
  Linked into the main repo as the `server/` submodule on branch `rl`.

### Server changes (fork, branch `rl`)

1. `2d22dda`: the tick length is configurable. `ServerConstants.TICK_MS`
   (default 600) is read from `server.tick_ms`, and `MajorUpdateWorker` sleeps
   for it instead of the literal 600. Also adds the `[rl]` config section
   (`bridge_enabled = false`, `bridge_port = 43610`).
2. `1591c87`: the control bridge, in `content/rl/RLBridge.kt` and
   `RLCommands.kt`.
   - A loopback-only TCP socket takes newline-delimited JSON. The socket thread
     only queues requests; a `TickListener` executes them on the game thread.
   - Commands: `ping`, `set_tick_ms`, `spawn`, `state`, `walk_to`, `interact`,
     `run_script`, `stop_script`, `wait`, `despawn`. Only characters the bridge
     spawned can be controlled.
   - Also `worldprops/rl.conf` (the bridge enabled) and a `.gitignore`
     exception so that file is tracked.

### Python (main repo)

- A `uv` project pinned to 3.12 (`pyproject.toml`, `.python-version`,
  `uv.lock`), with the `rlscape` package.
- `rlscape/bridge/client.py`: `BridgeClient`.
- `scripts/gate_check.py`: runs the G1 and G2 checks and writes JSON to
  `results/gates/`.
- `tests/test_bridge_live.py`: 4 integration tests that skip when no server is
  running.

### Bug found and fixed during validation

The first gate run collected 10 logs but only 175 Woodcutting XP.
`Skills.addExperience` clamps every skill at 175 XP until `tutorial:complete`
is set. `spawn` now mirrors the real tutorial exit in
`TutorialMagicTutorDialogue` "leave:yes": the `/save:tutorial:complete` flag,
varbit 3756 = 0, varp 281 = 1000, the starter kit and bank, and the landing
tile 3233,3230. After the fix: 10 logs, 250 XP. I added `xp_per_log` to the
gate output and a regression test, so this can't silently come back.

### Other findings

All recorded in `docs/decision-log.md`:
- the database isn't needed with the current config
- the world stops pulsing when the connectivity check fails, i.e. offline
- `AIPlayer.finalizeDeath` calls `fullRestore()`, which matters for combat
  fidelity later
- the bundled bot pulse caps bot actions at 75 per tick
- the game port binds to all interfaces (noted earlier)

## Documentation Changes

- `ROADMAP.md`: the fork, G1 and G2 marked PASS with measurements, the
  throughput section updated with measured speedup, and the Python track split
  into done and pending.
- `docs/decision-log.md`: the fork decision (overriding the patch-set
  recommendation), G1 and G2 results, the XP-cap bug, and the other findings
  above.
- `CLAUDE.md`: the environment section rewritten for the submodule, fork
  workflow, run and test commands, and the optional database.
- This record.

## Code Changes

Fork `CGriffin81/2009scape-rl`, branch `rl`:
- `Server/src/main/core/ServerConstants.kt`: `TICK_MS`, `RL_BRIDGE_ENABLED`,
  `RL_BRIDGE_PORT`.
- `Server/src/main/core/game/system/config/ServerConfigParser.kt`: parses
  `server.tick_ms`, `rl.bridge_enabled`, `rl.bridge_port`.
- `Server/src/main/core/worker/MajorUpdateWorker.kt`: the tick sleep uses
  `TICK_MS`.
- `Server/worldprops/default.conf`: `tick_ms` and the `[rl]` section.
- `Server/worldprops/rl.conf` (new), plus a `.gitignore` exception for it.
- `Server/src/main/content/rl/RLBridge.kt` and `RLCommands.kt` (new).

Main repo:
- `pyproject.toml`, `.python-version`, `uv.lock` (new).
- `rlscape/__init__.py`, `rlscape/bridge/__init__.py`,
  `rlscape/bridge/client.py` (new).
- `scripts/gate_check.py` (new).
- `tests/test_bridge_live.py` (new).
- `.gitignore`: stops ignoring `server/`.
- `.gitmodules` + the `server` submodule at `1591c87`.

## Infrastructure Changes

- Created the GitHub repo `CGriffin81/2009scape-rl` (private) and pushed
  `master` (full upstream history) and `rl`.
- Uploaded 367 MB to GitHub LFS for the fork.
- Server clone remotes: `upstream` = GitLab, `origin` = the fork.
- Installed a uv-managed CPython 3.12.14 and created `.venv`.
- Ran the server several times locally (stopped after each run). The second
  launch onward starts in about 8 s.

## Decisions

- **User decision:** server modifications live in a separate fork. This
  overrides the agent's recommendation of a patch set in the main repo.
- **Agent decision (reversible):**
  - fork name `2009scape-rl`, private
  - `master` mirrors upstream; work goes on `rl`
  - linked into the main repo as a submodule, so each main-repo commit pins the
    exact server version
  - pushed the full LFS history rather than squashing upstream history, to keep
    provenance and allow upstream merges
- **Agent decision:** the bridge's `spawn` replicates the tutorial-exit code
  path rather than an approximation. That's needed both for fidelity to the
  "fresh level 3" requirement and for correct XP.
- **Agent decision:** the bridge listens on loopback only and controls only
  characters it spawned.
- **Deferred:** GE price logging (G3) and the fixed price table. Both need the
  price-snapshot choice recorded in the decision log (alch-seeded vs
  post-warm-up), which is the user's call.

## Validation

- Fork build: `mvnw.cmd -B -q package -DskipTests` exit 0, run twice (before and
  after the spawn fix).
- Server log: "Using config file: worldprops/rl.conf", "RL bridge listening on
  127.0.0.1:43610", "2009Scape started in 7667 milliseconds".
- `scripts/gate_check.py`, final run (`results/gates/gate_check_20261005_220938.json`):

  | Requested ms/tick | Achieved ms/tick | Speedup |
  |---|---|---|
  | 600 | 604.51 | 1.0× |
  | 120 | 123.06 | 4.9× |
  | 60 | 63.18 | 9.5× |
  | 30 | 34.35 | 17.5× |
  | 15 | 17.63 | 34.0× |

  G2: combat level 3, total level 33, HP 10, at 3233,3230, 18 inventory
  stacks, 25 coins in the bank. 600 ticks of chopping: 38 interactions sent,
  10 logs, 250.0 XP, 25.0 XP per log.
- `uv run pytest`: 4 skipped with no server running; 4 passed (12.46 s) against
  the live server.
- `git ls-remote` on the fork and `gh repo view` confirm the push. Fork `rl` is at
  `1591c87d9d544e3dfdad956e3cbbd97ba2993af0`.

## Follow-Up

- G3: GE price logging over sped-up hours, then the fixed price table. Needs the
  user's snapshot choice.
- Check the wall-clock "in combat" flag under speedup once combat options exist.
- Possibly bind the game port to localhost in the fork.
- Possibly reduce ambient bots for speed, which affects the GE supply that G3
  will measure.
- Week-1 Python track: `docs/env-contract.md` and `docs/option-catalog.md` v0.
