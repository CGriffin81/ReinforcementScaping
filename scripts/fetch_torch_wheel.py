"""Download PyTorch's CUDA wheel into wheels/, where pyproject.toml's local index has uv install torch from (Caleb,
2026-11-08: CUDA torch for the RTX 3050; the driver supports CUDA 13.4).

Why not uv's own download: on this connection a long TLS download breaks partway (rustls: "cannot decrypt peer's
message"; curl: SEC_E_DECRYPT_FAILURE), and uv starts the 1.9 GB file again each time. This resumes where it broke
(an HTTP Range request) and checks the file against PyTorch's published SHA-256.

Usage, before `uv sync` on a fresh checkout:
    uv run --no-project python scripts/fetch_torch_wheel.py
"""

from __future__ import annotations

import hashlib
import time
import urllib.error
import urllib.request
from pathlib import Path

WHEEL = "torch-2.14.1+cu130-cp312-cp312-win_amd64.whl"
URL = "https://download.pytorch.org/whl/cu130/torch-2.14.1%2Bcu130-cp312-cp312-win_amd64.whl"
SHA256 = "0a09031e93632d14ef49553acd6211ece3ae9cdc0969a369b8c24e3cc4d15be9"  # download.pytorch.org/whl/cu130/torch/
OUT = Path(__file__).resolve().parents[1] / "wheels" / WHEEL
ATTEMPTS = 50
CHUNK = 1 << 20


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    if OUT.exists() and sha256(OUT) == SHA256:
        print(f"{OUT.name}: already here, SHA-256 checked")
        return
    for attempt in range(1, ATTEMPTS + 1):
        have = OUT.stat().st_size if OUT.exists() else 0
        request = urllib.request.Request(URL, headers={"Range": f"bytes={have}-"} if have else {})
        try:
            with urllib.request.urlopen(request, timeout=120) as response, OUT.open("ab" if have else "wb") as f:
                if have and response.status != 206:  # the server ignored the range: start again
                    f.seek(0)
                    f.truncate()
                for block in iter(lambda: response.read(CHUNK), b""):
                    f.write(block)
            break
        except (urllib.error.URLError, OSError) as error:
            print(f"attempt {attempt}: stopped at {OUT.stat().st_size if OUT.exists() else 0:,} bytes ({error}); "
                  "resuming")
            time.sleep(3)
    else:
        raise SystemExit(f"gave up after {ATTEMPTS} attempts")
    if sha256(OUT) != SHA256:
        OUT.unlink()
        raise SystemExit("the SHA-256 doesn't match: deleted; run this again")
    print(f"{OUT.name}: downloaded, SHA-256 checked")


if __name__ == "__main__":
    main()
