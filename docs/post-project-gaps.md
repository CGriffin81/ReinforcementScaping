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
  gp/hr in calibration and on E6's loot; not measured.

**How it's found.** `scripts/calibrate_combat.py` records any monster it sees listed alive at 0 hitpoints in a run
(`at_zero`), and its report flags the case. A normal death starts in the same tick as the last hit, so such a
monster is stuck. The site is then a candidate hazard (`candidates.HAZARDS`), for Caleb. `ServerEnv` (E6) should do
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
fights soon after leaving the Abyss (E6), not on calibration, which never mixes them.

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
- E6's policies can't craft chaos runes on the server either, so the two backends agree.

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
