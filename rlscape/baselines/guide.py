"""The scripted-guide baseline (E1; env contract decision 17): a new player following the RuneScape Wiki's training
guides as they stood in January 2009, the month the GE prices are frozen at. Its second draft, all 13 sim v0
skills, was reviewed by Caleb on 2026-10-31 (`docs/scripted-guide-draft.md`; decision log) and is one of E1's baselines.
Its fifth revision (Caleb, 2026-11-09, OQ-53 to OQ-59) adds sim v1's four skills, with the rules marked below.

The guides are the members' ones where January 2009 had them (Caleb, 2026-10-31: the character is a member):
melee [34], ranged [35], woodcutting [36], fishing [37], cooking [38], firemaking [39]. Mining, smithing, prayer and
magic had no members' guide, so theirs are the free-to-play pages or the skill articles; thieving's is members-only.
Fletching (brought forward from sim v1 by Caleb, 2026-10-31) had no training page, so its guide is the skill
article [40].

The guides say how to train each skill: the method at each level, and the tool or gear tier to use. They don't say
how to split time between skills, so the schedule is Caleb's:
- **Schedule** (2026-10-30, "Go after lowest skill"; 2026-10-31, "Minimum stint where the goal levels are multiples
  of 5"): the lowest of the 18 skills the sim trains directly (all but Hitpoints, which rises with combat; sim v1's
  four since OQ-53) starts a stint, trained until it reaches the next multiple of 5; then the lowest starts the next.
  Ties go to SKILLS' order. A skill that can't be trained right now (no bones, no logs, a fight its style can't start)
  passes the turn to the next lowest, which starts a stint of its own (OQ-58 (a): the stint used to stay, and Prayer's
  held most of an episode); the first resumes when it's the lowest again. Stints cut the trips between distant sites
  that switching every option would cost.
- **Sim v1's skills** (OQ-53): Agility, the Gnome course then the Wilderness's; Crafting, gems from drops, hard
  leather from 28, flax picked and spun from 10, soft leather below it from `kill_cows`' hides; Herblore, the best
  potion the level allows; Runecrafting, air then earth runes at the ruins. Their tables are below.
- **The coins** (Caleb, 2026-11-09): an upgrade takes at most half of them, the rest kept for the skills that lose
  gp; those skills' inputs (rune essence, herbs, vials, secondaries, thread) are bought whenever due. When the
  inputs for the stint cost more than the coins, the guide picks flax by Seers' Village, banks it until it covers them
  and the GE trip's two fares, sells it in one trip, and buys before any upgrade (OQ-59 (b): the money-maker carries
  through the stint).
- **Loot** (Caleb, 2026-11-09): half of what's obtained of an item is sold, half kept for processing, a whole stack at
  a time; what it buys to use is never sold.
- **Banking before a task** (Caleb, 2026-11-09): before gathering or a fight, a deposit if it would bank 5 or more
  slots the coming task doesn't use.
- **Gathering through the skilling slots** (rlscape.sim.skilling): the guide runs the slot that holds its method's
  path (the method, its produce kept); if no slot holds it, the skill's top XP slot.
- **Woodcutting** ([36]): normal trees to 14, oaks 15–29, willows from 30 (the guide's teaks and eucalyptus aren't
  in sim v0).
- **Mining** ([25]): copper and tin to 14, alternately (the guide's clay and essence aren't in sim v0); iron from 15,
  "the best ore for experience".
- **Fishing** ([37]): the small net to 19 (the guide's bait fishing at 5–20 isn't in sim v0); fly fishing from 20,
  "the fastest experience", with a fly rod and feathers bought for it. The guide fishes at Shilo Village, behind its
  quest; the sim's fly-fishing spot is Barbarian Village. Its monkfish (62) and barbarian fishing (70) aren't in sim
  v0.
- **Melee** ([34]):
  - each stat is trained only with its own style (accurate, aggressive, defensive); the guide leaves the order to the
    player
  - monsters come from the guide's list for the trained stat's level band (spiders, goblins, chickens and seagulls
    to 15; dark warriors to 30; hill giants to 45; flesh crawlers, experiments and moss giants to 55; white knights
    and ogres to 75; moss and fire giants, bloodvelds, bandits and armoured zombies after); the agent's 3 + 3 melee
    slots are searched for one, otherwise the top XP slot is fought
  - the scimitar is the weapon (the guide's "scimitar or dagger"); armour is the best tier the Defence level allows
  - drops are picked up (the `valuable` loot mode keeps cowhides and bones, which the guide says to collect)
- **Ranged** ([35]): the best shortbow the level allows, iron arrows; monsters from the guide's list by Ranged level
  (chickens, cows, rock crabs, men and goblins to 39, hill giants from 20; moss and ice giants from 40; yaks and green
  dragons from 50; fire giants from 60; demons and dragons later), otherwise the top ranged XP slot.
- **Magic** ([33]): the guide's strike spells (earth strike at 9, fire strike at 13), then the bolts, on the top
  magic XP slot, with runes bought ("the fastest way to obtain runes is to buy them"). Its other steps (curse at 19,
  telekinetic grab at 33, crumble undead at 39, high alchemy at 55) aren't sim v0 options. (Magic fights take off
  metal armour themselves: rlscape.sim.equipment.hinders.)
- **Prayer** ([30]): bury the bones that kills drop.
- **Firemaking** ([39]): burn the logs woodcutting brings in, the best the level allows (normal to 15, oaks to 30,
  willows after; the guide's maples and yews come from the GE, which the guide doesn't buy inputs from).
- **Cooking** ([38]): cook the fish fishing brings in ("easily obtainable with the Fishing skill").
- **Smithing** ([29]): bronze to 14 (smelt copper and tin, smith the bars), then iron from 15 ("the best way to power
  level"), from the ores mining brings in; with none, it mines them (copper and tin, or iron), as the guide says.
- **Fletching** ([40], "Level advancement"): arrow shafts cut where normal trees are chopped (a knife and an axe)
  to 24; oak longbows (u) 25–34; willow shortbows (u) 35–39; willow longbows (u) 40–49 ("they should not be
  strung"); maple shortbows (u) 50–54; maple longbows (u) 55–69; yew longbows from 70, strung. Bows are cut from the
  logs woodcutting banked (`fletch_<bow>` paths) or chopped and cut on the spot (`wc_<tree>_fletch`); when the
  guide's method isn't open, the earlier ones are tried. The knife is taken from Lumbridge Castle's spawn
  (`take_knife`, Caleb).
- **Thieving** ([27]): men to 4, the baker's stall 5–19, the silk stall 20–34, the fur stall 35–37, master farmers
  38–54, Knights of Ardougne 55–64, Menaphite thugs from 65. The guide's 30–37 (The Feud's experience) and 45–55
  (blackjacking bandits) need The Feud, which isn't in the sim, so its neighbouring methods stretch over those
  levels; it pickpockets the thugs it would blackjack. The guide's "cakes or better" are whatever food is carried:
  a food withdrawal fills every free slot, which leaves no room for the loot, so thieving stops when HP runs low and
  the schedule moves on while it regenerates.
- **Gear and tools:** upgrades are bought on the GE in this order, as the calibration characters do (env contract
  §7): the tool for the skill being trained (and for ranged the bow, arrows; magic the scarcest rune of its spell;
  smithing a hammer), then the scimitar, then armour, helm to kiteshield. Each takes the best tier that's both an
  upgrade and affordable, moving up a tier at a time as the guides do. A skill's own buys are also tried just before
  it, so a skill further down the schedule isn't left without them when the lowest can't be trained. Gear banked by
  a deposit is withdrawn before a fight; for ranged and magic, when the bank holds their arrows, bow or runes.
- **Processing inputs come from the guide's own gathering, not the GE**, as the 2009 guides do it (cook what you
  fish, burn what you cut, smelt what you mine). A GE buy takes as many as the coins allow, up to 1,000, which
  would spend everything on one input.
- **Funding upgrades** (the guides fund gear by selling cowhides and logs): when an upgrade can't be afforded, sell
  what's carried if it pays for it at GE prices, or take banked produce out to sell (`bank_withdraw_for_sale`) if
  that would. What's carried for sale means vocabulary produce (neither gear nor kept when banking, so nothing bought
  for use is sold, nor bones, which Prayer needs) and banknotes. Logs, ores and fish are sold as the guides do;
  the processing skills use what's left.
  Items outside V (a stall's cakes) stay banked: `sell_ge_misc` sells every misc item carried, gear included.
- **A full inventory:** cook raw fish while fewer than FOOD pieces of food are held (the fishing guide cooks fish
  "for food"), then use what's carried (burn the logs, bury the bones, smelt or smith), then bank. A deposit keeps only the last task's kit (rlscape.sim.kits); after thieving that's all
  the food, so if the inventory is full of it (a stall's bread), the surplus is sold. Before a gathering skill the
  guide takes its tool back out (`bank_withdraw_for_<task>`) if it isn't held.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from functools import cache

import numpy as np

from rlscape.envs.sim_env import SimEnv
from rlscape.gamedata import server as gd
from rlscape.sim.buying import (ARMOUR, ARROWS, AXES, CRAFTING_INPUTS, HAMMER, HERBLORE_INPUTS, PICKAXES,
                                RUNECRAFTING_INPUTS, SCIMITARS, SHORTBOWS, BankWithdrawForSale, is_upgrade, usable)
from rlscape.sim.economy import kept_on_deposit
from rlscape.sim.equipment import WEAPON
from rlscape.sim.health import foods_held
from rlscape.sim.skilling import slot_holding
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.slots import K
from rlscape.sim.kits import kit
from rlscape.sim.state import COINS, CharacterState
from rlscape.vocabulary import vocabulary

FLY_ROD, FEATHERS, FEATHER_REORDER = 309, 314, 50
IRON_ARROWS, ARROW_REORDER = 884, 50
RUNE_REORDER = 30  # casts of the guide's spell held (inventory and bank); below it, its scarcest rune is bought
FOOD = 10  # pieces of food to keep; raw fish are cooked only below it
KIT_WITHDRAWAL = {"fish_shrimp": "bank_withdraw_for_fish_shrimp", "fish_shrimp_swamp": "bank_withdraw_for_fish_shrimp",
                  "fish_fly": "bank_withdraw_for_fish_fly"}
DRAYNOR_WIZARDS_PICK = 14  # Draynor's Dark wizards (level 7) pick a character of combat level 14 or less
COMBAT = ("attack", "strength", "defence")
SIM_V1 = ("agility", "crafting", "herblore", "runecrafting")  # Caleb, 2026-11-09 (OQ-53): they join the schedule
SKILLS = (*COMBAT, "ranged", "magic", "prayer", "woodcutting", "firemaking", "fletching", "fishing", "cooking",
          "mining", "smithing", "thieving", *SIM_V1)  # SCHEDULE: the lowest of these starts the next stint
STINT = 5  # a stint trains its skill to the next multiple of this level
STYLE = {"attack": "accurate", "strength": "aggressive", "defence": "defensive"}
PROCESSING = {"prayer": "bury_bones", "firemaking": "burn_logs", "cooking": "cook_fish"}
# Pay-to-play melee training, January 2009 ([34]): monsters by the trained stat's level.
MELEE_BANDS = (
    (15, {"spider", "goblin", "chicken", "seagull"}),
    (30, {"dark warrior"}),
    (45, {"hill giant"}),
    (55, {"flesh crawler", "experiment", "moss giant"}),
    (75, {"white knight", "ogre", "jogre", "mogre"}),
    (99, {"moss giant", "fire giant", "skeletal hand", "zombie hand", "mutated bloodveld", "bandit",
          "armoured zombie"}),
)
# Pay-to-play ranged training, January 2009 ([35]): monsters by Ranged level.
RANGED_BANDS = (
    (19, {"chicken", "cow", "rock crab", "man", "woman", "goblin"}),
    (39, {"chicken", "cow", "rock crab", "man", "woman", "goblin", "hill giant"}),
    (49, {"moss giant", "hill giant", "ice giant", "ice warrior", "rock crab"}),
    (59, {"yak", "rock crab", "hill giant", "ice giant", "moss giant", "green dragon"}),
    (69, {"fire giant", "green dragon", "yak"}),
    (79, {"fire giant", "green dragon", "greater demon", "lesser demon", "iron dragon", "yak"}),
    (99, {"green dragon", "blue dragon", "red dragon", "black dragon", "bronze dragon", "iron dragon", "steel dragon",
          "mithril dragon", "yak", "fire giant", "tormented demon"}),
)
# Magic, January 2009 ([33]): the strike spells, then the bolts (the ones sim v0 casts whose runes the GE sells).
GUIDE_SPELLS = ("wind_strike", "water_strike", "earth_strike", "fire_strike", "wind_bolt", "water_bolt",
                "earth_bolt", "fire_bolt")
# Fletching, January 2009 ([40]): (first level, paths), the bank path before the chop-and-fletch one.
FLETCHING = ((1, ("wc_logs_fletch",)), (25, ("fletch_oak_longbow_u", "wc_oak_fletch")),
             (35, ("fletch_willow_shortbow_u", "wc_willow_fletch")),
             (40, ("fletch_willow_longbow_u", "wc_willow_fletch")),
             (50, ("fletch_maple_shortbow_u",)), (55, ("fletch_maple_longbow_u",)),
             (70, ("fletch_string_yew_longbow", "fletch_yew_longbow_u")))
# Thieving training, January 2009 ([27]): (first level, method), as mapped onto sim v0 above.
THIEVING = ((1, "pickpocket_men"), (5, "steal_bakers_stall"), (20, "steal_silk_stall"), (35, "steal_fur_stall"),
            (38, "pickpocket_master_farmers"), (55, "pickpocket_knights"), (65, "pickpocket_menaphite_thugs"))
# Sim v1's four skills (Caleb, 2026-11-09, OQ-53), from the January 2009 pages:
# Agility training ([45]): the Gnome Stronghold course to 25, Werewolf Skullball 25-52 (not in the sim, so the Gnome
# course stretches over it), the Wilderness course 52-80, Ape Atoll 80+ (not in the sim, so the Wilderness stretches).
AGILITY = ((1, "agility_gnome"), (52, "agility_wilderness"))
# Crafting ([43], [44]): hard leather bodies from 28, from cows' hides tanned at Ellis; flax picked by Seers' Village
# and spun into bowstrings from 10; below 10, soft leather from cows' hides (Caleb: "Cowhides from cows"), the best item
# the level allows, the hides from kill_cows (Caleb, 2026-11-09); gems only as drops bring them ("buying uncut gems for
# cutting is not worthwhile"). The page's wool (spun to 8) was bought for a while, and then taken out (Caleb,
# 2026-11-09: "Remove wool"): a spin loses 112 gp, wool's 123 against a ball's 11.
SOFT_LEATHER = ((1, "craft_leather_gloves"), (7, "craft_leather_boots"), (9, "craft_leather_cowl"),
                (11, "craft_leather_vambraces"), (14, "craft_leather_body"), (18, "craft_leather_chaps"))
GEM_CUTS = ((1, "cut_opal", 1625), (13, "cut_jade", 1627), (16, "cut_red_topaz", 1629), (20, "cut_sapphire", 1623),
            (27, "cut_emerald", 1621), (34, "cut_ruby", 1619), (43, "cut_diamond", 1617))
FLAX_SPIN, HARD_LEATHER_LEVEL = 10, 28
NEEDLE, THREAD, CHISEL, FLAX = 1733, 1734, 1755, 1779
COWHIDE, LEATHER, HARD_LEATHER = 1739, 1741, 1743
THREAD_REORDER = 5  # a reel sews 5 items
# Runecrafting ([47]): air runes to 9, then earth runes ("one may stay at earth runecrafting until 30"); the members'
# page's methods ([48]: Zanaris's cosmics, the ZMI altar, astral runes) aren't in the sim. Its talisman is bought
# (quests are flags only, so Rune Mysteries' air talisman isn't given), and rune essence too (the sim mines none).
RUNECRAFTING = ((1, "rc_air", 1438), (9, "rc_earth", 1440))
RUNE_ESSENCE, ESSENCE_LOAD = 1436, 28
# The flax money-maker (Caleb, 2026-11-09, OQ-59 (b)) sells at the GE, and the sim's way from the GE to the field is
# the home teleport and the 1,000 gp charter from Port Sarim to Catherby (back, the charter too when the teleport
# waits). Selling each load netted nothing, so the flax is banked until it covers the inputs and two fares.
FLAX_FARES = 2_000
# Herblore ([46], the potions by level; January 2009 had no training page): the best potion the level allows, from
# level 3 (Druidic Ritual's XP, Caleb, OQ-56), its herb, vial of water and secondary bought.
VIAL_OF_WATER, HERB_LOAD = 227, 14


def woodcutting_method(level: int) -> str:
    return "wc_logs" if level < 15 else "wc_oak" if level < 30 else "wc_willow"


def mining_method(state: CharacterState) -> str:
    if state.level("mining") >= 15:
        return "mine_iron"
    copper, tin = (state.bank.get(i, 0) + state.inventory.get(i, 0) for i in (436, 438))
    return "mine_copper" if copper <= tin else "mine_tin"


def shrimp_method(state: CharacterState) -> str:
    """Caleb (2026-11-01): Lumbridge Swamp's shrimp while Draynor's wizards would attack the character, Draynor's
    (next to its bank) after."""
    return "fish_shrimp_swamp" if state.combat_level() <= DRAYNOR_WIZARDS_PICK else "fish_shrimp"


def fishing_method(state: CharacterState) -> str:
    return "fish_fly" if state.level("fishing") >= 20 else shrimp_method(state)


def thieving_methods(level: int) -> list[str]:
    """The guide's method for the level first, then the earlier ones (for when it can't start, e.g. the desert
    without coins for a Shantay pass)."""
    return [method for start, method in reversed(THIEVING) if start <= level]


def fletching_methods(level: int) -> list[str]:
    """The guide's paths for the level first, then the earlier levels' (when the logs for these aren't held)."""
    return [path for start, paths in reversed(FLETCHING) if start <= level for path in paths]


def methods_for(table: tuple, level: int) -> list:
    """A (first level, method, ...) table's methods for the level, the guide's first, then the earlier ones."""
    return [row[1] if len(row) == 2 else row[1:] for row in reversed(table) if row[0] <= level]


def guide_potion(level: int) -> gd.Potion | None:
    """The best potion the Herblore level allows, by the January 2009 table ([46])."""
    potions = [p for p in gd.herblore_potions().values() if p.level <= level]
    return max(potions, key=lambda p: (p.level, p.experience), default=None)


@cache
def grimy_of() -> dict[int, int]:
    """A clean herb -> its grimy herb, which is what's bought (the GE's herbs)."""
    return {h.clean: h.grimy for h in gd.herbs().values()}


def guide_spell(level: int) -> gd.CombatSpell:
    """The best of the guide's spells the Magic level allows."""
    spells = gd.combat_spells()
    return max((spells[s] for s in GUIDE_SPELLS if spells[s].level <= level), key=lambda s: s.level)


def held(state: CharacterState, item: int) -> int:
    """Units held anywhere: inventory, bank, or worn."""
    worn = sum(state.worn(slot) for slot, i in state.equipment.items() if i == item)
    return state.inventory.get(item, 0) + state.bank.get(item, 0) + worn


def units(state: CharacterState, item: int) -> int:
    """Units held anywhere, banknotes in the inventory included (a GE buy of several arrives as notes)."""
    note = gd.noted_ids().get(item)
    return held(state, item) + (state.inventory.get(note, 0) if note is not None else 0)


def at_most(state: CharacterState, skill: str, level: int) -> CharacterState:
    """The state as if the skill were at most `level` (to pick the method a lower level uses)."""
    if state.level(skill) <= level:
        return state
    capped = replace(state, xp=list(state.xp))
    capped.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    return capped


def smithing_metals(level: int) -> tuple[str, ...]:
    return ("iron", "bronze") if level >= 15 else ("bronze",)


@cache
def kept_for_skills() -> frozenset[int]:
    """What the guide buys for sim v1's Crafting, Herblore and Runecrafting, never sold: their tools, thread, wool,
    vials, the potions' secondaries and unfinished potions, rune essence and talismans. Loot they use (hides,
    leathers, uncut gems, herbs) is produce, half sold (Caleb, 2026-11-09)."""
    loot = {COWHIDE, LEATHER, HARD_LEATHER} | {uncut for *_, uncut in GEM_CUTS} | {
        i for h in gd.herbs().values() for i in (h.grimy, h.clean)}
    return frozenset((set(CRAFTING_INPUTS) | set(HERBLORE_INPUTS) | set(RUNECRAFTING_INPUTS)) - loot)


CLEAR_SLOTS = 5  # a deposit before gathering or a fight must free this many slots (Claude's choice, for Caleb)


def task_of(state: CharacterState, option) -> str | None:
    """The task an option is about to do: a fight's class, the path a skilling slot holds now, kill_cows' class."""
    if hasattr(option, "slots") and option.family != "combat" and hasattr(option, "index"):
        candidate = option.slots.candidate(state, option.skill, option.index)
        option = candidate.path if candidate is not None else option
    if hasattr(option, "choice") and (choice := option.choice(state)) is not None:
        return f"combat:{choice[1].combat_class}"  # kill_cows
    return getattr(option, "task", None)


def junk_slots(state: CharacterState, task: str | None) -> int:
    """Inventory slots carried that the task about to start doesn't use (its kit, rlscape.sim.kits), a slot a stack or
    banknote, a slot a unit otherwise. Measured against the coming task, not the last: a deposit that banked the
    coming fight's runes would be undone by its withdrawal, and done again."""
    keep, stackable, unnoted = kit(state, task), gd.stackable_items(), gd.unnoted_ids()
    return sum(1 if (i in stackable or unnoted.get(i, i) != i) else n for i, n in state.inventory.items()
               if i not in keep and i != COINS)


def carried_flax(state: CharacterState) -> int:
    """Flax carried, banknotes included (bank_withdraw_for_sale takes it out as notes)."""
    return state.inventory.get(FLAX, 0) + state.inventory.get(gd.noted_ids().get(FLAX), 0)


def upgrade_budget(state: CharacterState) -> int:
    """The coins an upgrade may take: half of them, the other half kept for training the skills that lose gp (Caleb,
    2026-11-09: "half of gp should be preserved for training skills that are net negative on gp, when making upgrade
    decisions")."""
    return state.coins() // 2


@cache
def kept_for_prayer() -> frozenset[int]:
    """Bones: Prayer's only source in sim v0, and worth little at the GE."""
    return frozenset(gd.bone_experience())


class ScriptedGuidePolicy:
    name = "scripted_guide"

    def __init__(self) -> None:
        self.vocabulary = frozenset(vocabulary())
        self.last: str | None = None  # the previous option id
        self.sold: Counter[int] = Counter()  # units sold of each item this episode (half the loot is sold)
        self.funding: str | None = None  # the skill the flax money-maker is funding, until its inputs are bought
        self.stint: tuple[str, int] | None = None  # (skill, goal level)

    def reset(self, seed: int | None) -> None:  # deterministic: nothing to seed
        self.last, self.stint, self.sold, self.funding = None, None, Counter(), None

    def schedule(self, state: CharacterState) -> list[str]:
        """SCHEDULE: the stint's skill first, then the rest lowest first. A stint ends when its skill reaches the goal
        level, the next multiple of STINT above where it started; the lowest skill then starts the next."""
        lowest_first = sorted(SKILLS, key=lambda s: (state.level(s), SKILLS.index(s)))
        if self.stint is None or state.level(self.stint[0]) >= self.stint[1]:
            skill = lowest_first[0]
            self.stint = (skill, (state.level(skill) // STINT + 1) * STINT)
        return [self.stint[0], *(s for s in lowest_first if s != self.stint[0])]

    def act(self, env: SimEnv, obs: np.ndarray) -> int:
        state, mask = env.sim.state, env.action_masks()
        ids = {o.id: i for i, o in enumerate(env.options)}
        allowed = lambda option_id: option_id in ids and bool(mask[ids[option_id]])
        order = self.schedule(state)
        plan = ((o, owner) for o, owner in self._plan(env, state, order, allowed) if allowed(o))
        chosen = next(plan, None)
        if chosen is not None and chosen[0] == "bank_deposit" and (self.last or "").startswith("bank_withdraw"):
            # not straight back into the bank what was just taken out (seed 14 looped 1,300 times on a magic
            # withdrawal and a full inventory's deposit): the plan's next option, if it has one
            chosen = next((c for c in plan if c[0] != "bank_deposit"), chosen)
        if chosen is None:  # nothing in the plan is possible: the first allowed action
            action, owner = int(np.flatnonzero(mask)[0]), None
        else:
            action, owner = ids[chosen[0]], chosen[1]
        just_banked = self.last is not None and self.last.startswith(("bank_withdraw", "bank_deposit"))
        if (env.options[action].family in ("gathering", "combat") and allowed("bank_deposit") and not just_banked
                and junk_slots(state, task_of(state, env.options[action])) >= CLEAR_SLOTS):
            # bank what the task at hand doesn't need before gathering or fighting fills the inventory (Caleb,
            # 2026-11-09: "not banking everything they don't need for the task at hand"); the option comes next
            action, owner = ids["bank_deposit"], None
        if owner is not None and owner != order[0]:
            # the stint's skill couldn't be trained (Prayer without bones, say), and the plan fell to another skill's
            # training: that skill starts a stint, and the first resumes when it's the lowest again (Caleb, OQ-58 (a))
            self.stint = (owner, (state.level(owner) // STINT + 1) * STINT)
        self.last = env.options[action].id
        self._count_sale(state, self.last)
        money_maker = (self.last in (f"sell_ge_{FLAX}", "bank_withdraw_for_sale")
                       or self.last == slot_holding(env.options, state, "pick_flax"))
        if owner is not None and money_maker and self._input_need(state, owner) is not None:
            self.funding = owner  # the money-maker took over: it carries through the stint (Caleb, 2026-11-09)
        if self.funding is not None and (self.stint is None or self.stint[0] != self.funding
                                         or self._input_need(state, self.funding) is None):
            self.funding = None  # its inputs are bought, or the stint moved on
        return action

    def _plan(self, env: SimEnv, state: CharacterState, order: list[str], allowed):
        """(option id, the skill it trains or None for logistics), in order of preference; the first allowed one is
        taken. Logistics (upgrades, funding, a full inventory) are decided for the skill due next, then each skill
        is tried in schedule order."""
        skill = order[0]
        if self.last is not None and self.last.startswith("bank_withdraw_gear_"):
            combat_class = self.last.removeprefix("bank_withdraw_gear_")  # use it before it's banked again
            yield from ((f, s) for s in (COMBAT if combat_class == "melee" else (combat_class,))
                        for f in self._fights(env, state, s))
        prices, budget = gd.ge_prices_2009(), upgrade_budget(state)
        roles = [] if self.funding is not None else self._upgrades(state, skill)  # funding: the inputs come first
        yield from ((o, None) for o in ([] if self.funding is not None else self._affordable(state, skill)))
        # funding the next upgrade: enough that it fits in the half of the coins upgrades may spend
        shortfall = min((2 * prices[i] - state.coins() for tiers in roles for i in tiers if prices[i] > budget),
                        default=None)
        if shortfall is not None:  # at GE prices
            carried = self._carried_for_sale(state)
            value = sum(prices.get(i, 0) * n for i, n in carried.items())
            if value >= shortfall:
                yield from ((f"sell_ge_{item}", None)
                            for item in sorted(carried, key=lambda i: -prices.get(i, 0) * carried[i]))
            if value + self._banked_for_sale(state, prices) >= shortfall:
                yield "bank_withdraw_for_sale", None
        if state.free_slots() == 0:
            if carried_flax(state) and any(self._flax_ready(state, s) for s in order):
                yield f"sell_ge_{FLAX}", None  # enough of the money-maker's flax: sold before a deposit banks it
            if sum(n for _, n in self._food(state)) < FOOD:
                yield "cook_fish", None
            for next_skill in order:  # use what's carried (logs, bones, ores, bars) before banking it
                yield from ((o, None) for o in self._process_carried(state, next_skill))
            yield "bank_deposit", None  # keeps the last task's kit (rlscape.sim.kits)
            yield from ((f"sell_ge_{item}", None) for item, _ in self._food(state) if item in self.vocabulary)
        for next_skill in order:
            yield from ((f"buy_ge_{best}", next_skill) for chain in self._skill_chains(state, next_skill)
                        if (best := next((i for i in reversed(chain) if prices[i] <= budget and usable(state, i)
                                          and is_upgrade(state, i)), None)) is not None)
            yield from ((o, next_skill) for o in self._consumables(state, next_skill))
            if self._short(state, next_skill):  # its inputs cost more than the coins: flax pays for them (OQ-59 (b))
                if self._flax_ready(state, next_skill):  # sell it all in one GE trip
                    if carried_flax(state):
                        yield f"sell_ge_{FLAX}", next_skill
                    yield "bank_withdraw_for_sale", next_skill  # the banked loads, as banknotes
                else:  # another load, banked when the inventory fills (picking flax keeps nothing: OQ-52)
                    yield from ((o, next_skill) for o in self._slots_holding(env, state, ["pick_flax"]))
            yield from ((o, next_skill) for o in self._train(env, state, next_skill, allowed))
        yield "bank_deposit", None

    def _train(self, env: SimEnv, state: CharacterState, skill: str, allowed):
        """The options that train one skill the guide's way, in order of preference."""
        if skill in COMBAT or skill in ("ranged", "magic"):
            combat_class = "melee" if skill in COMBAT else skill
            fights = list(self._fights(env, state, skill))
            if any(allowed(f) for f in fights):  # better gear from the bank first, for a fight that can start
                yield f"bank_withdraw_gear_{combat_class}"
            yield from fights
            if skill in ("ranged", "magic") and self._kit_banked(state, skill):
                yield f"bank_withdraw_gear_{combat_class}"  # the bow and arrows, or the runes, a deposit banked
        elif skill in PROCESSING or skill == "smithing":
            yield from self._process_carried(state, skill)
            if skill in PROCESSING:
                yield f"bank_withdraw_for_{PROCESSING[skill]}"
                if skill == "firemaking":  # no logs to burn (Fletching cuts them all): chop and burn them, as [39]
                    trees = dict.fromkeys((woodcutting_method(state.level("woodcutting")), "wc_oak", "wc_logs"))
                    yield from self._slots_holding(env, state, [f"{tree}_burn" for tree in trees])
                    yield "bank_withdraw_for_woodcutting"  # the axe and tinderbox
            else:
                for metal in smithing_metals(state.level("smithing")):
                    yield from (f"bank_withdraw_for_smith_{metal}", f"bank_withdraw_for_smelt_{metal}")
                ore = "mine_iron" if state.level("smithing") >= 15 else mining_method(at_most(state, "mining", 14))
                yield from self._slots_holding(env, state, [ore])  # nothing to smith: mine it, as [29] says
                yield "bank_withdraw_for_mining"
        elif skill == "thieving":
            yield from self._slots_holding(env, state, thieving_methods(state.level("thieving")))
            yield "skill_thieving_xp1"
        elif skill == "fletching":
            yield "take_knife"  # Lumbridge Castle's, if none is held (Caleb)
            yield from self._slots_holding(env, state, fletching_methods(state.level("fletching")))
            yield "bank_withdraw_for_woodcutting"  # the axe and knife, for chopping and cutting on the spot
            yield "skill_fletching_xp1"
        elif skill == "agility":
            yield from self._slots_holding(env, state, methods_for(AGILITY, state.level("agility")))
            yield "skill_agility_xp1"
        elif skill == "crafting":
            yield from self._crafting(env, state)
        elif skill == "herblore":
            level = state.level("herblore")
            if (potion := guide_potion(level)) is not None:
                yield from self._slots_holding(env, state, [f"potion_{potion.name}"])
            herbs = sorted((h for h in gd.herbs().values() if h.level <= level), key=lambda h: -h.level)
            yield from self._slots_holding(env, state, [f"clean_{h.name}" for h in herbs])  # herbs drops brought
            yield "skill_herblore_xp1"
        elif skill == "runecrafting":
            methods = methods_for(RUNECRAFTING, state.level("runecrafting"))
            # the page's methods only, at the ruins: no top-slot fallback, which without the talisman is the Abyss
            yield from self._slots_holding(env, state, [method for method, _ in methods])
        else:
            method = self._method(state, skill)
            fallback = [shrimp_method(state)] if skill == "fishing" else []  # no fly rod or feathers yet
            yield from self._slots_holding(env, state, [method, *fallback])
            yield KIT_WITHDRAWAL.get(method, f"bank_withdraw_for_{skill}")  # its tool from the bank
            if skill == "fishing":
                yield "bank_withdraw_for_fish_shrimp"
            yield f"skill_{skill}_xp1"

    def _affordable(self, state: CharacterState, skill: str) -> list[str]:
        """The upgrades the guide would buy now with the skill due: per role, the best tier that fits the upgrade
        budget, half the coins (the guides move up a tier at a time: "mithril if you can afford it")."""
        prices, budget = gd.ge_prices_2009(), upgrade_budget(state)
        return [f"buy_ge_{best}" for tiers in self._upgrades(state, skill)
                if (best := next((i for i in tiers if prices[i] <= budget), None)) is not None]

    def _crafting(self, env: SimEnv, state: CharacterState):
        """Crafting the guide's way ([43], [44]): cut the gems drops brought; hard leather bodies from 28 while hides
        or hard leather are held; flax picked and spun from 10; soft leather, the best item the level allows, while
        hides or leather are held; and below 10, cows killed for their hides, `kill_cows`, Crafting's gathering path
        (Caleb, 2026-11-09)."""
        level, hides = state.level("crafting"), units(state, COWHIDE)
        yield from self._slots_holding(env, state, [path for start, path, uncut in reversed(GEM_CUTS)
                                                    if start <= level and units(state, uncut)])
        if level >= HARD_LEATHER_LEVEL and (units(state, HARD_LEATHER) or hides):
            yield from self._slots_holding(env, state, ["craft_hardleather_body", "tan_hard_leather"])
        if level >= FLAX_SPIN:
            yield from self._slots_holding(env, state, ["pick_flax_spin"])
        if units(state, LEATHER) or hides:
            yield from self._slots_holding(env, state, [*methods_for(SOFT_LEATHER, level), "tan_leather"])
        if level < FLAX_SPIN:
            yield from self._slots_holding(env, state, ["kill_cows"])  # the hides, its bones buried
        yield "skill_crafting_xp1"

    @staticmethod
    def _input_need(state: CharacterState, skill: str) -> tuple[int, int] | None:
        """(the input a skill that loses gp is short of, a load of it), or None: rune essence for Runecrafting (a
        load, 28), thread for leather (a reel's 5 items), and for Herblore the scarcest of its potion's herb, vial and
        secondary (a load, 14)."""
        if skill == "runecrafting" and units(state, RUNE_ESSENCE) < ESSENCE_LOAD:
            return RUNE_ESSENCE, ESSENCE_LOAD
        if skill == "crafting":
            if units(state, THREAD) < THREAD_REORDER and any(units(state, i) for i in (COWHIDE, LEATHER, HARD_LEATHER)):
                return THREAD, THREAD_REORDER
            return None
        if skill == "herblore" and (potion := guide_potion(state.level("herblore"))) is not None:
            herb = grimy_of()[potion.herb]
            made = units(state, potion.unfinished)
            counts = {herb: units(state, herb) + units(state, potion.herb) + made,
                      VIAL_OF_WATER: units(state, VIAL_OF_WATER) + made, potion.secondary: units(state, potion.secondary)}
            scarcest = min(counts, key=lambda i: (counts[i], i))
            if counts[scarcest] < HERB_LOAD and scarcest in gd.ge_prices_2009():
                return scarcest, HERB_LOAD
        return None

    def _consumables(self, state: CharacterState, skill: str):
        """GE buys of what a skill uses up (rune essence, herbs, vials, secondaries, thread), whenever it's due:
        upgrades keep half the coins back for these skills, which lose gp (Caleb, 2026-11-09, replacing OQ-53's
        "after affordable upgrades"). A buy takes as many as the coins allow, up to the item's lot (rune essence and
        herblore's inputs 1,000), so it can spend more than that half. While the coins can't cover a load, flax pays
        for it (_short, OQ-59 (b))."""
        if (need := self._input_need(state, skill)) is not None and not self._short(state, skill):
            yield f"buy_ge_{need[0]}"

    def _flax_ready(self, state: CharacterState, skill: str) -> bool:
        """Enough flax held (carried, noted or banked) to pay for the skill's inputs and the two fares a GE trip costs."""
        if not self._short(state, skill):
            return False
        prices = gd.ge_prices_2009()
        return units(state, FLAX) * prices[FLAX] >= self._funds_needed(state, skill) - state.coins() + FLAX_FARES

    def _funds_needed(self, state: CharacterState, skill: str) -> int:
        """What the skill's short input costs: for its stint (Caleb, 2026-11-09: the money-maker carries through the
        stint), the units the XP to the stint's goal level takes, or at least a load."""
        need = self._input_need(state, skill)
        if need is None:
            return 0
        item, load = need
        units_needed = load
        if self.stint is not None and self.stint[0] == skill and (per := self._xp_per_unit(state, skill)) > 0:
            xp_left = XP_FOR_LEVEL[self.stint[1]] - state.xp[SKILL_INDEX[skill]]
            units_needed = max(load, int(np.ceil(xp_left / per)) - units(state, item))
        return gd.ge_prices_2009().get(item, 0) * units_needed

    @staticmethod
    def _xp_per_unit(state: CharacterState, skill: str) -> float:
        """XP an input unit gives: a rune essence its rune's XP, a Herblore input its potion's finishing XP."""
        if skill == "runecrafting":
            rune = methods_for(RUNECRAFTING, state.level("runecrafting"))[0][0].removeprefix("rc_")
            from rlscape.gamedata import runecrafting as rcd  # imported here: the guide needs it only for this
            return rcd.runes()[rune].experience if rune in rcd.runes() else 0.0
        if skill == "herblore" and (potion := guide_potion(state.level("herblore"))) is not None:
            return potion.experience
        return 0.0

    def _short(self, state: CharacterState, skill: str) -> bool:
        """The skill's short input costs more than the coins held (Caleb, 2026-11-09, OQ-59 (b): then the guide picks
        flax by Seers' Village and sells it, 90 gp each, in full: it's picked to sell, not loot to keep half of)."""
        return self._input_need(state, skill) is not None and self._funds_needed(state, skill) > state.coins()

    @staticmethod
    def _kit_banked(state: CharacterState, skill: str) -> bool:
        """A deposit banked what the class fires (arrows, runes), and a withdrawal would make a kit: for ranged,
        arrows banked and a bow held anywhere; for magic, banked runes of the guide's spell and enough held anywhere
        for a cast."""
        if skill == "ranged":
            bows = [w for w, r in gd.ranged_weapons().items() if r.ammo_slot != WEAPON]
            return any(state.bank.get(a, 0) for a in ARROWS) and any(held(state, b) for b in bows)
        runes = guide_spell(state.level("magic")).runes
        return any(state.bank.get(r, 0) for r in runes) and all(held(state, r) >= n for r, n in runes.items())

    @staticmethod
    def _process_carried(state: CharacterState, skill: str):
        """A processing skill's options that use what the inventory holds (no bank trip)."""
        if skill in PROCESSING:
            yield PROCESSING[skill]
        elif skill == "smithing":
            for metal in smithing_metals(state.level("smithing")):
                yield from (f"smith_{metal}", f"smelt_{metal}")

    @staticmethod
    def _slots_holding(env: SimEnv, state: CharacterState, paths: list[str]):
        """The skilling slots that hold these paths now, in the paths' order."""
        for path in paths:
            if (slot := slot_holding(env.options, state, path)) is not None:
                yield slot

    @staticmethod
    def _food(state: CharacterState) -> list[tuple[int, int]]:
        """(item, pieces) for the food in the inventory."""
        return [(item, state.inventory[item]) for _, item in foods_held(state)]

    def _produce(self, item: int) -> bool:
        """Produce the guide sells from its inventory: vocabulary items that are neither gear nor kept when banking
        (tools, food, ammunition, runes), so it never sells what it bought to use, nor bones (for Prayer), nor what
        Crafting, Herblore and Runecrafting use (found 2026-11-09: it sold its air talisman to fund an upgrade). Their
        products (bowstrings, leather, cut gems, potions) are sold."""
        definition = gd.items().get(item)
        return (item in self.vocabulary and not kept_on_deposit(item) and item not in kept_for_prayer()
                and item not in kept_for_skills()
                and (definition is None or definition.equipment_slot is None))

    def _carried_for_sale(self, state: CharacterState) -> dict[int, int]:
        """Vocabulary item -> units carried to sell: its produce, and any banknotes (bank_withdraw_for_sale's), while
        under half of the item obtained has been sold (_for_sale)."""
        unnoted, out = gd.unnoted_ids(), {}
        for item, amount in state.inventory.items():
            real = unnoted.get(item, item)
            if real in self.vocabulary and (real != item or self._produce(item)) and self._produce(real) \
                    and self._for_sale(state, real):
                out[real] = out.get(real, 0) + amount
        return out

    def _for_sale(self, state: CharacterState, item: int) -> bool:
        """Half of the loot is sold and half kept for processing (Caleb, 2026-11-09): an item's stack is sold only
        while less than half of what's been obtained of it (sold, and held anywhere) has been. A sale sells the whole
        stack carried, so the half holds over the episode, not to the unit."""
        return self.sold[item] < (self.sold[item] + units(state, item)) / 2

    def _banked_for_sale(self, state: CharacterState, prices: dict[int, int]) -> int:
        """The value bank_withdraw_for_sale would bring out that the guide would sell: the stacks it takes (the most
        valuable first, a slot each, rlscape.sim.buying), for sale (_produce, _for_sale)."""
        notes, taken = gd.noted_ids(), []
        slots = state.free_slots()
        for item in BankWithdrawForSale.produce(state):
            if notes.get(item, item) in state.inventory:
                taken.append(item)
            elif slots > 0:
                taken.append(item)
                slots -= 1
        return sum(prices.get(i, 0) * state.bank[i] for i in taken if self._produce(i) and self._for_sale(state, i))

    def _count_sale(self, state: CharacterState, option_id: str) -> None:
        """A GE sale of an item sells all of it carried, banknotes included: count those units as sold."""
        item = option_id.removeprefix("sell_ge_")
        if option_id.startswith("sell_ge_") and item.isdigit():
            note = gd.noted_ids().get(int(item))
            self.sold[int(item)] += state.inventory.get(int(item), 0) + (state.inventory.get(note, 0) if note else 0)

    @staticmethod
    def _method(state: CharacterState, skill: str) -> str:
        """The guide's method for a gathering skill at the character's level: a path id (rlscape.sim.skilling)."""
        if skill == "woodcutting":
            return woodcutting_method(state.level("woodcutting"))
        return mining_method(state) if skill == "mining" else fishing_method(state)

    @staticmethod
    def _scarce_rune(state: CharacterState) -> int | None:
        """The rune that limits casts of the guide's spell, if fewer than RUNE_REORDER casts are held."""
        spell = guide_spell(state.level("magic"))
        casts = {rune: held(state, rune) // amount for rune, amount in spell.runes.items()}
        rune = min(casts, key=casts.get)
        return rune if casts[rune] < RUNE_REORDER else None

    def _skill_chains(self, state: CharacterState, skill: str) -> list[tuple[int, ...]]:
        """A skill's own buys, each a chain of tiers, worst first: its tool, and what it uses up."""
        chains: list[tuple[int, ...]] = [{"woodcutting": AXES, "mining": PICKAXES}.get(skill, ())]
        if skill == "fishing" and state.level("fishing") >= 20:
            chains += [(FLY_ROD,)] + ([(FEATHERS,)] if state.inventory.get(FEATHERS, 0) < FEATHER_REORDER else [])
        if skill == "ranged":
            chains += [SHORTBOWS] + ([(IRON_ARROWS,)] if sum(held(state, a) for a in ARROWS)
                                     < ARROW_REORDER else [])
        if skill == "magic" and (rune := self._scarce_rune(state)) is not None:
            chains += [(rune,)]
        if skill == "smithing":
            chains += [(HAMMER,)]
        if skill == "crafting":  # the tools of what it holds: a needle for leather, a chisel for gems
            if any(units(state, i) for i in (COWHIDE, LEATHER, HARD_LEATHER)) and not units(state, NEEDLE):
                chains += [(NEEDLE,)]
            if any(units(state, uncut) for *_, uncut in GEM_CUTS) and not units(state, CHISEL):
                chains += [(CHISEL,)]
        if skill == "runecrafting":  # the method's talisman, once (a talisman has no upgrade check)
            talisman = methods_for(RUNECRAFTING, state.level("runecrafting"))[0][1]
            if not units(state, talisman):
                chains += [(talisman,)]
        return [chain for chain in chains if chain]

    def _upgrades(self, state: CharacterState, skill: str) -> list[list[int]]:
        """The GE buys the guides call for now, by role in priority order (the skill's own, the scimitar, then
        armour): each role's usable upgrades, best tier first."""
        chains = [*self._skill_chains(state, skill), SCIMITARS, *(ARMOUR[piece::4] for piece in range(4))]
        roles = [[i for i in reversed(chain) if usable(state, i) and is_upgrade(state, i)] for chain in chains]
        return [tiers for tiers in roles if tiers]

    def _fights(self, env: SimEnv, state: CharacterState, skill: str):
        """Fights for a skill: a melee stat in its own style, ranged, or magic. The slots holding a monster from the
        guide's band for the skill's level first (melee and ranged), then the top XP slot."""
        combat_class = "melee" if skill in COMBAT else skill
        bands = MELEE_BANDS if skill in COMBAT else RANGED_BANDS if skill == "ranged" else ()
        band = next((names for top, names in bands if state.level(skill) <= top), set())
        slots = next(o.slots for o in env.options if o.family == "combat")
        matching = [i for i in range(2 * K) if (c := slots.candidate(state, combat_class, i)) is not None
                    and c.entry.npc.name.lower() in band]
        style = f"_{STYLE[skill]}" if skill in COMBAT else ""
        for index in [*matching, 0]:
            yield f"fight_{combat_class}_{'xp' if index < K else 'gp'}{index % K + 1}{style}"
