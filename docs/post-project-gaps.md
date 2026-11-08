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
