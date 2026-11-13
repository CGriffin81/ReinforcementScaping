# Post-project gaps

Gaps Caleb chose to leave for after the project. Each says what's missing, why it was left, what it costs the
study, and how it could be closed. The decision behind each is in `docs/decision-log.md`.

## West Ardougne is unreachable (OQ-37 (b), 2026-11-08)

**What's missing.** The sim and the server walker have no way into West Ardougne, so its 28 places (the sites of its
men, women, zombies, ghosts and rats among them) are masked for every character, although Plague City is complete
from the start.

**Why.** On this server the only way in is Plague City's own. Biohazard, which in 2009 opened the Mourners' way, isn't
implemented. The way in:
1. Edmond's dug hole in his East Ardougne garden (scenery 11417), which appears only with the quest's tunnel varbit
   set (`Vars.VARBIT_QUEST_PLAGUE_CITY_EDMOND_TUNNELS`);
2. the sewer below (2518, 9759);
3. the pipe up (scenery 2542, "climb-up") into West Ardougne at (2529, 3304). It lets a character through only with
   the quest past stage 7 and a gas mask worn (`PlagueCityListeners.kt`: "I can't let you enter the city without
   your gas mask on").

`spawn` completes quests as flags only, with no quest items (Caleb, 2026-11-06). So a fresh character has no gas mask
(a quest item, from Alrena), and the tunnel's varbit may not be set. Caleb chose to leave West Ardougne out rather
than give the start state a quest item (OQ-37).

**What it costs.** Probably little: its monsters are common kinds the agent can fight elsewhere, though the
screening for OQ-16 (a) found its sites would be offered in some bands and classes (their rates beat the ranker's
third-best there, travel aside).

**How to close it.**
- In the fork's `spawn` (`RLCommands.completeEveryQuest`): set the tunnel's varbit and give a gas mask (1506).
- In the travel model: the hole, the sewer and the pipe as one crossing from Edmond's garden to (2529, 3304), as
  Crandor's passage is done (`rlscape.routes.CROSSINGS`, `rlscape.bridge.walker.PASSAGE_STEPS`), passable only with
  the mask carried or worn. It needs timing on the server.
- Unmask West Ardougne's places, and check its sites in the calibration sets.

## A monster whose top damager has left the world dies with no killer (OQ-42, OQ-44 (a), 2026-11-08)

**What's missing.** The server credits a monster's death to the player who dealt it the most damage
(`ImpactHandler.getMostDamageEntity`, from the monster's impact log, by account uid). The log is cleared only when the
monster dies. If that player has left the world, the killer is null. The sim has no such case: its fights start
from monsters at full hitpoints.
- Inside a Kotlin `MapArea` zone, a null killer throws (`ClassScanner`'s zone wrapper declares
  `startDeath(e: Entity, killer: Entity)`), and the monster stays alive at 0 hitpoints: it can't be killed, every
  later hit on it is capped at 0, and it stays so until one character still there has dealt it more than the
  departed one did. The animated spades in the Abandoned Mine did this (`m002-spade-zero-hitpoints`).
- Elsewhere the death goes ahead with the monster as its own killer (`DeathTask`), and `NPC.finalizeDeath` passes no
  player to `handleDrops`: the kill's drops and credit go to no player.

**Why.** Caleb chose not to change the server for it: the spades are hazards (OQ-42), and the rest is this gap
(OQ-44 (a)). For an RL character it happens whenever a character is despawned with a monster hurt (every calibration
run ends at its budget mid-fight; an episode ends the same way). A human logging out does the same.

**What it costs.**
- It needs a departed character to have dealt the monster more than half its hitpoints (more than the next one can
  deal), so it shows up only where runs or episodes follow each other at one site.
- Stuck monsters: 106 of the sim's 2,184 combat sites are inside a Kotlin `MapArea` zone, by literal borders (71 in
  `MorytaniaArea`, 13 in the Lair of Tarn, 6 more in the Abandoned Mine (the possessed pickaxe beside the spades
  among them), 5 at the Kalphite Queen). None of the gate's cases is among them since the spades became hazards.
- Drops credited to no one: anywhere, for a kill a departed character did most of. It would bear on the loot cases'
  gp/hr in calibration, and a policy's loot on the server (E6, cut by OQ-17 (a′)); not measured.

**How it's found.** `scripts/calibrate_combat.py` records any monster it sees listed alive at 0 hitpoints in a run
(`at_zero`), and its report flags the case. A normal death starts in the same tick as the last hit, so such a
monster is stuck. The site is then a candidate hazard (`candidates.HAZARDS`), for Caleb. `ServerEnv` (cut by OQ-17 (a′), so for after the project) should do
the same once it exists. The unowned drops aren't flagged.

**How to close it.**
- In the fork (OQ-42 (a)): `getMostDamageEntity` returns the top damager still in the world, or the hit's source if
  none is (about six lines). Then the spades can be targets again, the stuck-monster check should find nothing, and
  a live test can pin it (one character deals a spade more than half its hitpoints and is despawned; a second kills
  it).
- Or, for RL characters only, a despawned character's uid leaves every monster's impact log (`RLPlayer.clear`).

## The Abyss's prayer drain isn't in the sim (OQ-48 (a), 2026-11-09)

**What's missing.** On the server, the Mage of Zamorak's teleport into the Abyss drains the character's prayer points
to 0 (`AbyssPlugin.teleport`). They stay at 0 until the character restores them, at an altar or with a prayer
potion, so until then it can flick no prayer: no protection, accuracy or damage prayers in a fight, and no Protect
Item. The sim has no prayer points at all. A fight flicks the prayers its levels give whenever it likes (flicking
costs nothing, as measured live), and the observation's prayer feature always reads 1. After an Abyss trip, the
server's character fights unprotected; the sim's flicks as before.

**Why.** Caleb chose (a) for OQ-48: the skull the same teleport gives is in the observation (one feature,
`skull_ticks`), and the drain is this gap. An Abyss runner seldom fights between trips. Prayer points would need
their own state, ways to restore them (an altar in the travel model, prayer potions), and every fight's flicking to
read them.

**What it costs.** A fight soon after an Abyss trip is easier in the sim than on the server, by as much as its
flicked prayers are worth. That's most for a fight its protection prayer covers, where the sim's character takes no
damage from that style. Fights in the Abyss itself aren't part of the gap: the teleport is the only way in, so they
flick nothing in the sim either (OQ-49 (a), 2026-11-09). It bears on the sim-to-server gap for any policy that
fights soon after leaving the Abyss on the server (E6, cut by OQ-17 (a′)), not on calibration, which never mixes
them.

**How to close it.**
- `CharacterState.prayer_points` (a float, the Prayer level when full), drained to 0 by `rlscape.sim.abyss.cross`.
- Restored by a prayer potion (in *V*: four doses) or at an altar. An altar would be a station in the travel model
  (Edgeville's monastery, next to the Abyss's bank, is the nearest), for a "recharge prayer" step an option could take
  on its way.
- The fights' flicking (`rlscape.combat.prayers`, the fighter's `flicks`) gives no prayer while the points are 0.
- The observation's prayer feature reads the points over the level (it's already there, reading 1).

