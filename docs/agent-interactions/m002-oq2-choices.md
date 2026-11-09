# Agent Interaction

## Metadata

- Interaction ID: m002-oq2-choices
- Timestamp CST: 2026-11-08 11:23:06 CST, from the session transcript's message timestamp (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (the choices recorded and the spawn flags built; the four skills not built yet)
- Commit: fork `7b377b2` (branch `rl`) and the main repo commit after `d0868d6` (branch `sim-v0`), both pushed

## Full Prompt

> OQ2
> Choice A - option A
> Choice C - Leave out studded leather, snakeskin, and jewelry.
> Choice D - Leave out the agility pyramid and brimhaven. Mark the barcrawl as complete so that agents may access
> barbarian agility. Also include Barbarian Fishing as a viable agility training method. If there are miniquest
> requirements to be able to do barbarian fishing, mark those as complete as well. Make the heavy fishing rod
> purchaseable from the GE.
> Choice E - Option A
> Choice F - Option A
> Choice H - Include The Abyss and tiaras as options
> Choice I - Option A

## Response Summary

- Recorded each choice with its options and Caleb's answer. Choices B and G weren't answered, so they're OQ-38.
- **Read from the server:**
  - **Barbarian Fishing** needs no miniquest: Fishing 48, Agility 15, Strength 15, the rod and bait. Each catch also
    gives 5 to 7 Agility and Strength XP. Otto's bed gives the rod only once his training starts, which stays
    unflagged, so the GE is the way to get one.
  - **The Barcrawl** gates the Barbarian Outpost course's gate.
  - **The Abyss** needs Enter the Abyss for the Mage of Zamorak's teleport. Its outer ring has obstacles, with a
    (level + 1)% chance a try. The rifts go to each altar.
  - **Pouches** drop from the abyssal monsters, or are Enter the Abyss's reward.
  - **Tiaras** come from a plain tiara and the talisman used on the altar.
  - **The death and astral altars** open on the server by the lacking quests' own levels.
- **Built (fork):**
  - `spawn` flags the Barcrawl and Enter the Abyss complete, flags only.
  - The bridge finds NPCs by the form a player sees. The mage is a multi-NPC named "null".
- **Checked live:** the course gate passes both ways; the mage teleports a fresh character to the Abyss with its prayer
  drained; 8 leaping trout gave 50 Fishing and 5 Agility and Strength XP each.
- **Raised for Caleb:** OQ-38 (B and G), OQ-39 (the death and astral altars), OQ-40 (pouches), OQ-41 (the rod's GE
  price).

## Documentation Changes

- `docs/decision-log.md`: "Decided: OQ-2's sim v1 choices (Caleb); built: the Barcrawl and Enter the Abyss complete from
  the start".
- `docs/open-questions-log.md`: OQ-38 to OQ-41.
- `docs/sim-v1-skills-draft.md`: now the spec for sim v1. Each choice's answer is stated, and it adds Barbarian
  Fishing, tiaras and the Abyss, plus the astral, death and blood altars. The counts are updated (about 85 items in
  *V*, about 2,065 actions and 3,300 features), as is the cost estimate (five to six days).
- `docs/env-contract.md`: v1.21, to confirm (§1: the two miniquests).
- `ROADMAP.md`: the status line.
- `CLAUDE.md`: the spawn line, and the bridge's NPC forms.
- This record.

## Code Changes

- **Fork** `Server/src/main/content/rl/RLCommands.kt`:
  - `completeMiniquests` (the Barcrawl: every bar, the card handed in; Enter the Abyss: varp 492 = 4), called by
    `spawnFreshCharacter`;
  - `shown(bot, node)` (`NPC.getShownNPC`), used by `candidates`, `interact`'s option lookup, and the index lookups
    of `interact` and `cast`.
- **Tests** (`tests/test_bridge_inputs_live.py`):
  - `test_the_barcrawl_and_enter_the_abyss_are_complete_from_the_start`;
  - `test_barbarian_fishing_needs_no_miniquest_and_trains_agility_and_strength`.

## Infrastructure Changes

- The server was rebuilt and started for the live checks and tests, then stopped by PID.

## Decisions

- **User decisions:** Choices A, E, F and I: (a). Choice C: studded leather, snakeskin and jewellery out. Choice D:
  - the Pyramid and Brimhaven out;
  - the Barcrawl complete;
  - Barbarian Fishing as Agility training, with any miniquest it needs complete;
  - the heavy rod on the GE.

  Choice H: the Abyss and tiaras in.
- **Agent choices (reversible):**
  - **Enter the Abyss flagged complete,** as the Barcrawl is. The Abyss needs the mage's teleport, which needs the
    miniquest. Flags only: its rewards (1,000 Runecrafting XP, the small pouch, the notes) aren't given, by the
    2026-11-06 rule for quests.
  - **Barbarian Training left unflagged.** Fishing doesn't need it, and its rod stage would only open the free rod
    under Otto's bed.
  - **The bridge's NPC lookup matches a multi-NPC's shown form,** as a client's click does. Without it the mage can't
    be found.
  - **The draft's new paths, proposed:** `barb_fish`, `make_tiara_<rune>`, `abyss_rc_<rune>`.

## Validation

- Live, by hand: the gate, the mage's teleport and barbarian fishing, as above.
- Live tests: every live file passed (42 and 19). Offline: 326 passed.

## Follow-Up

- Caleb: OQ-38 to OQ-41, and env contract v1.21.
- Next: build the four sim v1 skills.
- Commit when Caleb asks.
