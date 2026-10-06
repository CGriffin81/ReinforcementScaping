"""Install a GE database into the server, e.g. at the start of a real-server episode.

The server must be stopped: it holds the database open while running. The database it replaces is kept
next to it as grandexchange.db.bak.<timestamp>.

    uv run python scripts/install_ge_db.py [--db data/grandexchange_2009_frozen.db]
"""

from __future__ import annotations

import argparse
import shutil
import socket
from datetime import datetime
from pathlib import Path

from rlscape.bridge import DEFAULT_PORT

TARGET = Path("server/Server/data/eco/grandexchange.db")


def server_running() -> bool:
    try:
        socket.create_connection(("127.0.0.1", DEFAULT_PORT), timeout=1).close()
        return True
    except OSError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, default=Path("data/grandexchange_2009_frozen.db"))
    args = parser.parse_args()
    if server_running():
        raise SystemExit("the server is running; stop it before replacing its GE database")
    if TARGET.exists():
        backup = TARGET.with_name(f"{TARGET.name}.bak.{datetime.now():%Y%m%d_%H%M%S}")
        TARGET.rename(backup)
        print(f"kept the previous database as {backup}")
    shutil.copyfile(args.db, TARGET)
    print(f"installed {args.db} -> {TARGET}")


if __name__ == "__main__":
    main()