## Chaos runes aren't crafted (Caleb, 2026-11-09)

**What's missing.** No option crafts chaos runes: `rc_chaos` (the ruins), `abyss_rc_chaos` (the Abyss's rift) and
`make_tiara_chaos` are gone, with the chaos talisman and the chaos tiara, which only they used, from *V* and the GE's
buys (*V* 366). Chaos runes are still bought, dropped and cast with.

**Why.** Caleb took chaos rune crafting out, as an intentional gap. Its altar is at the foot of a ladder maze, three
floors down from where entering the ruins lands the character (2275, 4847, 3). The sim had only an estimate of the
way down (30 steps and three floors), and the server runner doesn't climb the maze's ladders. The Abyss's chaos
rift, which lands the character beside the altar past the maze, was measured (a craft 2 ticks after the click from
its landing at (2269, 4840, 0); the altar's own portal, 15 steps away, 12 ticks to outside), but went with the rest.

**What it costs.**
- Chaos runes come at Runecrafting 35 (8.5 XP an essence, pure essence only), between cosmic (27, 8 XP, by the Abyss
  only) and nature (44, 9 XP).
- In gold they're worth little: 136 gp a rune against 137 for the pure essence it takes (`data/prices_v2.csv`), so a
  load loses gold until Runecrafting 74 makes two a time.
- So an agent at 35 to 43 trains on cosmic, body or below instead: a little less XP an essence, and slower trips than
  the Abyss's chaos rift.
- A policy on the server (E6, cut by OQ-17 (a′)) couldn't craft chaos runes either, so the two backends agree.

**How to close it.**
- Measure the maze: the ladders' order from the ruins' landing down to the altar's floor. A runner that climbs ladders
  (`interact` on each ladder, "Climb-down" or "Climb-up") would time it as `scripts/calibrate_runecrafting.py` times
  the other ruins.
- Put chaos back:
  - in `RC_RUNES` and `ABYSS_RUNES` (`rlscape/sim/runecrafting.py`), with its `INSIDE` walks (the maze, then the
    15 steps to the portal);
  - the rift's landing beside the altar (`abyss.CHAOS_LANDING`, one step from it);
  - the chaos talisman (1452) and tiara (5543) in `data/vocabulary.csv`. Their buys come back with `RC_RUNES`.
- The decision log's Runecrafting part 4 entry has the Abyss's chaos measurements.

## The Abyss's crowd is too light at the leeches in the sim (OQ-51 (a), 2026-11-09)

**What's missing.** A fight in the Abyss takes the outer ring's crowd (OQ-49 (a)): 0.8 attacks a tick from the
crossing's mix of kinds, less the fought monster's own swings. The rate was fitted to the server's fights at the
guardians (band 61) and the walkers (band 91). The sim's mix is the same whatever the character kills. On the
server, most likely, it isn't: killing leeches never thins the guardians and walkers that gather round, and those do
the damage. At the leeches the server's site does 0.47 damage a tick against the guardians' 0.37, though a leech
barely hits.

So at the leeches (band 61, melee) the sim's character:
- eats 0.68 of the server's food an hour (133.5 lobsters against 197.5);
- lasts 1.48 times as long before its food runs out.

Its XP an hour matches (0.94). The other two cases held out of the fit are inside the gate: the guardians at band 91
(1.14) and ranged at the walkers at band 91 (1.18).

**Why.** Caleb chose (a) for OQ-51, since the sim freezes on Nov 10. Modelling how the crowd builds up would need
three things:
- a gathering rate fitted on the server;
- new runs held out of that fit;
- a new env contract version after the freeze.

**What it costs.**
- **Food:** a fight at the leeches costs about a third less food in the sim than on the server. At band 61 that's
  about 64 lobsters an hour, or about 14,600 gp an hour at 228 gp a lobster.
- **The pouches:** leeches die fastest of the Abyss's monsters (about 550 kills an hour at band 61), so they drop the
  most of the pouches, which come only from the Abyss's monsters. An agent could overrate fighting leeches for
  pouches.
- **The gate:** the case is reported as a residual gap, as the gate's rule has it (ROADMAP week 3: "residual gaps are
  reported").

**How to close it.**
- Model how the crowd builds up:
  - each damaging kind gathers round a character that stays, at a rate fitted on the server. Standing tests can fit
    it, as the 1.13 attacks a tick measured standing at combat level 50 was;
  - a kind thins only when the character kills one of it.
- Fit it on the guardians and the walkers again, and hold out the leeches and another band.
- Add a new env contract version (§8's row for the Abyss's crowd), confirmed by Caleb.
- The decision log's OQ-49 (a) entry has the fit and the held-out runs
  (`results/calibration/abyss-fight-check-cases.json`).

## Trips through the Al Kharid toll gate may be too fast in the sim (OQ-86 (b), 2026-11-12)

**What's missing.** The cause of one travel check trip's miss, found by the sim-to-real table. "Varrock east bank to
Al Kharid, paying the toll" took the server 88 ticks on Nov 1 (the sim 84: 0.95) and 200 on Nov 6 (0.42). After the
home teleport, the server's walk from Lumbridge took 178 ticks, against 66 before, and the same at 600 ms ticks. The
sim takes the same route both days: the home teleport, then the toll gate. Between the two runs every quest became
complete at spawn (2026-11-06), which gives free passage at the gate (Prince Ali Rescue). Whether the server's walker
then went round the gate, or the gate took longer to pass, wasn't looked into. Travel's other 48 gated trips include
one more miss, the way out of the Abyss from its north (1.21), which the decision log explains.

**Why.** Caleb chose (b) for OQ-86: report it as a known gap without investigating. The sim is frozen (sim-v1.2), so a
fix couldn't reach the experiments, and investigating needs a server beside the training runs.

**What it costs.**
- **Time on such trips:** if the server's 200 ticks are what a person's trip takes, the sim takes about 0.4 of it for
  a walk through the gate into or out of Al Kharid (its bank, furnace and mine): on this trip, 116 ticks (about 70
  seconds) less.
- **How much it matters isn't measured:** the policies' decision logs can bound it, by the game time on options whose
  trips cross the gate.
- **The gate:** the trip is reported as a residual gap, as the gate's rule has it (ROADMAP week 3: "residual gaps
  are reported").

**How to close it.**
- Run the trip on the server both ways, 3 runs, with the bridge's state each tick, to see the walker's path and the
  gate (about an hour).
- If the gate's free passage takes longer, or the walker goes round it, fit the gate's time or fix the walker in a
  new sim version, and rerun travel's check set (`scripts/validate_travel.py --set check`).
