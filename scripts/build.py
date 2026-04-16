from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"
DIST = FRONTEND / "dist"
STATIC = BACKEND / "static"


def run(cmd: list[str], cwd: Path) -> None:
    print(f"[build] {' '.join(cmd)} (cwd={cwd})")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> int:
    run(["npm", "run", "build"], FRONTEND)

    if STATIC.exists():
        shutil.rmtree(STATIC)
    shutil.copytree(DIST, STATIC)
    print(f"[build] copied {DIST} -> {STATIC}")
    print("[build] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
