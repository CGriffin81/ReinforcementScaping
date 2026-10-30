"""The stage's quest set (option catalog §10, Caleb, 2026-10-27): the 32-quest-point route, Waterfall Quest, the nine
former backups and Dragon Slayer. Names are the server's Quests enum (content/data/Quests.kt); quest points come
from each quest class's constructor, as the catalog lists them.

The observation encodes each quest's stage and the quest points (env contract §3); sim v1's quest options will use
the same list.
"""

from __future__ import annotations

QUEST_SET = {
    # the 32-quest-point route
    "COOKS_ASSISTANT": 1, "ROMEO_JULIET": 5, "GOBLIN_DIPLOMACY": 5, "ERNEST_THE_CHICKEN": 4, "PRINCE_ALI_RESCUE": 3,
    "DRUIDIC_RITUAL": 4, "SHEEP_HERDER": 4, "MURDER_MYSTERY": 3, "PIRATES_TREASURE": 2, "DORICS_QUEST": 1,
    # for XP
    "WATERFALL_QUEST": 1,
    # the former backups
    "WITCHS_POTION": 1, "IMP_CATCHER": 1, "THE_RESTLESS_GHOST": 1, "RUNE_MYSTERIES": 1, "SHEEP_SHEARER": 1,
    "MONKS_FRIEND": 1, "BLACK_KNIGHTS_FORTRESS": 3, "VAMPIRE_SLAYER": 3, "DEMON_SLAYER": 3,
    # the goal
    "DRAGON_SLAYER": 2,
}
DRAGON_SLAYER_QUEST_POINTS = 32  # quest points needed to start Dragon Slayer; the observation's scale
