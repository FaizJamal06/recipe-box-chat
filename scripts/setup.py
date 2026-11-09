"""Create .venv, install requirements, and npm ci if the frontend exists. Cross-platform replacement for a multi-line shell target."""
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"


def main() -> None:
    """Idempotent: safe to re-run."""
    if not VENV.exists():
        venv.create(VENV, with_pip=True)
    py = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    subprocess.run([str(py), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], check=True)
    if (ROOT / "frontend" / "package.json").exists():
        subprocess.run(["npm", "ci"], cwd=ROOT / "frontend", check=True, shell=sys.platform == "win32")


if __name__ == "__main__":
    main()
