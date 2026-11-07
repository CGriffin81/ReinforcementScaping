"""Check the sim's drop tables item by item against the server (env contract §7; Caleb, 2026-11-06, OQ-20 (a)).

The gp/hr of a few short runs can't settle the gate where rare drops make up the loot, so the tables are checked on
their own: a strong character kills about 200 of a monster on the server, and every drop is counted.
- Counting: the character's own ground items within PROBE_RADIUS, each counted once by its key (the bridge's
  `ground_items`), however often it comes into view. Only its kills drop its own items; it doesn't retaliate, so
  only the monsters it clicks die: the probed one nearest, or one of them attacking it (a single-combat area refuses
  any other while one attacks). Nothing is picked up.
- Protection (Caleb, 2026-11-06): the bridge flicks its protection prayers (`flick`), and against dragons it wears
  an anti-dragon shield and drinks an antifire potion whenever the last runs out, so the breath does nothing. It eats
  under 50 hitpoints, and its food is topped up (setup only: the probe counts drops, not how long food lasts).
- Kills: its style XP over 4 per hitpoint of the monster, counting completed kills only.
- The sim: rlscape.sim.combat.roll_drops rolls the same number of kills SIM_REPLICATES times. An item fits when the
  server's count is within the sim's central 99%. Items the sim never drops (the rare drop table, gems, herbs, seeds:
  the sub-tables gd.SPECIAL_DROP_SLOTS leaves out) are listed with their value per kill, which the sim's gp/hr lacks.

Setup only (calibration): debug_set_levels, debug_give and debug_teleport, never exposed to the agent.

Usage, with the server running (worldprops/rl.conf):
    uv run python scripts/probe_drops.py [--npcs 178 89 2685 941] [--kills 200] [--tick-ms 50]
    uv run python scripts/probe_drops.py --rejudge results/calibration/drops-<stamp>.json   (no server)
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from rlscape.bridge.client import BridgeClient, BridgeError, run_suffix
from rlscape.combat.candidates import ANTI_DRAGON_SHIELD, DRAGONFIRE_NPCS, enemy_pool
from rlscape.gamedata import server as gd
from rlscape.sim.combat import roll_drops
from rlscape.sim.state import SPAWN
from rlscape.travel import travel_ticks

REPO = Path(__file__).resolve().parents[1]
# Black Knight, unicorn, hobgoblin: the loot runs' monsters (2026-11-05); green dragon, with the anti-dragon shield
DEFAULT_NPCS = (178, 89, 2685, 941)
PROBE_RADIUS = 20
SIM_REPLICATES = 2000
FIT = (0.005, 0.995)
MAX_TICKS_PER_KILL = 120  # give up on a monster that takes longer than this a kill, on average
# DeathTask waits out the monster's death animation, 30 ticks at most (6 if it has none), before the drop: a 12-tick
# wait missed the last kill's drop at big monsters (199 of 200 always-drops, 2026-11-07)
DROP_WAIT_TICKS = 31
NO_KILL_TICKS = 2_000  # give up on a site with no kill by then
MAX_SITES = 3  # sites to try for a monster before giving it up
SHARK = 385
ANTIFIRE_4 = 2452
ANTIFIRE_EVERY = 580  # ticks between doses: a dose lasts 600 (Consumables.ANTIFIRE)
FOOD_LOW, FOOD_TOP_UP = 5, 10
# A strong melee kit: rune scimitar, full helm, platebody, platelegs, kiteshield; an anti-dragon shield for dragons
GEAR = (1333, 1163, 1127, 1079, 1201)
STYLE_SKILLS = ("attack", "strength", "defence")


def xp(state: dict[str, Any], skill: str) -> float:
    return next(s["xp"] for s in state["skills"] if s["name"].lower() == skill)


def setup(client: BridgeClient, npc: int, site: tuple[int, int, int]) -> int:
    uid = client.spawn()["uid"]
    client.debug_set_levels(uid, {s: 99 for s in (*STYLE_SKILLS, "hitpoints", "prayer")})
    for item in {i["id"] for i in client.state(uid)["inventory"]}:
        client.item_option(uid, item, "Drop")  # no starter kit: a combat inventory
    client.wait(2)
    gear = [ANTI_DRAGON_SHIELD if (item == 1201 and npc in DRAGONFIRE_NPCS) else item for item in GEAR]
    for item in gear:
        client.debug_give(uid, item, 1)
        for option in ("Wield", "Wear"):
            try:
                client.item_option(uid, item, option)
                break
            except BridgeError:
                continue
        client.wait(1)
    client.debug_give(uid, SHARK, 15)
    if npc in DRAGONFIRE_NPCS:
        client.debug_give(uid, ANTIFIRE_4, 3)
    client.set_retaliate(uid, False)  # only what it clicks dies, so every drop of its own is from a probed kill
    client.flick(uid)
    client.debug_teleport(uid, *site)
    client.wait(3)
    return uid


def same_monster(npc: gd.Npc) -> list[int]:
    """The NPC ids that are this monster: its name, hitpoints and drop table (green dragons come as 941 and 4677 to
    4680), so the kill count by XP and the drop table hold for any of them."""
    npcs, tables = gd.npcs(), gd.drop_tables()
    return sorted(i for i, other in npcs.items() if other.name == npc.name and other.hitpoints == npc.hitpoints
                  and tables.get(i) == tables.get(npc.id))


def own_items(client: BridgeClient, uid: int, seen: dict[Any, tuple[int, int]]) -> None:
    """Count the character's own ground items in view, each once by its key."""
    for item in client.ground_items(uid, PROBE_RADIUS):
        if item["own"]:
            key = item.get("key") or (item["id"], item["location"]["x"], item["location"]["y"], item["amount"])
            seen.setdefault(key, (item["id"], item["amount"]))


