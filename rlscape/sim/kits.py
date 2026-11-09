"""What each task needs in the inventory (Caleb, 2026-10-30: "deposit all items that are not suitable to the task at
hand").

The task is the last activity the character did. Every gathering, processing and combat option names its task
(`Option.task`), and the engine records it in `state.task` after the option runs. `bank_deposit` keeps the task's kit
in the inventory and banks everything else; worn items stay worn. The withdrawals take kits back out: for gathering
`bank_withdraw_for_<task>` (here), for processing `bank_withdraw_for_<activity>`, for fights
`bank_withdraw_gear_<class>`, and food through `bank_withdraw_food` and the per-tier food withdrawals.

Kits:
- `woodcutting` / `mining`: the best axe / pickaxe the level allows (SkillingTool's priority); woodcutting also
  keeps a tinderbox and a knife, which its chop-and-burn and chop-and-fletch paths use (rlscape.sim.skilling).
- `fletching`: the knife and whatever fletching inputs are carried (logs, bows, bowstrings, shafts, feathers, tips).
- `crafting`: the chisel, needle and thread, and whatever crafting inputs are carried (uncut gems, leathers).
- `herblore`: the pestle and mortar, and whatever herblore inputs are carried (herbs, vials of water, unfinished
  potions, secondaries).
- `runecrafting`: whatever essence and talismans are carried.
- `fishing:<method>`: the method's tool and its bait or feathers.
- `thieving`: food, since failed attempts hurt.
- `processing:<activity>`: its tools and inputs (WITHDRAW_RECIPES); cooking also keeps logs and a tinderbox, for a
  fire where the character stands.
- `combat:<class>`: food; antipoison and antifire doses; the combat potions for the class's skills (rlscape.sim.potions); what
  that class's fight would put on from the inventory (wield_best on a
  copy: weapon, armour, the ranged kit's ammunition); an anti-dragon shield, which fights against dragonfire monsters
  put on, unless the class's weapon is two-handed; and, for magic, runes.
- no task yet: nothing.
"""

from __future__ import annotations

from dataclasses import replace

from rlscape.combat.candidates import DRAGONFIRE_PROTECTION
from rlscape.gamedata import server as gd
from rlscape.sim.equipment import WEAPON, wield_best
from rlscape.sim.health import ANTIPOISON_DOSES
from rlscape.sim.potions import ANTIFIRE, CLASS_SKILLS, DOSE_OF, POTION_DOSES, POTIONS
from rlscape.sim.mining import PICKAXE_PRIORITY
from rlscape.sim.processing import TINDERBOX
from rlscape.sim.state import CharacterState
from rlscape.sim.woodcutting import HATCHET_PRIORITY, best_tool

GATHERING_TOOLS = {"woodcutting": HATCHET_PRIORITY, "mining": PICKAXE_PRIORITY}


def kit(state: CharacterState, task: str | None) -> set[int]:
    """The inventory items the task keeps."""
    if task is None:
        return set()
    kind, _, detail = task.partition(":")
    inventory, food = set(state.inventory), set(gd.food_healing())
    if kind in GATHERING_TOOLS:
        tool = best_tool(state, GATHERING_TOOLS[kind], kind)
        keep = {tool.item} & inventory if tool is not None else set()
        return keep | ({TINDERBOX, gd.KNIFE} & inventory if kind == "woodcutting" else set())  # burn / fletch paths
    if kind == "fishing":
        method = gd.fishing_methods()[detail]
        return {method.tool, *method.bait} & inventory
    if kind == "thieving":
        return inventory & food
    if kind == "fletching":
        from rlscape.sim.fletching import inputs  # imported here: fletching imports economy, which imports this
        return inventory & ({gd.KNIFE} | inputs())
    if kind == "crafting":
        from rlscape.sim.crafting import inputs as craft_inputs  # imported here, as fletching's
        return inventory & craft_inputs()
    if kind == "herblore":
        from rlscape.sim.herblore import inputs as herb_inputs  # imported here, as fletching's
        return inventory & herb_inputs()
    if kind == "runecrafting":
        from rlscape.sim.runecrafting import inputs as rc_inputs  # imported here, as fletching's
        return inventory & rc_inputs()
    if kind == "agility":  # food, for the falls (rlscape.sim.agility eats as thieving does)
        return inventory & food
    if kind == "processing":
        return _processing_kit(state, detail)
    if kind == "combat":
        armed = replace(state, inventory=dict(state.inventory), equipment=dict(state.equipment),
                        worn_amounts=dict(state.worn_amounts))
        wield_best(armed, detail)
        wielded = {i for i in inventory if armed.inventory.get(i, 0) < state.inventory[i]}
        runes = {i for i in inventory if gd.items().get(i) and gd.items()[i].name.lower().endswith(" rune")}
        weapon = armed.equipment.get(WEAPON)
        guards = set() if weapon is not None and gd.items()[weapon].two_handed else inventory & DRAGONFIRE_PROTECTION
        doses = inventory & set(ANTIPOISON_DOSES)
        doses |= {i for i in inventory & POTION_DOSES if POTIONS[DOSE_OF[i][0]][0] in CLASS_SKILLS[detail]}
        doses |= inventory & set(ANTIFIRE)
        return wielded | guards | doses | (inventory & food) | (runes if detail == "magic" else set())
    raise ValueError(f"unknown task {task!r}")


def _processing_kit(state: CharacterState, activity: str) -> set[int]:
    from rlscape.sim.economy import WITHDRAW_RECIPES, _raw_foods  # imported here: economy imports this module

    tools, inputs = WITHDRAW_RECIPES[activity]
    inventory = set(state.inventory)
    if inputs == "raw_food":
        items = set(_raw_foods()) | set(gd.log_types()) | {TINDERBOX}  # a fire where the character stands
    elif inputs == "logs":
        items = set(gd.log_types())
    elif inputs == "bones":
        items = set(gd.bone_experience())
    else:
        items = {item for item, _ in inputs}
    return (set(tools) | items) & inventory
