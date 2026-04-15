"""
scripts/wait_server.py
等待 HTTP 服务就绪的辅助脚本，供 start.bat 调用

用法：
    python wait_server.py <url> [timeout_seconds]

退出码：
    0 = 服务就绪
    1 = 超时或失败
"""

import sys
import time
import urllib.error
import urllib.request


def wait_for_server(url: str, timeout: int = 30) -> bool:
    print(f"  等待服务就绪: {url}")
    for i in range(timeout):
        try:
            urllib.request.urlopen(url, timeout=2)
            print(f"  [OK] 服务已就绪！({i + 1}s)")
            return True
        except Exception:
            print(f"  等待中... {i + 1}/{timeout}s", end="\r")
            time.sleep(1)
    print(f"\n  [超时] {timeout}s 内服务未就绪")
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python wait_server.py <url> [timeout]")
        sys.exit(1)

    target_url = sys.argv[1]
    timeout_sec = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    ok = wait_for_server(target_url, timeout_sec)
    sys.exit(0 if ok else 1)
