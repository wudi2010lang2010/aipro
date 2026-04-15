"""
scripts/start.py
一键启动脚本

用法：
    python scripts/start.py           # 正常启动
    python scripts/start.py --dev     # 开发模式（热重载）
    python scripts/start.py --no-browser  # 不自动打开浏览器
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# ─── 路径计算 ──────────────────────────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"


# ─── 工具函数 ──────────────────────────────────────────────────────────────────


def check_env() -> bool:
    """检查 .env 文件是否存在，不存在则提示用户创建。"""
    env_file = BACKEND_DIR / ".env"
    example_file = BACKEND_DIR / ".env.example"

    if not env_file.exists():
        print("=" * 60)
        print("  首次启动：未找到配置文件 backend/.env")
        print("=" * 60)
        if example_file.exists():
            print(f"\n  请复制模板文件并填入配置：")
            print(f"    copy backend\\.env.example backend\\.env")
            print(f"\n  然后编辑 backend\\.env 填入：")
            print(f"    TUSHARE_TOKEN=你的tushare token")
            print(f"    GEMINI_API_KEY=你的Gemini API Key（可选）")
            print(f"    WECOM_WEBHOOK_URL=企业微信Webhook（可选）")
        else:
            print(f"\n  请在 backend/ 目录下创建 .env 文件")
            print(f"  参考文档：STOCK-ANALYZER-PROJECT-PLAN.md")
        print()
        return False
    return True


def check_dependencies() -> bool:
    """检查关键依赖是否已安装。"""
    missing = []

    deps = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("sqlalchemy", "SQLAlchemy"),
        ("loguru", "loguru"),
        ("dotenv", "python-dotenv"),
        ("apscheduler", "APScheduler"),
    ]

    for module, package in deps:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if missing:
        print("=" * 60)
        print("  缺少必要依赖，请先安装：")
        print("=" * 60)
        print(f"\n  cd backend")
        print(f"  pip install -r requirements.txt")
        print(f"\n  缺少的包：{', '.join(missing)}")
        print()
        return False

    return True


def wait_for_server(host: str, port: int, timeout: int = 15) -> bool:
    """
    轮询等待 FastAPI 服务启动完成。
    每 0.5 秒检查一次，超时返回 False。
    """
    import socket

    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
    return False


# ─── 主函数 ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Stock AI Analyzer 一键启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python scripts/start.py               正常启动
  python scripts/start.py --dev         开发模式（代码修改后自动重载）
  python scripts/start.py --no-browser  不自动打开浏览器
  python scripts/start.py --port 9000   指定端口
        """,
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="开发模式，启用热重载（代码修改后自动重启）",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="不自动打开浏览器",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="绑定地址，默认 127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="监听端口，默认 8000",
    )
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════╗")
    print("║        Stock AI Analyzer  v1.0.0             ║")
    print("║        AI 辅助 A 股短线趋势交易分析           ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    # ── 前置检查 ──────────────────────────────────────────────────────────────
    if not check_dependencies():
        sys.exit(1)

    env_ok = check_env()
    if not env_ok:
        # 配置文件缺失，询问是否继续（方便首次体验）
        answer = input("  是否仍要继续启动（不会加载 tushare）？[y/N] ").strip().lower()
        if answer != "y":
            sys.exit(0)
        print()

    # ── 构建 uvicorn 启动命令 ──────────────────────────────────────────────────
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--log-level",
        "warning",  # uvicorn 自身日志用 warning，详细日志由 loguru 处理
    ]

    if args.dev:
        cmd.append("--reload")
        print("  [开发模式] 热重载已启用，修改代码后服务自动重启")
        print()

    url = f"http://{args.host}:{args.port}"

    print(f"  后端目录：{BACKEND_DIR}")
    print(f"  服务地址：{url}")
    print(f"  API 文档：{url}/docs")
    print()
    print("  正在启动服务...")
    print("  按 Ctrl+C 退出")
    print()

    # ── 启动后端进程 ──────────────────────────────────────────────────────────
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR)  # 确保 backend/ 在 Python 路径中

    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(BACKEND_DIR),
            env=env,
            # 不捕获 stdout/stderr，让日志直接输出到终端
        )
    except FileNotFoundError:
        print(f"  错误：找不到 Python 解释器 {sys.executable}")
        sys.exit(1)

    # ── 等待服务就绪 ──────────────────────────────────────────────────────────
    print("  等待服务启动", end="", flush=True)
    ready = False
    for _ in range(20):  # 最多等 10 秒
        time.sleep(0.5)
        print(".", end="", flush=True)
        try:
            import socket

            with socket.create_connection((args.host, args.port), timeout=1):
                ready = True
                break
        except (ConnectionRefusedError, OSError):
            pass

    print()

    if not ready:
        print()
        print("  ⚠ 服务启动超时，请查看上方日志排查问题")
        print("  常见原因：")
        print("    1. 端口被占用（换一个 --port）")
        print("    2. requirements.txt 依赖未安装完整")
        print("    3. backend/.env 配置有误")
    else:
        print(f"  ✓ 服务已就绪：{url}")

        if not args.no_browser:
            print(f"  正在打开浏览器...")
            time.sleep(0.5)
            webbrowser.open(url)
        print()

    # ── 等待进程结束 ──────────────────────────────────────────────────────────
    try:
        process.wait()
    except KeyboardInterrupt:
        print()
        print("  正在关闭服务...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("  已退出")
    except Exception as exc:
        print(f"  异常退出: {exc}")
        process.kill()

    print()


if __name__ == "__main__":
    main()