def server_probe(client: BridgeClient, npc: gd.Npc, site: tuple[int, int, int], kills: int) -> dict[str, Any]:
    uid = setup(client, npc.id, site)
    ids = same_monster(npc)
    attack = {"uid": uid, "name": npc.name, "option": "Attack", "object": False, "ids": ids, "packet": True}
    try:
        start = client.state(uid)
        base = sum(xp(start, s) for s in STYLE_SKILLS)
        seen: dict[Any, tuple[int, int]] = {}  # ground item key -> (id, amount)
        first_tick = client.wait(0)
        ticks, killed, reported, died, antifire_at = 0, 0, 0, False, None
        antifire = [2458, 2456, 2454, ANTIFIRE_4]  # the emptiest first
        while killed < kills and ticks < MAX_TICKS_PER_KILL * kills:
            state = client.state(uid)
            # completed kills: a monster still being fought has given part of its XP
            killed = int((sum(xp(state, s) for s in STYLE_SKILLS) - base) / (4 * npc.hitpoints) + 1e-6)
            here = state["location"]
            if abs(here["x"] - site[0]) + abs(here["y"] - site[1]) > 60 or state["hitpoints"] <= 0:
                print(f"  {npc.name}: died or left the site after {killed} kills", flush=True)
                died = True  # stop before counting: a death drops the character's gear as its own items
                break
            own_items(client, uid, seen)
            if killed == 0 and ticks > NO_KILL_TICKS:
                print(f"  {npc.name}: no kill in {ticks} ticks", flush=True)
                break
            food = sum(i["amount"] for i in state["inventory"] if i["id"] == SHARK)
            if food < FOOD_LOW:
                client.debug_give(uid, SHARK, FOOD_TOP_UP)
            dose = next((d for d in antifire if any(i["id"] == d for i in state["inventory"])), None)
            if npc.id in DRAGONFIRE_NPCS and dose and (antifire_at is None or ticks - antifire_at >= ANTIFIRE_EVERY):
                client.request("item_option", uid=uid, item=dose, option="Drink", packet=True)
                antifire_at = ticks
            elif state["hitpoints"] < 50 and food:
                client.request("item_option", uid=uid, item=SHARK, option="Eat", packet=True)
            elif state["target"] is None and not state["busy"] and killed < kills:  # none after the last: its drop
                # would come in the wait for the last kill's (51 always-drops for 50 cows, 2026-11-07)
                fighting_it = [a for a in state["attackers"] if a["id"] in ids]
                try:
                    if fighting_it:  # the one attacking it: a single-combat area allows no other
                        client.request("interact", **{**attack, "index": fighting_it[0]["index"]})
                    else:
                        client.request("interact", **attack)
                except BridgeError:
                    pass  # none in reach: wait for a respawn
            ticks = client.wait(1) - first_tick  # game ticks: the loop can lag the world at a fast tick
            if killed >= reported + 25:
                reported = killed
                print(f"  {npc.name}: {killed} kills in {ticks} ticks", flush=True)
        if not died:
            client.wait(DROP_WAIT_TICKS)  # the last kill's death animation and drop
            own_items(client, uid, seen)
        counts: Counter[int] = Counter()
        for item_id, amount in seen.values():
            counts[gd.unnoted_ids().get(item_id, item_id)] += amount
        return {"kills": killed, "ticks": ticks, "counts": dict(counts), "died": died, "ids": ids,
                "keyed": all(not isinstance(k, tuple) for k in seen)}
    finally:
        client.despawn(uid)


