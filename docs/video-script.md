# Video script: Learning to Climb (draft 1)

A draft for Caleb to read over a recording of the replay page, written 2026-11-20 (`m002-video-script`).

- **How it reads:** **[SCREEN]** lines say what to show; the paragraphs under them are the narration. It's about
  1,535 words: about 11 minutes at 140 words a minute, and each section's times come from its words. The paragraphs
  marked *(cut for a short version)* are about 175 words, so without them it's about 9¾ minutes. A shorter limit
  needs real cuts (the simulator section and RQ4's list first).
- **The numbers** are measured: each is an hour-20 mean from the published evaluation summaries (2026-11-19). A
  configuration's number is the mean over its 5 training seeds, each evaluated on the same 30 episodes. The demo's
  numbers are one episode, seed 0, the same one the evaluation scored.
- **The verdicts** on H1 to H3 (section 6, filled 2026-11-23) are Caleb's (decision log, 2026-11-22): H1 and H2
  partly supported, H3 supported, each with the evidence the reviewer's guide gives it. The hypervolumes are
  `scripts/figures.py`'s `hypervolume.csv`: 0.394 (95% CI 0.360 to 0.456) for E5's one agent, 0.373 (0.278 to 0.484)
  for E3's five.
- **The slides and figures to show** (2026-11-22, `m002-video-slides`):
  - The title card and the formulation slide are a Slides deck, "Learning to Climb video slides"
    (https://claude.ai/artifact/2A3RY6Kavdyhy1LpaWrSnA, private to Caleb). Present it full screen, or download it as
    a PDF from its Share menu.
  - The figures: `uv run python scripts/figures.py` writes each as a PNG and a PDF to `results/figures/` (git-ignored).
- **The loop counts** (section 7, filled 2026-11-22) are the final census's (decision log, 2026-11-20), by OQ-90
  (a)'s rule: runs whose last 100k-decision block averages over 1,000 decisions an episode, the first round against
  the rerun. At γ_hr 0.5 and 0.9 that's 4 of 10 against none; at 0.99, 6 of 40 against 10 (8 of the rerun's 10 in
  E3).
- **The repository is private.** The graders need to open the link, so it has to be public, or shared with them,
  before you submit.

## The demo to record

The replay page for E3's (.5, .5) seed 0, beside the scripted guide. It's already made, in the E3 worktree
(`D:\ReinforcementScaping-runs\results\replays\`), with a copy in this one's `results\replays\` (git-ignored):
`e3-reward-weight-sweep_normalised_weights0.5-0.5_seed0_episode0.html`. To make it again (about 2 minutes, from the
E3 worktree):

```
uv run python scripts/replay.py runs/e3-reward-weight-sweep/normalised_weights0.5-0.5/seed0 --also scripted_guide
```

It holds four replays of episode seed 0. Each checkpoint is named by the training episodes it had played:

| Replay | Decisions | Total level | Net worth | What it does |
|---|---:|---:|---:|---|
| After 538 episodes (early) | 155 | 282 | 21,038 | woodcutting (and fletching), agility, melee; no plan |
| After 4,299 episodes (middle) | 752 | 223 | 1,540,616 | the thieving ladder, from hour 2 |
| After 5,688 episodes (final) | 729 | 280 | 1,046,904 | the same ladder, with more skill training |
| Scripted guide | 368 | 337 | 130,826 | crafting, combat and gathering, by a human guide's plan |

The moments the narration points at, in the final replay, as the page shows them ("decision N of 729", and the game
time beside it):

| Decision | Game time | Pickpocketing, for the first time | Thieving after it | Net worth after it |
|---:|---|---|---:|---:|
| 20 | 2:18 | men | 4 | 1,430 |
| 66 | 4:18 | farmers | 20 | 13,152 |
| 123 | 6:09 | warriors | 33 | 25,882 |
| 164 | 7:32 | (farmers again: Thieving reaches 38) | 38 | 36,721 |
| 172 | 7:54 | Master Farmers (they need 38) | 38 | 38,234 |

- Between decisions 164 and 172 it restocks: it buys a few items, catches and cooks shrimp, banks, and takes food.
  Decision 172 is its next pickpocketing trip.
- At decision 172, "What the policy weighed" puts dropping anchovies first (66%) and pickpocketing second (26%): the
  evaluation samples each choice from the policy, and this one drew the second. Best not to dwell on that panel there.

- Of the final replay's 1.05 million coins of net worth, about 1.03 million comes from pickpocketing; 93 of its 124
  pickpocketing trips end when the food runs out.
- Its fishing is shrimp, caught and cooked in the Lumbridge swamp: the food that keeps it pickpocketing.
- Its coins stay near zero: the wealth is the seeds it banks.

Recording, checked on the page (2026-11-20):
- Record the browser full screen (Windows: Win + Alt + R in the Xbox Game Bar, or OBS).
- Collapse "How to read this" at the top first, so the timeline is in view.
- The four buttons above **Play** pick the replay. **Play** and its speed menu (Slow, Normal, Fast, Fastest) play an
  episode, and the slider jumps to a decision.
- The page is long: the timeline and the map are at the top, then the decision, "What the policy weighed" and the
  skills, then the "Total level" and "Net worth (gp)" charts, which show all four replays at once. Zooming the
  browser out (Ctrl and minus) fits more of it in one shot.

---

## 1. Cold open (0:00 to 0:22)

**[SCREEN]** The final replay ("After 5,688 episodes") playing fast: the map's route and the net worth chart rising.

This is an agent I trained with reinforcement learning to play 2009Scape, a community recreation of RuneScape as it
was in 2009. It starts as a brand-new character. In twenty hours of game time, it decides, one activity at a time,
how to become as skilled and as rich as it can.

## 2. The question (0:22 to 1:01)

**[SCREEN]** Title card (the slides' slide 1): *Learning to Climb: Hierarchical RL for Skill and Wealth Accumulation
in 2009Scape*, Caleb Griffin, CS898BG.

I'm Caleb Griffin, and this is my project for CS898BG, Learning to Climb. RuneScape is a good test bed for long-term
planning. There are twenty-four skills, combat, and a player-run market. And the best moves often pay off late: you
spend hours on something that earns little, so that later activities earn far more. My question is whether an agent
that chooses between whole activities can learn plans like that, and beat sensible hand-made strategies. And how does
the balance between two goals, skill and wealth, change what it learns?

## 3. The formulation (1:01 to 2:44)

**[SCREEN]** The formulation (the slides' slide 2): state, then an option, then τ game ticks later, the reward and the
next state.

I set this up as a semi-Markov decision process. The agent doesn't click or press keys. Each action is an *option*:
a whole activity, like "chop logs and fletch them", "pickpocket Master Farmers", "fight cows", "bank", or "sell an
item on the Grand Exchange". There are 2,294 of them. An action mask hides the ones that aren't possible in the
current state, like an activity the character doesn't have the level for.

*(cut for a short version)* The observation is a vector of about 3,500 numbers: the character's levels, its
inventory, bank and equipment, where it is, and features of each option it could choose.

Every episode starts from a fresh level-3 character, with checkpoints every two game-hours, and ends at twenty. The
reward has two parts. Skill is the gain in levels, summed over all twenty-four skills. Wealth is the gain in net
worth: coins plus the value of everything the character owns. A weight sets the balance between them. Each part is
scaled by the best twenty-hour gain any baseline made on it, so half and half really means half and half.

Options take very different amounts of time, from a fraction of a second to over ten minutes. So the discount is by
game time: a reward τ ticks later is discounted by γ to the power τ, with γ set per game-hour. The learner is PPO
with action masking, with that discount built into its advantage estimates.

## 4. The simulator (2:44 to 3:27)

**[SCREEN]** The sim-to-real table (`results/summary/sim-to-real/README.md`), then the repository's `rlscape/sim/`.

Each training run is two million decisions, far too many to play on the real game server. So I built a simulator.
Its skilling, combat and drop formulas are ported from the server's source code. The rest, like walking, banking and
trading times, is measured on a local copy of the server, which I modified so an agent can drive a character from
inside it. Then every kind of option was checked against the server: 533 of 548 measurements are within plus or
minus 20 percent, and each one outside is explained. Every result in this video comes from the simulator.

## 5. The demo (3:27 to 5:48)

**[SCREEN]** The top of the replay page: the four bands of "What each replay did, over 20 game-hours".

Here's one agent, trained with skill and wealth weighted equally, at three points in its training, beside the
scripted guide. Each band is one twenty-hour episode, coloured by the kind of activity. Everything is the same
episode, seed zero, so the differences are what the agent learned.

**[SCREEN]** Pick "After 538 episodes" and play it. Show "What the policy weighed".

Early in training it's a generalist. It chops and fletches logs, runs an agility course, and fights. Look at what the
policy weighed: its top choice often gets only twenty to forty percent, so it's still unsure. It ends at total level
282, but with only about twenty thousand coins.

**[SCREEN]** Pick "After 5,688 episodes". Scrub to decision 20, then 66, 123 and 172 (game time 2:18, 4:18, 6:09
and 7:54), with the skills panel and the net worth chart in view.

The trained agent does something very different. At hour two it starts pickpocketing men. Around hour four it moves
on to farmers, and at hour six to warriors. Then, at hour seven and a half, its Thieving reaches 38, the level Master
Farmers need. It restocks its food, and its very next pickpocketing trip is on Master Farmers. They drop seeds, and on
the 2009 market some of those seeds were worth a lot. Up to that point the character was worth just 38 thousand
coins.

**[SCREEN]** Play from decision 172 to the end, with the net worth chart in view.

From there, its net worth climbs to over a million by hour twenty. Pickpocketing hurts when it fails, so it needs
food. It catches and cooks shrimp in the Lumbridge swamp to keep itself fed: 93 of its 124 pickpocketing trips end
because the food has run out. Nobody told it about this chain. It found it from the reward.

**[SCREEN]** Pick "scripted guide" and play it, then the total level and net worth charts.

The scripted guide follows a human training guide: crafting, combat and gathering, in a sensible order. In this
episode it ends at level 337 and 131 thousand coins. The trained agent ends at 280 and over a million. It gives up
some skill for eight times the wealth.

*(cut for a short version)* **[SCREEN]** Pick "After 4,299 episodes".

In the middle of training it had the same plan but chased wealth harder: 1.5 million coins, but level 223. By the end
it had rebalanced toward skill, which is what a half-and-half weight asks for.

## 6. The results (5:48 to 9:26)

**[SCREEN]** The progress figure (`progress`), with the baselines.

Here is the full evaluation. Each trained agent plays the same thirty episodes, and I compare it with four baselines:
random choice, a greedy agent that maximises XP per hour, a greedy agent that maximises coins per hour, and the
scripted guide. After twenty hours, the guide averages total level 351 and about 130 thousand coins. The greedy
wealth agent makes 1.76 million coins, but reaches only level 79.

**[SCREEN]** The trade-off figure (`pareto`): the five weightings' points beside the baselines.

The main experiment trains five weightings, from all skill to all wealth, five seeds each. As the weight moves toward
wealth, the average total level falls from 382 to 41, and net worth rises from about 11 thousand to 3.7 million
coins. At the ends, the all-skill agents average level 382, above the guide in four of five seeds. The all-wealth
agents average 3.7 million coins, about twice the greedy wealth agent, and all five seeds beat it. In between, they
don't: at the three mixed weightings, the best baseline scores higher, on average, on the very reward the agents were
trained for.

My first hypothesis, that the agents win by investing early as the demo's agent did, is only partly supported. Where
they win, at the ends, they're ahead from hour two, and the all-wealth agents win by trading uncut gems from the start.

**[SCREEN]** The activity-mix figure (`mix`).

The second, that each weighting finds its own mix of activities, is partly supported too. Toward wealth, yes: a
quarter skill almost only chops logs and fletches them into arrow shafts, and all wealth is buying uncut gems in a
shop and selling them on the Grand Exchange. But all skill and three-quarters skill share one mix.

*(cut for a short version)* **[SCREEN]** The trade-off figure (`pareto`) again, with E5's points.

Next, I trained one agent that is told the weight at the start of each episode, instead of five specialists. Told
"all skill", it averages level 359, against the specialists' 382. Told "all wealth", it averages 862 thousand coins,
against 3.7 million. But over the whole trade-off it about matches them: a hypervolume of 0.39 against 0.37, with
wide, overlapping intervals, for a fifth of the training.

**[SCREEN]** The learning curves for RQ4 (`learning_rq4`).

Last, what changes which strategies are found? I tried three changes at the half-and-half weight. Plain PPO there
averages level 263 and 588 thousand coins, but four of its five seeds end training in a loop. The agent in the demo
is the one that doesn't.
- An exploration bonus, random network distillation, did change what's discovered, which supports my third
  hypothesis: all its seeds took up buying and selling, and none fishing or banking, unlike plain PPO. But it ended
  lower on both: level 226 and 135 thousand coins.
- A shorter discount horizon pushed the agents toward wealth. At γ 0.5 per game-hour, they average 2.2 million
  coins. At 0.9, they average level 330 and 1.1 million coins, above 0.99's 263 and 588 thousand.
- Potential-based shaping ended at level 194 and 142 thousand coins, over four of its five seeds. The fifth seed
  loops so much that its evaluation episodes hit the evaluator's limit of 100,000 decisions before hour twenty. Which
  brings me to what went wrong.

## 7. What went wrong, and the limits (9:26 to 10:33)

**[SCREEN]** A looping run's learning curve: its decisions per episode jumping.

Some agents learn to loop. They repeat near-instant options that earn nothing, thousands of times an episode:
changing which loot to pick up, or depositing items at the bank and withdrawing them again. Partway through the
project, I changed two things in the trainer. I fixed a bug in how it handled an episode's time limit, and I gave
every decision a minimum cost in game time. Then I retrained all fifty runs. After that, none of the 10 runs at the
shorter discount horizons end looping, against 4 before. But at γ 0.99, 10 of 40 do, against 6 before, eight of them
in the main experiment. Why is untested.

*(cut for a short version)* There are limits too. Everything is in a simulator, checked against the server but not
the server itself. Quests are out of scope. And the low-level actions, like walking and clicking, are scripted, not
learned: I could only bound what learning them might add.

## 8. Close (10:33 to 10:57)

**[SCREEN]** The repository's README.

Everything is in the GitHub repository: the code, the simulator, the configurations, every experiment's published
results, and a reviewer's guide that maps each claim to its figure and code. **[Optional, your call: The code was
written with an AI coding assistant, under the course's AI policy, and every interaction is logged in the
repository.]** Thanks for watching.
