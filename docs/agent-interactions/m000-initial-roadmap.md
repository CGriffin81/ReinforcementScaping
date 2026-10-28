# Agent Interaction

## Metadata

- Interaction ID: m000-initial-roadmap
- Timestamp CST: 2026-10-05 20:59:44 CST (from the session transcript's message timestamp, UTC−05:00; corrected 2026-10-28, the original estimate was ~20:57:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS
- Commit: None (the repo didn't exist yet; the roadmap was first committed with the m001 work in `1e7291a`)

## Full Prompt

> We are going to make a 2009 era Runescape bot. The pdf scopes out the proposal in answer to requirements. Make a roadmap to build this reinforcement learning project. Ask me any questions you need answered to perform work on this task.

Referenced files: `CS898BG_RL_Project_Proposal_2009Scape.pdf` (the proposal, dated
2026-09-23) and `Requirements.md` (the course proposal requirements).

## Response Summary

Read the proposal and the requirements. Checked the 2009Scape Singleplayer guide,
the upstream server's bot package listing (`core/game/bots/`,
`content/global/bots/`), the README (JDK 11, Maven, MySQL), and
`worldprops/default.conf` (`bots_influence_ge_price = true`, `members = true`). Then
checked the local machine: Ryzen 7 5800X / 16 threads, 32 GB, RTX 3050 8 GB,
Python 3.14, uv, git, and Docker present; no JDK; no 2009Scape install.

Wrote `ROADMAP.md`:
- Guiding principles: the simulator is the critical path, one environment contract
  with two backends, drive the server from the inside via `AIPlayer`/`Script` rather
  than the client, port formulas and measure overheads, and log every decision.
- System architecture, a draft bridge protocol, and the proposed repo layout.
- A table of technical decisions to settle early: SMDP discounting γ^τ, PBRS in an
  SMDP, wealth as net worth, skill-reward normalization, a fixed price table, RND
  with masking, masking for Envelope Q, pinning Python 3.12, Windows
  multiprocessing, and reproducibility.
- Throughput estimates for the simulator and the real server.
- A week-by-week plan (weeks 1–8) mapped to experiments E1–E7, with exit criteria.
- The critical path and fallbacks, a draft option catalog, and open questions.

Asked 8 questions: due date, division of labor and AI-code policy, permission to
install tooling and where the repo lives, starting character, episode horizon,
activity scope and combat, stretch preference, and whether any work had started.

## Documentation Changes

- Added `ROADMAP.md`.

## Code Changes

None.

## Infrastructure Changes

None.

## Decisions

- **Agent recommendations** (proposed, not yet accepted): simulator-first critical
  path; server control through server-side `AIPlayer` + `Script` instead of client
  automation; SMDP-correct discounting; Python 3.12; the LLM planner as stretch.
- **User decisions:** none in this interaction. The answers came in the next
  interaction (`m000-open-decisions-resolved`).

## Validation

- Confirmed the existence of the server bot API files and the bundled bot scripts
  through the GitLab API tree listing.
- Hardware and tooling facts came from the local system queries. Nothing was
  executed against a game server.

## Follow-Up

- The user answered the open questions; see `m000-open-decisions-resolved`.
