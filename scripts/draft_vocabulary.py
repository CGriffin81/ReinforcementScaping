"""Draft the item vocabulary V by the agreed rule (option catalog §9 and §8) for Caleb to check.

V = what the catalog's activities produce or consume, plus every item the agent can buy, plus the most valuable
common drops from the enemy pool. This script applies that rule to the simulator's own data and writes
`data/vocabulary_draft.csv`: one row per candidate item, with the groups that put it there, its value, and whether
the draft proposes it.

The drop ranking repeats the candidate selection the agent sees (3 monsters by XP/hr and 3 by gp/hr per combat
class) over the calibration bands (env contract §7: levels, gear and quests by band) and 18 hub towns, with loot
mode "all", and records each drop's expected gp/hr in every selected fight. A drop counts as valuable when its best
gp/hr reaches DROP_GP_PER_HOUR somewhere, and as common when it drops in at least MIN_DROP_FIGHTS selected fights.

The `proposed` column is Claude's recommendation, for Caleb to check. Rows the rule names but the recommendation
leaves out say why in `note`:
- rare drops (valuable, but in fewer than MIN_DROP_FIGHTS fights);
- smithed products no other group names: they're made to be sold or alched in bulk, which the misc actions do;
- burnt food: worthless, and drop_misc covers it.

Usage: uv run python scripts/draft_vocabulary.py
"""

from __future__ import annotations

import csv
import sys
import time
from collections import defaultdict
from pathlib import Path

from rlscape.combat import formulas as f
from rlscape.combat.access import Progress
from rlscape.combat.candidates import Character, enemy_pool, select_candidates
from rlscape.combat.rates import Fighter, Plan
from rlscape.gamedata import server as gd
from rlscape.quests import QUEST_SET
from rlscape.sim import fishing, mining, processing, woodcutting
from rlscape.sim.buying import GE_ITEMS, SHOP_ITEMS
from rlscape.sim.economy import WITHDRAW_RECIPES
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import COINS, CharacterState

OUT = Path(__file__).resolve().parents[1] / "data" / "vocabulary_draft.csv"
DROP_GP_PER_HOUR = 1_000  # a drop's best expected gp/hr, in some selected fight, to count as valuable
MIN_DROP_FIGHTS = 20  # selected fights (of up to 3,564 in the sweep) a drop appears in, to count as common
BANDS = (1, 11, 21, 31, 41, 51, 61, 71, 81, 91, 99)

# Gear by band (wear level, item ids), as the candidate sweep for the access table used.
MELEE = [(1, [1321, 1117, 1155, 1075, 1189]), (5, [1325, 1119, 1157, 1069, 1193]), (20, [1329, 1121, 1159, 1071, 1197]),
         (30, [1331, 1123, 1161, 1073, 1199]), (40, [1333, 1127, 1163, 1079, 1201]), (60, [4587, 1127, 1163, 1079, 1201])]
RANGED = [(1, [841, 1129, 882]), (20, [849, 1129, 884]), (30, [853, 1129, 888]), (40, [857, 1135, 1099, 1065, 890]),
          (50, [861, 1135, 1099, 1065, 892])]
MAGIC_GEAR = [579, 577, 1011, 1381]
HUBS = {"Lumbridge": (3222, 3218, 0), "Varrock": (3212, 3424, 0), "Falador": (2965, 3380, 0), "Draynor": (3093, 3244, 0),
        "Al Kharid": (3293, 3174, 0), "Edgeville": (3093, 3493, 0), "Ardougne": (2662, 3305, 0), "Seers": (2726, 3485, 0),
        "Catherby": (2809, 3436, 0), "Yanille": (2606, 3093, 0), "Rellekka": (2643, 3676, 0), "Canifis": (3493, 3488, 0),
        "Port Phasmatys": (3687, 3467, 0), "Shilo": (2852, 2955, 0), "Gnome Stronghold": (2449, 3436, 0),
        "Pollnivneach": (3359, 2974, 0), "Burthorpe": (2899, 3546, 0), "Brimhaven": (2760, 3178, 0)}
