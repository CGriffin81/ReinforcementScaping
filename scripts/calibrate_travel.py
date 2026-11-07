"""Calibrate travel and banking: the trip from each gathering site to its nearest bank, a deposit, and back, on the
server and in the sim.

The server runner walks the planned route as a player clicks it (rlscape.bridge.walker), opens the nearest bank booth,
deposits the inventory (the bank's deposit button, then "Deposit Inventory") and walks back, a tick at a time. The sim
gives the same trips with its walk model (rlscape.sim.movement) and BANKING_TICKS. A fresh character makes each trip
with its starter kit and full run energy.

Usage, with the server running (worldprops/rl.conf):
    uv run python scripts/calibrate_travel.py [--options wc_willow mine_iron ...]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rlscape.bridge.client import BridgeClient, BridgeError
from rlscape.bridge.walker import walk_route
from rlscape.gamedata import server as gd
from rlscape.routes import BLOCKS_TILE, surface
from rlscape.sim.fishing import fishing_options
from rlscape.sim.mining import mining_options
from rlscape.sim.movement import route_ticks
from rlscape.sim.state import CharacterState
from rlscape.sim.woodcutting import woodcutting_options
from rlscape.travel import BANKING_TICKS, travel_ticks

REPO = Path(__file__).resolve().parent.parent
BANK_IFACE, DEPOSIT_BUTTON, OPTIONS_4, DEPOSIT_INVENTORY = 762, 18, 232, 2  # BankInterface; BankDepositDialogue
BANK_TIMEOUT = 20


def sites() -> list[tuple[str, tuple[int, int, int]]]:
    out = [(o.id, o.site.tile) for o in (*woodcutting_options(), *mining_options())]
    return out + [(o.id, o.start) for o in fishing_options()]


def stand_tile(world, tile: tuple[int, int, int]) -> tuple[int, int, int] | None:
    """The nearest tile a character can stand on, from which the site's resource is a step away (a tree's or a
    rock's tile is the object's; a fishing spot's is water)."""
    for r in range(0, 4):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                t = (tile[0] + dx, tile[1] + dy, 0)
                n = world.node(t)
                if max(abs(dx), abs(dy)) == r and n is not None and not world.flags.flat[n] & BLOCKS_TILE                         and world.graph[n].nnz:
                    return t
    return None


def bank_deposit(client: BridgeClient, uid: int) -> tuple[int, bool]:
    """Open the nearest bank booth and deposit the inventory, as a player clicks it: (ticks, done)."""
    ticks, step = 0, [{"cmd": "interact", "uid": uid, "name": "Bank booth", "option": "Use-quickly", "object": True,
                       "packet": True}]
    stage = "open"
    while ticks < BANK_TIMEOUT:
        result = client.schedule([[*step, {"cmd": "state", "uid": uid}]])[0]["results"]
        state, ticks, step = result[-1]["state"], ticks + 1, []
        if stage == "open" and not result[0].get("ok", True):
            return ticks, False  # no booth reachable
        if stage in ("open", "opening") and state["interface"] == BANK_IFACE:
            step, stage = [{"cmd": "interface_button", "uid": uid, "interface": BANK_IFACE, "button": DEPOSIT_BUTTON,
                            "packet": True}], "deposit"
        elif stage == "open":
            stage = "opening"
        elif stage == "deposit" and state["chatbox"] == OPTIONS_4:
            step, stage = [{"cmd": "dialogue_button", "uid": uid, "interface": OPTIONS_4, "button": DEPOSIT_INVENTORY,
                            "packet": True}], "depositing"
        elif stage == "depositing" and not state["inventory"]:
            return ticks, True
    return ticks, False


def trip(client: BridgeClient, world, name: str, site: tuple[int, int, int]) -> dict[str, Any]:
    """The sim's nearest bank is by straight line; here it's the nearest by the planned walk, among the surface's
    booth banks (the sim's choice is compared in the output)."""
    start = stand_tile(world, site)
    banks = [b for b in gd.banks() if b.plane == 0 and "Grand Exchange" not in b.name]  # stairs and GE: to come
    bank = min(banks, key=lambda b: world.steps(start, (b.x, b.y, 0)) if start else travel_ticks(site, (b.x, b.y, 0)))
    bank_tile = (bank.x, bank.y, 0)
    state = CharacterState.fresh()
    state.location = site
    sim_out = route_ticks(state, bank_tile)
    out: dict[str, Any] = {"option": name, "site": site, "start": start, "bank": bank.name, "bank_tile": bank_tile,
                           "planned_steps": world.steps(start, bank_tile) if start else None,
                           "sim_walk": sim_out, "sim_banking": BANKING_TICKS}
    if start is None:
        return out | {"error": "no stand tile"}
    uid = client.spawn()["uid"]
    try:
        client.debug_teleport(uid, *start)
        client.wait(2)
        there = walk_route(client, uid, world, bank_tile)
        out |= {"server_walk": there.ticks, "arrived": there.arrived, "clicks": there.clicks, "doors": there.doors,
                "replans": there.replans}
        if there.arrived:
            out["server_banking"], out["deposited"] = bank_deposit(client, uid)
            back = walk_route(client, uid, world, start)
            out |= {"server_back": back.ticks, "back_arrived": back.arrived}
            here = client.state(uid)["location"]
            out["end"] = (here["x"], here["y"], here["z"])
    except BridgeError as e:
        out["error"] = str(e)
    finally:
        client.despawn(uid)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--options", nargs="*", help="option ids (default: every gathering site)")
    parser.add_argument("--tick-ms", type=int, default=50)
    args = parser.parse_args()
    world = surface()
    rows = []
    with BridgeClient(timeout=600) as client:
        old_ms = client.ping()["tick_ms"]
        client.set_tick_ms(args.tick_ms)
        try:
            for name, site in sites():
                if args.options and name not in args.options:
                    continue
                row = trip(client, world, name, site)
                rows.append(row)
                ratio = row["sim_walk"] / row["server_walk"] if row.get("server_walk") else float("nan")
                print(f"{name:20s} -> {row['bank'][:24]:24s} steps {row['planned_steps']!s:>6} "
                      f"walk server {row.get('server_walk', '-')!s:>4} sim {row['sim_walk']!s:>4} ({ratio:.2f}) "
                      f"banking server {row.get('server_banking', '-')!s:>3} sim {BANKING_TICKS} "
                      f"back {row.get('server_back', '-')!s:>4} doors {row.get('doors', '-')} "
                      f"{'' if row.get('deposited', True) else 'NOT DEPOSITED'} {row.get('error', '')}")
        finally:
            client.set_tick_ms(old_ms)
    out = REPO / "results" / "calibration" / f"travel-{datetime.now():%Y%m%d-%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"args": vars(args), "trips": rows}, indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
