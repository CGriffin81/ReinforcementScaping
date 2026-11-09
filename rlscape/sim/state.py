"""The simulated character: skills, hitpoints, inventory, bank, equipment, location and progress.

Inventory rules follow the game: 28 slots; a stackable item (coins, runes, arrows, banknotes, summoning charms) takes
one slot however many there are, every other item one slot each. Net worth uses `data/prices_v2.csv` (env contract §4).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from rlscape.combat.access import Progress, relevant, start_progress
from rlscape.combat.neighbours import TOLERANCE_TICKS  # noqa: F401 (Region.TOLERANCE_TICKS, in game ticks)
from rlscape.gamedata import server as gd
from rlscape.sim.skills import SKILL_INDEX, SKILLS, XP_FOR_LEVEL, capped_total_xp, level_for_xp, skill_measure

INVENTORY_SLOTS = 28
COINS = 995
SPAWN = (3233, 3230, 0)  # where the bridge's `spawn` places a character leaving Tutorial Island
FRESH_HITPOINTS_LEVEL = 10


@dataclass
class CharacterState:
    tick: int
    xp: list[float]  # per skill, in SKILLS order
    hp: float
    inventory: dict[int, int]
    bank: dict[int, int]
    equipment: dict[int, int] = field(default_factory=dict)  # equipment slot -> item id
    # equipment slot -> amount, for worn stacks (arrows or bolts in the quiver, a thrown weapon); others hold one
    worn_amounts: dict[int, int] = field(default_factory=dict)
    location: tuple[int, int, int] = SPAWN
    loot_mode: str = "valuable"
    progress: Progress = field(default_factory=start_progress)  # every quest complete (start_progress)
    regen_counter: int = 0  # ticks into the current hitpoint-regeneration cycle (rlscape.sim.health)
    dropped: dict[int, int] = field(default_factory=dict)  # dropped during the current step (the engine reports it)
    gravestone: object | None = None  # rlscape.sim.combat.Gravestone after a death outside the Wilderness
    # (shop, item) -> (amount, tick it was set), for shop stock the character has moved (rlscape.sim.shops)
    shop_stock: dict[tuple[int, int], tuple[int, int]] = field(default_factory=dict)
    task: str | None = None  # the last activity's task (rlscape.sim.kits): what bank_deposit keeps
    run_energy: float = 100.0  # % (rlscape.sim.energy); a fresh character has it full
    energy_clock: int = 0  # ticks into the current step that run energy accounts for (rlscape.sim.energy)
    region_since: int = 0  # the tick it entered its map region (64 x 64 tiles): aggression tolerance counts from it
    home_teleport_ready: int = 0  # the tick from which the home teleport can be cast again (rlscape.sim.transport)
    poison_severity: int = 0  # the poison on the character (rlscape.sim.health); 0 when there's none
    poison_clock: int = 0  # ticks into its 30-tick cycle
    poison_immune_until: int = 0  # the tick an antipoison's immunity runs out (rlscape.sim.health)
    boosts: dict[str, int] = field(default_factory=dict)  # skill -> a potion's boost, still on (rlscape.sim.potions)
    antifire_until: int = 0  # the tick an antifire potion's immunity runs out (rlscape.sim.potions)
    # items left on the current reel of thread (LeatherCrafting.decayThread's saved "threadCharges"; rlscape.sim.crafting)
    thread_charges: int = 5
    skulled_until: int = 0  # the tick the skull the Abyss's teleport gives runs out (rlscape.sim.abyss; 2,000 ticks)
    # essence pouch kind -> (its capacity now, the essence left before its next decay), for the kinds not as new; and
    # the essence a trip has put in them, (essence item, amount) (rlscape.sim.pouches)
    pouches: dict[int, tuple[int, int]] = field(default_factory=dict)
    pouch_essence: dict[int, tuple[int, int]] = field(default_factory=dict)

    @classmethod
    def fresh(cls) -> CharacterState:
        """A level-3 character exactly as it leaves Tutorial Island, with every quest the server has complete (env
        contract §1)."""
        xp = [0.0] * len(SKILLS)
        xp[SKILL_INDEX["hitpoints"]] = float(XP_FOR_LEVEL[FRESH_HITPOINTS_LEVEL])
        inventory, bank = gd.starter_kit()
        state = cls(tick=0, xp=xp, hp=FRESH_HITPOINTS_LEVEL, inventory={}, bank=dict(bank))
        for item, amount in inventory:
            state.add(item, amount)
        return state

    def level(self, skill: str) -> int:
        return level_for_xp(self.xp[SKILL_INDEX[skill]])

    def boosted(self, skill: str) -> int:
        """The level a potion has raised it to, as fights use it; the level itself without one."""
        return self.level(skill) + self.boosts.get(skill, 0)

    def max_hp(self) -> int:
        return self.level("hitpoints")

    def combat_level(self) -> int:
        """Skills.calculateCombatLevel: a quarter of Defence, Hitpoints and half Prayer, plus 0.325 of the best of
        Attack + Strength, Ranged x 1.5 and Magic x 1.5 (each halved and floored before the x 3); summoning adds
        nothing below 8."""
        lv = self.level
        base = 0.25 * (lv("defence") + lv("hitpoints") + (lv("prayer") // 2))
        style = max(lv("attack") + lv("strength"), lv("ranged") // 2 * 3, lv("magic") // 2 * 3)
        return int(base + 0.325 * style)

    def total_level(self) -> int:
        return sum(level_for_xp(x) for x in self.xp)

    def skill_measure(self) -> float:
        return skill_measure(self.xp)

    def total_xp(self) -> float:
        """Reported total XP: each skill's XP up to level 99's."""
        return capped_total_xp(self.xp)

    def slots_used(self) -> int:
        stackable = gd.stackable_items()
        return sum(1 if item in stackable else amount for item, amount in self.inventory.items())

    def free_slots(self) -> int:
        return INVENTORY_SLOTS - self.slots_used()

    def add(self, item: int, amount: int = 1) -> int:
        """Add up to `amount` to the inventory, as far as the free slots allow; returns how many were added."""
        if item in gd.stackable_items():
            added = amount if (item in self.inventory or self.free_slots() > 0) else 0
        else:
            added = min(amount, self.free_slots())
        if added:
            self.inventory[item] = self.inventory.get(item, 0) + added
        return added

    def take(self, item: int, amount: int = 1, container: dict[int, int] | None = None) -> None:
        """Remove `amount` of an item from the inventory (or another container); the caller checks it's there."""
        container = self.inventory if container is None else container
        container[item] -= amount
        if container[item] == 0:
            del container[item]

    def worn(self, slot: int) -> int:
        """How many of the item in an equipment slot are worn; 0 for an empty slot."""
        return self.worn_amounts.get(slot, 1) if slot in self.equipment else 0

    def use_worn(self, slot: int, amount: int) -> None:
        """Use up `amount` from a worn stack; the slot empties when it runs out."""
        left = self.worn(slot) - amount
        if left > 0:
            self.worn_amounts[slot] = left
        else:
            del self.equipment[slot]
            self.worn_amounts.pop(slot, None)

    def holds(self, item: int) -> bool:
        """In the inventory or worn (SkillingTool.checkTool looks in both)."""
        return self.inventory.get(item, 0) > 0 or item in self.equipment.values()

    def coins(self) -> int:
        return self.inventory.get(COINS, 0) + self.bank.get(COINS, 0)

    def access_progress(self) -> Progress:
        """`progress` holds the quests; access also looks at the items held (inventory, bank or worn), levels and
        coins, taken from the state as it is now, then reduced to what the access table checks."""
        held = frozenset(self.inventory) | frozenset(self.bank) | frozenset(self.equipment.values())
        levels = tuple((skill, level) for skill in SKILLS if (level := self.level(skill)) > 1)
        return relevant(replace(self.progress, items_held=held, levels=levels, coins=self.coins()))

    def net_worth(self) -> float:
        values = gd.item_values()
        worth = 0.0
        for container in (self.inventory, self.bank):
            for item, amount in container.items():
                worth += amount * (1 if item == COINS else values.get(item, 0))
        worth += sum(self.worn(slot) * values.get(item, 0) for slot, item in self.equipment.items())
        return worth
