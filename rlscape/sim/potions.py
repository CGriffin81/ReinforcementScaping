"""Combat potions (Caleb, 2026-11-06: "combat inventories should hold as many potions as it takes to boost stats
while training, if the agent opts to use potions"), from the server's Consumables and SkillEffect.

- A dose raises a skill to its level plus int(base + bonus x level); a dose while still boosted tops it back up to
  that, no higher (Skills.updateLevel's maximum), so doses don't stack.
- The boost falls by 1 every 101 ticks, on SkillRestore's cycle, the one hitpoint regeneration runs on
  (rlscape.sim.health.regenerate). Death restores every stat, so it clears the boosts.
- A dose leaves the next in its slot, the last an empty vial (Potion.consume).

The rule fights follow (an agent choice, reversible): before each kill, for each skill the class fights with, drink
when its boost is at or under half a dose's and a potion for it is carried; the super first, and of each the emptiest
potion first. So a boost stays between a half and a full dose's, and a 15-minute fight takes a few doses a skill. The
agent opts in by buying the potions; the deposit keeps them with the fighting kit.
"""

from __future__ import annotations

from rlscape.gamedata import server as gd
from rlscape.sim.health import ANTIPOISON, DRINK_TICKS, SUPER_ANTIPOISON, VIAL
from rlscape.sim.state import CharacterState

# name -> (skill, base, bonus, the potion's ids from 4 doses to 1), Consumables' constants
POTIONS = {
    "super_attack": ("attack", 5, 0.15, (2436, 145, 147, 149)),
    "super_strength": ("strength", 5, 0.15, (2440, 157, 159, 161)),
    "super_defence": ("defence", 5, 0.15, (2442, 163, 165, 167)),
    "attack": ("attack", 3, 0.1, (2428, 121, 123, 125)),
    "strength": ("strength", 3, 0.1, (113, 115, 117, 119)),
    "defence": ("defence", 3, 0.1, (2432, 133, 135, 137)),
    "ranging": ("ranged", 4, 0.1, (2444, 169, 171, 173)),
    "magic": ("magic", 4, 0.0, (3040, 3042, 3044, 3046)),
}
# Antifire (Consumables.ANTIFIRE: AddTimerEffect("dragonfire:immunity", 600), DragonFireImmunity): a dose keeps a
# dragon's breath to nothing behind the anti-dragon shield (rlscape.combat.rates.breath_max) for 600 ticks, and
# another restarts it. The rule (an agent choice): drink before a kill of a dragon when the immunity has run out,
# while a dose is carried.
ANTIFIRE = (2452, 2454, 2456, 2458)
ANTIFIRE_TICKS = 600
CLASS_SKILLS = {"melee": ("attack", "strength", "defence"), "ranged": ("ranged", "defence"),
                "magic": ("magic", "defence")}
DOSE_OF = {item: (name, len(ids) - i) for name, (_, _, _, ids) in POTIONS.items() for i, item in enumerate(ids)}
POTION_DOSES = frozenset(DOSE_OF)
FOUR_DOSES = tuple(ids[0] for _, _, _, ids in POTIONS.values())


# Every potion the sim drinks, by the observation's name: its doses, 4 to 1. Only the four-dose potions are in V
# (Caleb, 2026-11-06, OQ-25); the lower doses are misc, but stay consumable: drunk as any dose, kept by deposits,
# and never sold, alched or dropped by the misc actions (economy.kept_on_deposit). The observation counts the doses of
# each (rlscape.envs.encoding).
ALL_POTIONS = {**{name: ids for name, (*_, ids) in POTIONS.items()}, "super_antipoison": SUPER_ANTIPOISON,
               "antipoison": ANTIPOISON, "antifire": ANTIFIRE}
DOSES = {item: (name, len(ids) - i) for name, ids in ALL_POTIONS.items() for i, item in enumerate(ids)}


def doses_held(container: dict[int, int], name: str) -> int:
    """The doses of a potion in a container (banknotes count as their potions)."""
    unnoted = gd.unnoted_ids()
    return sum(DOSES[unnoted.get(i, i)][1] * n for i, n in container.items()
               if unnoted.get(i, i) in DOSES and DOSES[unnoted.get(i, i)][0] == name)


def dose_boost(name: str, level: int) -> int:
    """SkillEffect.activate: int(base + bonus x level)."""
    _, base, bonus, _ = POTIONS[name]
    return int(base + bonus * level)


def drink(state: CharacterState, item: int) -> None:
    """Drink one dose of the potion `item`: the boost to a full dose's, the next dose (or a vial) in its slot."""
    name, _ = DOSE_OF[item]
    skill, _, _, ids = POTIONS[name]
    state.take(item)
    following = ids.index(item) + 1
    state.add(ids[following] if following < len(ids) else VIAL)
    state.boosts[skill] = max(state.boosts.get(skill, 0), dose_boost(name, state.level(skill)))


def drink_antifire(state: CharacterState, now: int) -> int:
    """Drink an antifire dose, the emptiest potion first, if the immunity has run out at tick `now` and one is
    carried; the ticks it takes."""
    if now < state.antifire_until:
        return 0
    item = next((i for i in ANTIFIRE[::-1] if state.inventory.get(i)), None)
    if item is None:
        return 0
    state.take(item)
    following = ANTIFIRE.index(item) + 1
    state.add(ANTIFIRE[following] if following < len(ANTIFIRE) else VIAL)
    state.antifire_until = now + ANTIFIRE_TICKS
    return DRINK_TICKS


def antifire_cover(state: CharacterState, ticks: float) -> float:
    """The share of the next `ticks` the antifire carried (and any immunity running) keeps the breath off."""
    if ticks <= 0:
        return 1.0
    covered = max(state.antifire_until - state.tick, 0)
    covered += sum(ANTIFIRE_TICKS * (len(ANTIFIRE) - ANTIFIRE.index(i)) * n
                   for i, n in state.inventory.items() if i in ANTIFIRE)
    return min(covered / ticks, 1.0)


def drink_boosts(state: CharacterState, combat_class: str) -> int:
    """The fights' rule: drink for each of the class's skills whose boost is at or under half a dose's, from the best
    potion carried for it; the ticks it takes."""
    ticks = 0
    for skill in CLASS_SKILLS[combat_class]:
        carried = [(dose_boost(name, state.level(skill)), -doses, item) for item in state.inventory
                   if item in DOSE_OF for name, doses in [DOSE_OF[item]] if POTIONS[name][0] == skill]
        if not carried:
            continue
        full, _, item = max(carried)  # the strongest potion, and of it the emptiest
        if state.boosts.get(skill, 0) <= full / 2:
            drink(state, item)
            ticks += DRINK_TICKS
    return ticks