def sim_counts(table: gd.DropTable, kills: int, replicates: int, rng: np.random.Generator) -> dict[int, np.ndarray]:
    """Per item, its total count in each of `replicates` runs of `kills` kills."""
    out: dict[int, np.ndarray] = {}
    for r in range(replicates):
        for _ in range(kills):
            for item, amount in roll_drops(table, rng):
                item = gd.unnoted_ids().get(item, item)
                out.setdefault(item, np.zeros(replicates))[r] += amount
    return out


def judge(server: dict[int, int], sim: dict[int, np.ndarray], kills: int) -> dict[str, Any]:
    values, rows = gd.item_values(), []
    for item in sorted(set(server) | set(sim)):
        count, dist = server.get(item, 0), sim.get(item)
        if dist is None:
            rows.append({"item": item, "name": gd.items()[item].name if item in gd.items() else str(item),
                         "server": count, "sim_mean": 0.0, "fits": False, "sim_never": True,
                         "gp_per_kill": count * values.get(item, 0) / max(kills, 1)})
            continue
        low, high = np.quantile(dist, FIT)
        rows.append({"item": item, "name": gd.items()[item].name if item in gd.items() else str(item),
                     "server": count, "sim_mean": float(dist.mean()), "sim_low": float(low), "sim_high": float(high),
                     "fits": bool(low <= count <= high), "sim_never": False})
    missing_gp = sum(r["gp_per_kill"] for r in rows if r.get("sim_never"))
    return {"items": rows, "fits": sum(r["fits"] for r in rows if not r["sim_never"]),
            "checked": sum(not r["sim_never"] for r in rows), "sim_never_gp_per_kill": missing_gp}


def rejudge(path: Path, pool: dict, rng: np.random.Generator) -> None:
    """An earlier probe's server counts, judged by the sim's drop sampler as it is now; saved beside it."""
    old = json.loads(path.read_text())
    monsters = []
    for m in old["monsters"]:
        counts = {int(k): v for k, v in m["counts"].items()}
        verdict = judge(counts, sim_counts(pool[m["npc"]].drops, m["kills"], SIM_REPLICATES, rng), m["kills"])
        monsters.append({**m, **verdict})
        print(f'{m["name"]}: {verdict["fits"]} of {verdict["checked"]} items fit; '
              f'{verdict["sim_never_gp_per_kill"]:.0f} gp a kill the sim never drops')
    out = path.resolve().with_name(path.stem + "-rejudged.json")
    out.write_text(json.dumps({**old, "rejudged": True, "monsters": monsters}, indent=1))
    print(f"saved {out.relative_to(REPO)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--npcs", type=int, nargs="+", default=list(DEFAULT_NPCS))
    parser.add_argument("--kills", type=int, default=200)
    parser.add_argument("--tick-ms", type=int, default=50)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--rejudge", type=Path, help="no server: judge an earlier file's server counts by the sim now")
    args = parser.parse_args()
    pool = {e.npc.id: e for e in enemy_pool()}
    rng, results = np.random.default_rng(args.seed), []
    if args.rejudge:
        return rejudge(args.rejudge, pool, rng)
    out = REPO / "results" / "calibration" / f"drops-{datetime.now():%Y%m%d-%H%M}{run_suffix(args.tick_ms)}.json"
    with BridgeClient() as client:
        old_ms = client.ping()["tick_ms"]
        client.set_tick_ms(args.tick_ms)
        try:
            for npc_id in args.npcs:
                entry = pool[npc_id]
                # the sites with the most of them first, then the nearest Lumbridge; one where no kill comes in
                # NO_KILL_TICKS (the server refusing the attack, as west of the Fishing Guild) gives way to the next
                sites = sorted((s for s in entry.sites if travel_ticks(SPAWN, s.spawn) < float("inf")),
                               key=lambda s: (-s.spawns, travel_ticks(SPAWN, s.spawn)))
                failed = []
                for candidate in sites[:MAX_SITES]:
                    site = candidate.spawn
                    server = server_probe(client, entry.npc, tuple(site), args.kills)
                    if server["kills"] or server["died"]:
                        break
                    failed.append(list(site))
                server["sites_without_a_kill"] = failed
                verdict = judge(server["counts"], sim_counts(entry.drops, server["kills"], SIM_REPLICATES, rng),
                                server["kills"])
                results.append({"npc": npc_id, "name": entry.npc.name, "site": list(site), **server, **verdict})
                print(f'{entry.npc.name}: {server["kills"]} kills in {server["ticks"]} ticks; '
                      f'{verdict["fits"]} of {verdict["checked"]} items fit; '
                      f'{verdict["sim_never_gp_per_kill"]:.0f} gp a kill the sim never drops', flush=True)
                out.write_text(json.dumps({"args": vars(args), "monsters": results}, indent=1))  # after each
        finally:
            client.set_tick_ms(old_ms)
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
