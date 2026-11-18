# Agent Interaction

## Metadata

- Interaction ID: m002-loop-cause
- Timestamp CST: 2026-11-17 00:02:09 CST (the question) and 00:11:37 CST (Caleb's follow-up), the session transcript's
  timestamps (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. The question is answered with measurements from a finished run and three checked references. The
  remedies are logged as a post-project gap and the references are added to the resource list.
- Commit: this commit, to `main` directly (Caleb: "Log both, then commit it to main directly", 00:11:37 CST).

## Full Prompt

> With these runs looping, is that evidence of our tests, training, or instructions being bad? Is it a limitation of
> how these Reinforcement Learning algorithms learn the action space?

Then (00:11:37 CST), on Claude's offer to log the remedies in `docs/post-project-gaps.md` and to add the references to
`docs/resources.md`:

> Log both, then commit it to main directly

## Response Summary

- **The loop, measured** (E3's (.75, .25) seed 0, its finished decision log, by 50k-decision part; scratchpad
  `loop_time.py`):
  - A loot-setting change takes 1 tick (`LOOT_MODE_TICKS` in `rlscape/sim/slots.py`) and has no reward. Choosing the
    current mode is masked, so three of the four modes are always available.
  - After the collapse (1.55M to 2.0M), 95–99% of its decisions are loot changes, taking 6–29% of the game time.
  - Its other decisions earn 10–15 reward a game-hour, against about 13 before the collapse (1.2M to 1.5M).
  - So it still plays as before, with stalling in between. Its reward fell by about a fifth (261.2 to 204.9), about the
    game time the stalling takes.
- **The tests:** not the cause. The tests and the ±20% gate check that the sim matches the server, and a loot setting
  is instant in the game too. No test runs 2M decisions of learning. E2's sanity ladder checks that PPO learns small
  tasks.
- **The reward:** not reward hacking. Reward hacking is a loop that pays more than the intended play; this one pays
  less. One open exception: E4's RND bonus pays for new observations, and a loot change changes the observation
  (`m002-collapse-check`'s hypothesis, untested).
- **The training:** partly.
  - The first round's horizon bootstrap was a bug in the trainer, which Claude wrote. Fixed by PR #30. Among the same
    13 runs, 3 ended looping in the first round, against 2 in the rerun.
    - With more runs done, this doesn't hold at γ_hr 0.99. Among the 36 runs done at the 2026-11-18 15:28 run check
      (`m002-collapse-check`), 7 end looping in the first round and 8 in the rerun.
    - At γ_hr 0.5 and 0.9 (E6a), the count went from 3 to 0. At 0.99 (E3, E4, E5, E6b) it went from 4 to 8, and E3's
      alone from 1 to 7.
    - The rerun's floor costs a decision at least 1.15% of its value at γ_hr 0.5, 0.18% at 0.9 and 0.017% at 0.99. So
      the loops stopped where the floor costs most.
    - Why E3 loops more at 0.99 is untested. The candidates are the horizon bootstrap's removal and E3's sim change
      (the death-budget cap).
  - The trainer adapts PPO to the SMDP in its discount only (γ^τ with the 100-tick floor). Its batches (256 decisions
    an env), entropy bonus (0.01) and GAE λ count decisions, not game time.
  - The floor charges a 1-tick decision as 100 ticks: at γ_hr 0.99, 1 − 0.99^(100/6000) = 0.017% of the value, about
    0.03 when an episode earns about 200. A working option of about 300 ticks earns about 0.65.
  - In the loop, 95–99% of each batch is loot changes, so the working options get a few percent of the updates. This
    is Claude's inference for why it doesn't recover, not measured.
  - Which seed falls in varies. (.5, .5) loops on seed 1, not seed 0. (.75, .25) looped only on seed 0 when this was
    written, with seed 1 at about 1.75M. Seed 1 then looped in its last 100k block, from 1.9M. This was corrected at
    the 2026-11-17 07:08 run check (`m002-collapse-check`).
- **The RL limitation:** a known one.
  - In hierarchical RL, a high-level policy that switches options at no cost switches too often. Harb et al. (AAAI
    2018) add a deliberation cost, a fixed cost per switch. The floor is a weak form of one, paid in discount.
  - PPO's performance can collapse late in long runs: Dohare, Lan and Mahmood (EWRL 2023) and Moalla et al. (NeurIPS
    2024). Whether that mechanism is the one here is untested.
- **For the report:** a finding with its cause in two parts, a trainer bug that was fixed and a learner limitation
  that the action space exposes. The remedies (a per-decision cost, the loot setting folded into the fight options or
  masked until a fight, batches weighted by game time) change the sim or the trainer, so under Caleb's (a) they're
  after-project work.
  - At the 2026-11-18 15:28 run check, the counts by discount no longer support the first part at γ_hr 0.99 (above).
    How the report frames the cause is Caleb's call.
  - Some runs loop on banking instead of loot changes. They deposit and withdraw for a trip at a bank, 8 ticks a
    decision, with no reward: the first round's E3 (0, 1) seed 1, and the rerun's (.5, .5) seed 2 from 1.25M. Folding
    or masking the loot setting wouldn't stop these loops. The per-decision cost and game-time batches would. This was
    added at the 2026-11-17 16:18 run check (`m002-collapse-check`).

## Documentation Changes

- `docs/post-project-gaps.md`: "A high-level policy can stall on near-instant options": the loop, why it's left, what
  it costs, and four ways to close it.
- `docs/resources.md`: [53] Harb et al. (2018), [54] Dohare et al. (2023), [55] Moalla et al. (2024).
- `docs/decision-log.md`: the logging, under the 2026-11-16 decision on the collapsed runs.
- This record.

## Code Changes

- None. Scratchpad `loop_time.py` (read-only).

## Infrastructure Changes

- None.

## Decisions

- **Agent Recommendation:** report the loops as a finding, with both causes. Offered: log the remedies in
  `docs/post-project-gaps.md`, and add the three references to `docs/resources.md` if the report cites them.
- **User Decision (Caleb, 00:11:37 CST):** log both, the gap and the references. The runs carry on unchanged, as
  decided on 2026-11-16.

## Validation

- The measurements read E3's (.75, .25) seed 0's finished decision parts 24 to 39, with the option, duration and reward
  columns only.
- The constants come from the code and E3's config: `LOOT_MODE_TICKS = 1`, `SetLootMode.available`,
  `TICKS_PER_HOUR = 6_000`, `gamma_hr: 0.99`, `ent_coef: 0.01`, `n_steps: 256`.
- The references were checked by web search, from their listings, not their full texts:
  - Harb, Bacon, Klissarov and Precup, "When Waiting Is Not an Option: Learning Options With a Deliberation Cost",
    AAAI-18 (arXiv 1709.04571);
  - Dohare, Lan and Mahmood, "Overcoming Policy Collapse in Deep Reinforcement Learning", EWRL 2023;
  - Moalla et al., "No Representation, No Trust: Connecting Representation, Collapse, and Trust Issues in PPO",
    NeurIPS 2024 (arXiv 2405.00662).

## Follow-Up

- **Done:** the gap and the references are logged.
- **The report:** cite [53]–[55] where it discusses the looping runs. Dohare et al.'s entry is checked from its listing
  only; check its full text before the report quotes its findings.
