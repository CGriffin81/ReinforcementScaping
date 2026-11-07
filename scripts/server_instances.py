"""Extra 2009Scape servers beside the usual one, so calibration runs, probes and live tests can run at once (Caleb,
2026-11-06: "run multiple tests at once, where possible").

Instance 1 is worldprops/rl.conf, as ever. Instance n (2 and up) is the same config with its own world: world_id n
(game port 43594 + n), bridge port 43610 + n - 1, and its own Grand Exchange database and server store under
server/Server/data/eco/instance-<n>, which the fork's git ignores. Each world ticks on its own, so one can run at
600 ms while another runs at 50. A client picks an instance with RL_BRIDGE_PORT (rlscape.bridge.client). Each runs
its own copy of the built jar (results/servers/server-<n>.jar), so a rebuild doesn't touch a running one; rerun this
for an instance, stopped, to give it the new build.

Usage:
    uv run python scripts/server_instances.py 2 3        # configs, jar copies, the frozen GE
then, from server/Server, one per instance:
    java -jar <repo>/results/servers/server-2.jar <repo>/results/servers/rl-2.conf
and point anything at it:
    RL_BRIDGE_PORT=43611 uv run python scripts/calibrate.py ...
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from install_ge_db import install

from rlscape.bridge.client import BASE_PORT

REPO = Path(__file__).resolve().parents[1]
RL_CONF = REPO / "server" / "Server" / "worldprops" / "rl.conf"
JAR = REPO / "server" / "Server" / "target" / "server-1.0.0-jar-with-dependencies.jar"
OUT = REPO / "results" / "servers"


def config(instance: int) -> str:
    """rl.conf with the instance's world, bridge port, GE database and server store."""
    text = RL_CONF.read_text(encoding="utf-8")
    eco = f'"@data/eco/instance-{instance}"'
    for key, value in (("world_id", f'"{instance}"'), ("bridge_port", str(BASE_PORT + instance - 1)),
                       ("grand_exchange_data_path", eco), ("eco_data", eco),
                       ("store_path", f'"@data/eco/instance-{instance}/serverstore"')):
        text, n = re.subn(rf"^{key} = .*$", f"{key} = {value}", text, flags=re.M)
        assert n == 1, f"rl.conf has {n} lines for {key}"
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("instances", type=int, nargs="+", help="instance numbers, 2 and up")
    parser.add_argument("--db", type=Path, default=REPO / "data" / "grandexchange_2009_frozen.db")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for n in args.instances:
        if n < 2:
            parser.error("instance 1 is worldprops/rl.conf itself")
        path = OUT / f"rl-{n}.conf"
        path.write_text(config(n), encoding="utf-8")
        install(args.db, n)  # refuses while the instance runs
        jar = OUT / f"server-{n}.jar"
        shutil.copyfile(JAR, jar)
        print(f"instance {n}: java -jar {jar} {path} (bridge {BASE_PORT + n - 1}, game port {43594 + n})")


if __name__ == "__main__":
    main()
