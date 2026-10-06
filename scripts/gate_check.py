"""Week-1 decision-gate checks G1 (world speed) and G2 (state readout and action injection).

Needs the forked server running with the bridge enabled:
    java -jar target/server-1.0.0-jar-with-dependencies.jar worldprops/rl.conf   (from server/Server)

Usage:
    uv run python scripts/gate_check.py [--port 43610] [--chop-ticks 600]
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from rlscape.bridge import DEFAULT_PORT, BridgeClient

WOODCUTTING = 8
LOGS = 1511


def measure_tick_rate(client: BridgeClient, tick_ms: int, wall_seconds: float = 6.0) -> dict:
    """Set the tick length, then time a fixed number of ticks against the wall clock."""
    client.set_tick_ms(tick_ms)
    client.wait(3)  # let the new interval take effect
    ticks = max(10, int(wall_seconds * 1000 / tick_ms))
    start_tick = client.wait(0)
    start = time.perf_counter()
    end_tick = client.wait(ticks)
    elapsed = time.perf_counter() - start
    achieved = elapsed * 1000 / (end_tick - start_tick)
    return {
        "requested_ms": tick_ms,
        "ticks": end_tick - start_tick,
        "achieved_ms_per_tick": round(achieved, 2),
        "speedup_vs_600ms": round(600 / achieved, 1),
    }


def g1_world_speed(client: BridgeClient) -> list[dict]:
    return [measure_tick_rate(client, ms) for ms in (600, 120, 60, 30, 15)]


def skill(state: dict, skill_id: int) -> dict:
    return next(s for s in state["skills"] if s["id"] == skill_id)


def count(items: list[dict], item_id: int) -> int:
    return sum(i["amount"] for i in items if i["id"] == item_id)


def g2_control(client: BridgeClient, chop_ticks: int, tick_ms: int) -> dict:
    """Spawn a fresh character, read its state, and chop trees through authentic interactions."""
    client.set_tick_ms(tick_ms)
    fresh = client.spawn()
    uid = fresh["uid"]
    try:
        total_level = sum(s["level"] for s in fresh["skills"])
        start_tick = client.wait(0)
        interactions = 0
        while client.wait(0) - start_tick < chop_ticks:
            state = client.state(uid)
            if not state["busy"] and not state["moving"]:
                client.interact(uid, "Tree", "Chop down")
                interactions += 1
            client.wait(10)
        final = client.state(uid)
        xp = skill(final, WOODCUTTING)["xp"]
        logs = count(final["inventory"], LOGS)
        return {
            "fresh_character": {
                "combat_level": fresh["combat_level"],
                "total_level": total_level,
                "hitpoints": fresh["hitpoints"],
                "location": fresh["location"],
                "inventory": [f'{i["name"]} x{i["amount"]}' for i in fresh["inventory"]],
                "bank": [f'{i["name"]} x{i["amount"]}' for i in fresh["bank"]],
            },
            "chop_ticks": chop_ticks,
            "interactions_sent": interactions,
            "woodcutting_xp": xp,
            "woodcutting_level": skill(final, WOODCUTTING)["level"],
            "logs_in_inventory": logs,
            # Normal trees give 25 xp per log; anything else means xp is being capped or modified.
            "xp_per_log": round(xp / logs, 2) if logs else None,
            "final_location": final["location"],
        }
    finally:
        client.despawn(uid)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--chop-ticks", type=int, default=600, help="game ticks to spend chopping in G2")
    parser.add_argument("--chop-tick-ms", type=int, default=30, help="tick length used while chopping")
    args = parser.parse_args()

    with BridgeClient(port=args.port) as client:
        result = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "server": client.ping(),
            "g1_world_speed": g1_world_speed(client),
            "g2_control": g2_control(client, args.chop_ticks, args.chop_tick_ms),
        }
        client.set_tick_ms(600)

    out_dir = Path("results/gates")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"gate_check_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
