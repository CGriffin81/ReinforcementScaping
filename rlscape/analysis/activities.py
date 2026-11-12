"""The activities the analysis groups options into (OQ-76, Caleb, 2026-11-11): each gathering skill, each combat
style, smithing, cooking, firemaking, prayer, selling, buying, alchemy and banking, 20 in all, and `other` for the
rest (dropping an item, taking the knife, reclaiming a gravestone, and the loot settings).

An option's activity is read from its catalog id alone (docs/option-catalog.md), so an evaluation trace, which names
options by id, groups the same way as a training run's decision log. A skill slot counts for its skill whatever path
fills it: chop-and-burn and chop-and-fletch (woodcutting's fletch slot, sim v1.2) are woodcutting, as the catalog
files them.
"""

from __future__ import annotations

GATHERING = ("woodcutting", "fishing", "mining", "thieving", "fletching", "crafting", "agility", "herblore",
             "runecrafting")
COMBAT = ("melee", "ranged", "magic")
PROCESSING = {"smelt": "smithing", "smith": "smithing", "cook": "cooking", "burn": "firemaking", "bury": "prayer"}
ACTIVITIES = (*GATHERING, *COMBAT, "smithing", "cooking", "firemaking", "prayer", "selling", "buying", "alchemy",
              "banking")
OTHER = "other"


def activity(option: str) -> str:
    """The activity of an option, by its catalog id (`skill_mining_xp1`, `fight_melee_gp2_defensive`, `sell_ge_440`,
    `bank_withdraw_for_cook_fish`, ...)."""
    head, _, rest = option.partition("_")
    if head == "skill":
        skill = rest.split("_")[0]
        return skill if skill in GATHERING else OTHER
    if head == "fight":
        style = rest.split("_")[0]
        return style if style in COMBAT else OTHER
    if head in PROCESSING:
        return PROCESSING[head]
    if head == "sell":
        return "selling"
    if head == "buy":
        return "buying"
    if head in ("high", "low") and rest.startswith("alch"):
        return "alchemy"
    if head == "bank":
        return "banking"
    return OTHER