# Quests by band (env contract §7), cumulative.
EARLY = ("COOKS_ASSISTANT", "SHEEP_SHEARER", "RUNE_MYSTERIES", "ROMEO_JULIET")
ROUTE = ("COOKS_ASSISTANT", "ROMEO_JULIET", "GOBLIN_DIPLOMACY", "ERNEST_THE_CHICKEN", "PRINCE_ALI_RESCUE",
         "DRUIDIC_RITUAL", "SHEEP_HERDER", "MURDER_MYSTERY", "PIRATES_TREASURE", "DORICS_QUEST")


def quests_for(level: int) -> frozenset[str]:
    if level >= 51:
        return frozenset(QUEST_SET)
    if level >= 31:
        return frozenset(EARLY + ROUTE)
    return frozenset(EARLY) if level >= 11 else frozenset()


def produced_and_consumed() -> dict[int, set[str]]:
    groups: dict[int, set[str]] = defaultdict(set)
    for tree, _ in woodcutting.SITES.values():
        groups[gd.tree_types()[tree].reward].add("gathered")
    for rock, _ in mining.SITES.values():
        groups[gd.rock_types()[rock].reward].add("gathered")
    for gem in mining.GEMS:
        groups[gem].add("gathered")
    for method, _ in fishing.SITES.values():
        for fish in gd.fishing_methods()[method].fish:
            groups[gd.fish_types()[fish].item].add("gathered")
    for tools, inputs in WITHDRAW_RECIPES.values():
        if isinstance(inputs, tuple):
            for item, _ in inputs:
                groups[item].add("consumed")
    for option in processing.processing_options():
        if isinstance(option, processing.Smelt):
            groups[option.bar.product].add("processed")
            for item, _ in option.bar.ores:
                groups[item].add("consumed")
        if isinstance(option, processing.Smith):
            for item in smithed_products(option):
                groups[item].add("smithed")
    return groups


def smithed_products(option: processing.Smith) -> set[int]:
    """Every item the smith option can make: its best item for each level and number of bars held."""
    out = set()
    state = CharacterState.fresh()
    state.progress = Progress(quests_complete=frozenset(QUEST_SET))
    state.inventory = {processing.HAMMER: 1}
    for level in range(1, 100):
        state.xp[SKILL_INDEX["smithing"]] = float(XP_FOR_LEVEL[level])
        for bars in range(1, 28):
            state.inventory[option.bar] = bars
            best = option.best_item(state)
            if best is not None:
                out.add(best.product)
    return out


def bonuses(ids: list[int]) -> tuple[int, ...]:
    return tuple(map(sum, zip(*(gd.items()[i].bonuses for i in ids))))


def gear(table, level):
    return [ids for req, ids in table if req <= level][-1]


def drop_sweep() -> dict[int, tuple[float, int, str]]:
    """Item -> (best expected gp/hr in a selected fight, fights it appears in, where the best was)."""
    pool, values, unnoted = enemy_pool(), gd.item_values(), gd.unnoted_ids()
    best: dict[int, tuple[float, int, str]] = {}
    seen: dict[int, int] = defaultdict(int)
    for level in BANDS:
        hp = max(10, level)
        spell = max((s for s, v in f.SPELLS.items() if v[0] <= level), key=lambda s: f.SPELLS[s][0])
        plans = {"melee": (Fighter(level, level, level, hp, 1, 1, bonuses(gear(MELEE, level)), 4),
                           [Plan("melee", f.AGGRESSIVE), Plan("melee", f.ACCURATE)]),
                 "ranged": (Fighter(1, 1, level, hp, level, 1, bonuses(gear(RANGED, level)), 4),
                            [Plan("ranged", f.RAPID)]),
                 "magic": (Fighter(1, 1, level, hp, 1, level, bonuses(MAGIC_GEAR), 5), [Plan("magic", spell)])}
        levels = tuple((s, level) for s in ("attack", "strength", "defence", "hitpoints", "ranged", "magic"))
        progress = Progress(quests_complete=quests_for(level), levels=levels, coins=100 * level * 7)
        for hub, location in HUBS.items():
            character = Character(location, hp, hp, 180, 13, 1201 if level >= 40 else None, "all", progress)
            for combat_class, candidates in select_candidates(pool, plans, character, 1500, k=3).items():
                for c in candidates:
                    if c.entry.drops is None:
                        continue
                    for item, count in c.entry.drops.expected_items().items():
                        item = unnoted.get(item, item)  # a noted drop banks as the item itself
                        if item == COINS:
                            continue
                        gp = c.kills_per_hour * count * values.get(item, 0)
                        seen[item] += 1
                        if gp > best.get(item, (-1.0, 0, ""))[0]:
                            best[item] = (gp, 0, f"{c.entry.npc.name} ({combat_class}, level {level}, {hub})")
    return {item: (gp, seen[item], where) for item, (gp, _, where) in best.items()}


