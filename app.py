import errno
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path

from challenge_reminder.notifications import notify_issue
from challenge_reminder.reminders import due_issues
from challenge_reminder.server import create_server
from challenge_reminder.store import IssueStore


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_PATH = PROJECT_ROOT / "data" / "issues.json"
WEB_DIR = PROJECT_ROOT / "web"
HOST = "127.0.0.1"
DEFAULT_PORT = 8787
PORT_ATTEMPTS = 20


def find_server(port=DEFAULT_PORT):
    store = IssueStore(DATA_PATH)
    last_error = None

    for candidate in range(port, port + PORT_ATTEMPTS):
        try:
            server = create_server(HOST, candidate, store, WEB_DIR)
        except OSError as exc:
            last_error = exc
            if exc.errno in (errno.EADDRINUSE, errno.EACCES, errno.WSAEADDRINUSE):
                continue
            raise

        server.issue_store = store
        return server

    end_port = port + PORT_ATTEMPTS - 1
    message = f"无法在 {HOST}:{port}-{end_port} 启动服务：端口均不可用"
    if last_error is not None:
        message = f"{message}（最后错误：{last_error}）"
    raise RuntimeError(message)


def reminder_loop(store, interval_seconds=20, stop_event=None, store_lock=None):
    while stop_event is None or not stop_event.is_set():
        now = datetime.now().astimezone()
        lock = store_lock or _NullLock()

        with lock:
            issues = due_issues(store.list_issues(), now)
            for issue in issues:
                notify_issue(issue)
                store.mark_notified(issue["id"])

        if stop_event is None:
            time.sleep(interval_seconds)
        else:
            stop_event.wait(interval_seconds)


def main():
    server = find_server()
    port = server.server_address[1]
    store = server.issue_store
    store_lock = server.RequestHandlerClass.store_lock
    stop_event = threading.Event()

    server_thread = threading.Thread(target=server.serve_forever, name="http-server", daemon=True)
    reminder_thread = threading.Thread(
        target=reminder_loop,
        args=(store,),
        kwargs={"stop_event": stop_event, "store_lock": store_lock},
        name="reminder-loop",
        daemon=True,
    )

    server_thread.start()
    reminder_thread.start()

    url = f"http://localhost:{port}"
    print(f"挑战杯提醒已启动：{url}")
    print(f"数据文件：{DATA_PATH}")
    webbrowser.open(url)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭挑战杯提醒...")
        stop_event.set()
        server.shutdown()
        server.server_close()
        reminder_thread.join(timeout=interval_join_timeout())
        server_thread.join(timeout=interval_join_timeout())


def interval_join_timeout():
    return 5


class _NullLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


if __name__ == "__main__":
    main()
