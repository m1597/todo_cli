"""桌面入口：后台启动 FastAPI，再用 PyWebView 打开原生窗口。"""

import argparse
import socket
import sys
import threading
import time

import uvicorn

from app.db import default_db_path
from app.main import app

# ===========================================================================
# 桌面版的运行顺序：
# 1. 在后台线程启动 uvicorn（和命令行里的 uvicorn 是同一个服务器）
# 2. 等它真正开始监听端口
# 3. 主线程打开 PyWebView 窗口，窗口里加载 http://127.0.0.1:端口
# 4. 窗口关闭后，通知 uvicorn 退出
#
# 为什么要用线程：uvicorn 需要一直运行，而 PyWebView 的窗口也要一直运行；
# 一个程序里同时做两件“不能结束”的事，就把其中一个放到后台线程。
# ===========================================================================

HOST = "127.0.0.1"


def ensure_streams():
    """PyInstaller --windowed 下 stdout/stderr 为 None，重定向到日志文件。"""
    # 正常从终端运行时，stdout/stderr 已经存在，不需要处理。
    if sys.stdout is not None and sys.stderr is not None:
        return
    # 打包成无控制台程序后，print 和日志没有地方输出，所以写进 app.log。
    log_dir = default_db_path().parent
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = open(log_dir / "app.log", "a", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = log_file
    if sys.stderr is None:
        sys.stderr = log_file


def find_free_port():
    """让操作系统分配一个空闲端口，避免和已运行的服务冲突。"""
    # 端口写 0 表示“随便给我一个没被占用的端口”，系统会临时分配。
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


def wait_until_ready(server, timeout=15):
    """轮询等待 uvicorn 设置 started 标记，最多等 timeout 秒。"""
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
    # Config 描述“怎么启动”，Server 才是真正运行的服务对象。
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=HOST,
            port=port,
            log_level="warning",
            access_log=False,
        )
    )
    # daemon=True 表示这是后台线程：主线程结束时它会自动跟着结束。
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    # 不等它准备好就打开窗口，窗口可能先显示“无法连接”，所以先等一等。
    wait_until_ready(server)

    url = f"http://{HOST}:{port}"
    print(f"待办清单运行在 {url}")

    if args.headless:
        # 测试模式：不打开窗口，主线程保持运行，直到按 Ctrl+C 或进程被结束。
        try:
            while thread.is_alive():
                thread.join(0.5)
        except KeyboardInterrupt:
            pass
    else:
        # PyWebView 必须在主线程创建窗口；uvicorn 已经在后台线程跑着了。
        import webview

        webview.create_window(
            "待办清单",
            url,
            width=980,
            height=800,
            min_size=(420, 560),
            background_color="#f3f5f9",
        )
        # start() 会阻塞，直到窗口关闭。
        webview.start()

    # 窗口关闭或收到 Ctrl+C 后停止后台服务。
    server.should_exit = True
    thread.join(timeout=5)


if __name__ == "__main__":
    main()
