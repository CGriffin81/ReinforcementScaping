"""Validate travel: fresh trips on the server and in the sim (the walks' overheads were fitted on other trips).

For each trip, the sim plans the fastest way (rlscape.sim.movement.route) for a character set up as the trip says
(levels and items; every quest the server has is complete, as on spawn), and times it (route_ticks). The server
runner sets up the same character, takes the same transports the same way a player does (rlscape.bridge.travel) and
times the whole trip a tick at a time. Two sets:
"fit", whose transports' times were set from these runs (rlscape.gamedata.transports), and "check", trips none of
those times came from: other walks, spells, tablets, jewellery, a charter and a ship. Entrana isn't checked yet (its
monks' conversation).

Usage, with the server running (worldprops/rl.conf):
    uv run python scripts/validate_travel.py [--trips name ...]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rlscape.bridge.client import BridgeClient, run_suffix
from rlscape.bridge.travel import go
from rlscape.routes import surface
from rlscape.sim.movement import route, route_ticks
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import COINS, CharacterState

REPO = Path(__file__).resolve().parent.parent
GATE = 0.20  # env contract §7


@dataclass(frozen=True)
class Trip:
    name: str
    start: tuple[int, int, int]
    end: tuple[int, int, int]
    items: tuple[tuple[int, int], ...] = ()
    levels: tuple[tuple[str, int], ...] = ()
    expect: tuple[str, ...] = field(default=())  # the transports the sim should choose (checked, not forced)


TRIPS = (
    Trip("walk Varrock west bank to Falador east bank", (3185, 3436, 0), (3013, 3355, 0)),
    Trip("walk Draynor bank to Port Sarim docks", (3092, 3245, 0), (3028, 3218, 0)),
    Trip("walk Edgeville bank to Barbarian Village", (3094, 3491, 0), (3082, 3420, 0)),
    Trip("walk Al Kharid bank to its mine", (3270, 3167, 0), (3300, 3300, 0)),
    Trip("walk over the ditch into the Wilderness", (3094, 3491, 0), (3094, 3540, 0)),
    Trip("home teleport from Varrock", (3212, 3428, 0), (3222, 3218, 0), expect=("home",)),
    Trip("Varrock teleport spell", (3222, 3218, 0), (3210, 3434, 0), items=((563, 1), (556, 3), (554, 1)),
         levels=(("magic", 25),), expect=("spell:varrock",)),
    Trip("Varrock tablet", (3222, 3218, 0), (3210, 3434, 0), items=((8007, 1),), expect=("tablet:varrock_teleport",)),
    Trip("glory to Karamja", (2965, 3378, 0), (2915, 3152, 0), items=((1712, 1),),
         expect=("jewellery:amulet_of_glory:karamja",)),
    Trip("games necklace to Burthorpe", (3222, 3218, 0), (2899, 3555, 0), items=((3853, 1),),
         expect=("jewellery:games_necklace:burthorpe games room",)),
    Trip("ship Port Sarim to Musa Point", (3029, 3217, 0), (2915, 3152, 0), items=((COINS, 30),),
         expect=("ship:port_sarim-karamja",)),
    Trip("ship Musa Point to Port Sarim", (2915, 3152, 0), (3013, 3215, 0), items=((COINS, 30),),
         expect=("ship:karamja-port_sarim",)),
    Trip("charter Catherby to Port Sarim", (2797, 3414, 0), (3039, 3193, 0), items=((COINS, 1000),),
         expect=("charter:catherby-port_sarim",)),
    Trip("seed pod to the Grand Tree", (3222, 3218, 0), (2465, 3489, 0), items=((9469, 1),),
         expect=("seed_pod:squash",)),
)
CHECK = (
    Trip("walk Rimmington to Port Sarim", (2957, 3214, 0), (3028, 3218, 0)),
    Trip("walk Falador west bank to Taverley", (2946, 3368, 0), (2894, 3449, 0)),
    Trip("walk Lumbridge to Draynor square", (3222, 3218, 0), (3093, 3250, 0)),
    Trip("Varrock east bank to Al Kharid, paying the toll", (3253, 3420, 0), (3293, 3175, 0),
         items=((995, 20),), expect=("home",)),
    Trip("walk Edgeville to Wilderness level 5", (3094, 3491, 0), (3094, 3560, 0)),
    Trip("home teleport from Falador", (2965, 3385, 0), (3212, 3247, 0), expect=("home",)),
    Trip("Falador teleport spell", (3222, 3218, 0), (2965, 3385, 0), items=((563, 1), (556, 3), (555, 1)),
         levels=(("magic", 37),), expect=("spell:falador",)),
    Trip("Lumbridge tablet", (3212, 3428, 0), (3221, 3225, 0), items=((8008, 1),),
         expect=("tablet:lumbridge_teleport",)),
    Trip("glory to Draynor", (3212, 3428, 0), (3093, 3245, 0), items=((1712, 1),),
         expect=("jewellery:amulet_of_glory:draynor village",)),
    Trip("ring of dueling to the Duel Arena", (3222, 3218, 0), (3315, 3240, 0), items=((2552, 1),),
         expect=("jewellery:ring_of_dueling:al kharid duel arena",)),
    Trip("games necklace to Barbarian Outpost", (3222, 3218, 0), (2522, 3570, 0), items=((3853, 1),),
         expect=("jewellery:games_necklace:barbarian outpost",)),
    Trip("charter Port Sarim to Catherby", (3039, 3193, 0), (2809, 3436, 0), items=((995, 1000),),
         expect=("charter:port_sarim-catherby",)),
    Trip("ship Brimhaven to Ardougne", (2770, 3226, 0), (2662, 3305, 0), items=((995, 30),),
         expect=("ship:brimhaven-ardougne",)),
)
SETS = {"fit": TRIPS, "check": CHECK}


def sim_character(trip: Trip) -> CharacterState:
    state = CharacterState.fresh()
    for item, amount in trip.items:
        state.add(item, amount)
    for skill, lv in trip.levels:
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[lv])
    state.location = trip.start
    return state


def run(client: BridgeClient, world, trip: Trip) -> dict[str, Any]:
    state = sim_character(trip)
    planned = route(state, trip.end)
    sim = route_ticks(state, trip.end)
    used = tuple(t.id for t in planned.transports)
    out: dict[str, Any] = {"trip": trip.name, "sim_ticks": sim, "transports": used, "as_expected": used == trip.expect,
                           "on_foot": planned.on_foot}
    uid = client.spawn()["uid"]
    try:
        if trip.levels:
            client.debug_set_levels(uid, dict(trip.levels))
        for item, amount in trip.items:
            client.debug_give(uid, item, amount)
        client.debug_teleport(uid, *trip.start)
        client.wait(3)
        done = go(client, uid, planned.transports, trip.end, pays_toll=bool(planned.toll))
        out |= {"server_ticks": done.ticks, "arrived": done.arrived, "steps": done.steps}
    finally:
        client.despawn(uid)
    if out.get("arrived"):
        out["sim_over_server"] = round(sim / done.ticks, 3)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--set", choices=sorted(SETS), default="check")
    parser.add_argument("--trips", nargs="*", help="trip names (default: the whole set)")
    parser.add_argument("--tick-ms", type=int, default=50)
    args = parser.parse_args()
    world, rows = surface(), []
    with BridgeClient(timeout=600) as client:
        old_ms = client.ping()["tick_ms"]
        client.set_tick_ms(args.tick_ms)
        try:
            for trip in SETS[args.set]:
                if args.trips and trip.name not in args.trips:
                    continue
                row = run(client, world, trip)
                rows.append(row)
                ratio = row.get("sim_over_server")
                print(f"{trip.name:44s} sim {row['sim_ticks']:5.0f} server {row.get('server_ticks', '-')!s:>5} "
                      f"({ratio if ratio else 'not there'}) {'' if row['as_expected'] else 'UNEXPECTED '}"
                      f"{list(row['transports'])} {[s for s in row.get('steps', []) if s[0].startswith('stuck')]}")
        finally:
            client.set_tick_ms(old_ms)
    ratios = [r["sim_over_server"] for r in rows if r.get("sim_over_server")]
    if ratios:
        inside = sum(abs(r - 1) <= GATE for r in ratios)
        print(f"sim over server {min(ratios):.2f} to {max(ratios):.2f}; {inside} of {len(ratios)} within ±20%")
    out = REPO / "results" / "calibration" / f"travel-validation-{datetime.now():%Y%m%d-%H%M}{run_suffix(args.tick_ms)}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"args": vars(args), "trips": rows}, indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
