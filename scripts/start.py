from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"


def wait_port(host: str, port: int, timeout: int = 20) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Start Stock AI Analyzer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if args.dev:
        cmd.append("--reload")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)

    print(f"[start] backend: {BACKEND}")
    print(f"[start] url: http://{args.host}:{args.port}")
    proc = subprocess.Popen(cmd, cwd=str(BACKEND), env=env)

    try:
        if wait_port(args.host, args.port, timeout=20):
            print("[start] server ready")
            if not args.no_browser:
                webbrowser.open(f"http://{args.host}:{args.port}")
        else:
            print("[start] warning: server not ready within timeout")
        proc.wait()
    except KeyboardInterrupt:
        print("[start] stopping...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