def main() -> None:
    start = time.time()
    groups = produced_and_consumed()
    for item in (*GE_ITEMS, *SHOP_ITEMS):
        groups[item].add("bought")
    raw_foods = {raw for raw, c in gd.cookables().items() if c.cooked in gd.food_healing()}
    burnt_names = {}  # burnt food is untradeable, so neither export names it
    drops = drop_sweep()
    for item, (gp, _, _) in drops.items():
        if gp >= DROP_GP_PER_HOUR:
            groups[item].add("drop")
    for raw in [i for i in groups if i in raw_foods]:  # what cooking makes from the raw food in V
        cooked = gd.cookables()[raw]
        groups[raw].add("consumed")
        groups[cooked.cooked].add("processed")
        groups[cooked.burnt].add("burnt")
        burnt_names[cooked.burnt] = f"Burnt {gd.items()[cooked.cooked].name.lower()}"
    values, ge, stackable = gd.item_values(), gd.ge_prices_2009(), gd.stackable_items()

    def name_of(item: int) -> str:
        return gd.items()[item].name if item in gd.items() else burnt_names.get(item, str(item))
    rows = []
    for item, why in groups.items():
        note = ""
        if why == {"burnt"}:
            note = "burnt food: worthless, drop_misc covers it"
        elif why == {"smithed"}:
            note = "smithed product: sold or alched in bulk by the misc actions"
        elif why == {"drop"} and drops[item][1] < MIN_DROP_FIGHTS:
            note = f"rare drop: in {drops[item][1]} of the sweep's fights"
        rows.append({
            "item_id": item, "name": name_of(item),
            "groups": ";".join(sorted(why)), "proposed": "no" if note else "yes", "note": note,
            "value": values.get(item, 0), "ge_price_2009": ge.get(item, ""), "stackable": item in stackable,
            "best_drop_gp_per_hour": round(drops[item][0]) if item in drops else "",
            "drop_fights": drops[item][1] if item in drops else "",
            "best_drop_at": drops[item][2] if item in drops else "",
        })
    # near misses: drops under the threshold but worth showing Caleb
    for item, (gp, n, where) in drops.items():
        if item not in groups and gp >= DROP_GP_PER_HOUR / 4:
            rows.append({"item_id": item, "name": name_of(item), "groups": "drop",
                         "proposed": "no", "note": f"drop under {DROP_GP_PER_HOUR} gp/hr",
                         "value": values.get(item, 0), "ge_price_2009": ge.get(item, ""),
                         "stackable": item in stackable, "best_drop_gp_per_hour": round(gp), "drop_fights": n,
                         "best_drop_at": where})
    order = ("gathered", "processed", "smithed", "consumed", "bought", "drop", "burnt")
    rows.sort(key=lambda r: (r["proposed"] != "yes", min(order.index(g) for g in r["groups"].split(";")),
                             r["item_id"]))
    with OUT.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    proposed = [r for r in rows if r["proposed"] == "yes"]
    print(f"{len(proposed)} proposed of {len(rows)} rows -> {OUT} ({time.time() - start:.0f}s)", file=sys.stderr)


if __name__ == "__main__":
    main()
