"""Install a GE database into the server, e.g. at the start of a real-server episode.

The server must be stopped: it holds the database open while running. The database it replaces is kept
next to it as grandexchange.db.bak.<timestamp>. `--instance n` installs into an extra server's own
(scripts/server_instances.py).

    uv run python scripts/install_ge_db.py [--db data/grandexchange_2009_frozen.db] [--instance 1]
"""

from __future__ import annotations

import argparse
import shutil
import socket
from datetime import datetime
from pathlib import Path

from rlscape.bridge.client import BASE_PORT

ECO = Path("server/Server/data/eco")


def target(instance: int) -> Path:
    """Instance 1's GE database (worldprops/rl.conf), or an extra instance's (data/eco/instance-<n>)."""
    return ECO / "grandexchange.db" if instance == 1 else ECO / f"instance-{instance}" / "grandexchange.db"


def server_running(instance: int = 1) -> bool:
    try:
        socket.create_connection(("127.0.0.1", BASE_PORT + instance - 1), timeout=1).close()
        return True
    except OSError:
        return False


def install(db: Path, instance: int = 1) -> None:
    if server_running(instance):
        raise SystemExit(f"server instance {instance} is running; stop it before replacing its GE database")
    path = target(instance)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(f"{path.name}.bak.{datetime.now():%Y%m%d_%H%M%S}")
        path.rename(backup)
        print(f"kept the previous database as {backup}")
    shutil.copyfile(db, path)
    print(f"installed {db} -> {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, default=Path("data/grandexchange_2009_frozen.db"))
    parser.add_argument("--instance", type=int, default=1)
    args = parser.parse_args()
    install(args.db, args.instance)


if __name__ == "__main__":
    main()
