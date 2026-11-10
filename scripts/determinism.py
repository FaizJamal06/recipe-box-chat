"""Build the DB twice in parallel processes with different string-hash seeds and compare fingerprints.

Run: python scripts/determinism.py [--other PATH]   (~6 min; the first build replaces data/recipes.db)
Exit 1 if any fingerprint number differs.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app.db import connect, fingerprint  # noqa: E402
from app.ingest import DB  # noqa: E402

BUILD = "import sys; from pathlib import Path; from app.ingest import build, RAW, SOURCES; " \
        "build(Path(sys.argv[1]), {s: RAW / f for s, f in SOURCES.items()})"


def main() -> None:
    """Run both builds, print each build's last log line and both fingerprints side by side."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--other", type=Path, default=ROOT / "data" / "recipes_check.db")
    other = ap.parse_args().other
    env = lambda seed: {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT / "backend")}
    procs = [subprocess.Popen([sys.executable, "-c", BUILD, str(p)], env=env(seed), text=True,
                              stdout=subprocess.PIPE) for p, seed in ((DB, "1"), (other, "2"))]
    for p in procs:
        print(p.communicate()[0].strip().splitlines()[-1])
    fps = []
    for path in (DB, other):
        con = connect(path)
        fps.append(fingerprint(con))
        con.close()
    for k in fps[0]:
        print(f"{'same' if fps[0][k] == fps[1][k] else 'DIFF'}  {k}: {fps[0][k]} | {fps[1][k]}")
    other.unlink()
    sys.exit(0 if fps[0] == fps[1] else 1)


if __name__ == "__main__":
    main()
