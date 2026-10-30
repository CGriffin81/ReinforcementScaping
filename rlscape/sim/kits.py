"""What each task needs in the inventory (Caleb, 2026-10-30: "deposit all items that are not suitable to the task at
hand").

The task is the last activity the character did. Every gathering, processing and combat option names its task
(`Option.task`), and the engine records it in `state.task` after the option runs. `bank_deposit` keeps the task's kit
in the inventory and banks everything else; worn items stay worn. The withdrawals take kits back out: for gathering
`bank_withdraw_for_<task>` (here), for processing `bank_withdraw_for_<activity>`, for fights
`bank_withdraw_gear_<class>`, and food through `bank_withdraw_food` and the per-tier food withdrawals.

Kits:
- `woodcutting` / `mining`: the best axe / pickaxe the level allows (SkillingTool's priority).
- `fishing:<method>`: the method's tool and its bait or feathers.
- `thieving`: food, since failed attempts hurt.
- `processing:<activity>`: its tools and inputs (WITHDRAW_RECIPES); cooking also keeps logs and a tinderbox, for a
  fire where the character stands.
- `combat:<class>`: food; what that class's fight would put on from the inventory (wield_best on a copy: weapon,
  armour, the ranged kit's ammunition); and, for magic, runes.
- no task yet: nothing.
"""

from __future__ import annotations

from dataclasses import replace

from rlscape.gamedata import server as gd
from rlscape.sim.equipment import wield_best
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
        return {tool.item} & inventory if tool is not None else set()
    if kind == "fishing":
        method = gd.fishing_methods()[detail]
        return {method.tool, *method.bait} & inventory
    if kind == "thieving":
        return inventory & food
    if kind == "processing":
        return _processing_kit(state, detail)
    if kind == "combat":
        armed = replace(state, inventory=dict(state.inventory), equipment=dict(state.equipment),
                        worn_amounts=dict(state.worn_amounts))
        wield_best(armed, detail)
        wielded = {i for i in inventory if armed.inventory.get(i, 0) < state.inventory[i]}
        runes = {i for i in inventory if gd.items().get(i) and gd.items()[i].name.lower().endswith(" rune")}
        return wielded | (inventory & food) | (runes if detail == "magic" else set())
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
