"""桌面入口：后台启动 FastAPI，再用 PyWebView 打开原生窗口。"""

import argparse
import socket
import sys
import threading
import time

import uvicorn

from app.db import default_db_path
from app.main import app

HOST = "127.0.0.1"


def ensure_streams():
    """PyInstaller --windowed 下 stdout/stderr 为 None，重定向到日志文件。"""
    if sys.stdout is not None and sys.stderr is not None:
        return
    log_dir = default_db_path().parent
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = open(log_dir / "app.log", "a", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = log_file
    if sys.stderr is None:
        sys.stderr = log_file


def find_free_port():
    """让操作系统分配一个空闲端口，避免和已运行的服务冲突。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


def wait_until_ready(server, timeout=15):
    deadline = time.monotonic() + timeout
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("服务启动超时")
        time.sleep(0.05)


def main():
    ensure_streams()
    parser = argparse.ArgumentParser(description="待办清单桌面版")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="只启动本地服务，不打开窗口（用于测试）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="指定端口，默认自动选择空闲端口",
    )
    args = parser.parse_args()

    port = args.port or find_free_port()
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=HOST,
            port=port,
            log_level="warning",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    wait_until_ready(server)

    url = f"http://{HOST}:{port}"
    print(f"待办清单运行在 {url}")

    if args.headless:
        try:
            while thread.is_alive():
                thread.join(0.5)
        except KeyboardInterrupt:
            pass
    else:
        import webview

        webview.create_window(
            "待办清单",
            url,
            width=980,
            height=800,
            min_size=(420, 560),
            background_color="#f3f5f9",
        )
        webview.start()

    # 窗口关闭或收到 Ctrl+C 后停止后台服务。
    server.should_exit = True
    thread.join(timeout=5)


if __name__ == "__main__":
    main()
