import errno
import os
import sys
import threading
import time
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path

from challenge_reminder.data_location import ConfigurableIssueStore
from challenge_reminder.notifications import notify_issue
from challenge_reminder.reminders import due_issues
from challenge_reminder.server import create_server


APP_NAME = "ChallengeCupReminder"
PROJECT_ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
DEFAULT_PORT = 8787
PORT_ATTEMPTS = 20
DATA_PATH = None
WEB_DIR = None


def is_packaged():
    return bool(getattr(sys, "frozen", False))


def get_resource_root():
    if is_packaged() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return PROJECT_ROOT


def get_data_root():
    if is_packaged():
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / APP_NAME
        return Path.home() / APP_NAME
    return PROJECT_ROOT


def get_data_path():
    return get_data_root() / "data" / "issues.json"


def get_config_path():
    return get_data_root() / "config.json"


def get_web_dir():
    return get_resource_root() / "web"


def should_open_browser():
    return os.environ.get("CHALLENGE_REMINDER_NO_BROWSER") != "1"


DATA_PATH = get_data_path()
WEB_DIR = get_web_dir()


def find_server(port=DEFAULT_PORT):
    store = ConfigurableIssueStore(get_data_path(), get_config_path())
    last_error = None

    for candidate in range(port, port + PORT_ATTEMPTS):
        try:
            server = create_server(HOST, candidate, store, get_web_dir())
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


def reminder_loop(
    store,
    interval_seconds=20,
    stop_event=None,
    store_lock=None,
    notify=notify_issue,
    sleep=time.sleep,
    run_once=False,
    on_error=None,
):
    on_error = on_error or _report_background_error
    while stop_event is None or not stop_event.is_set():
        try:
            run_reminder_cycle(store, store_lock=store_lock, notify=notify, on_error=on_error)
        except Exception:
            on_error()

        if run_once:
            return

        if stop_event is None:
            sleep(interval_seconds)
        else:
            stop_event.wait(interval_seconds)


def run_reminder_cycle(store, store_lock=None, notify=notify_issue, on_error=None):
    on_error = on_error or _report_background_error
    now = datetime.now().astimezone()
    lock = store_lock or _NullLock()

    with lock:
        issues = due_issues(store.list_issues(), now)

    for issue in issues:
        try:
            if notify(issue) is not True:
                continue
            with lock:
                store.mark_notified(issue["id"])
        except Exception:
            on_error()


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
    print(f"数据文件：{store.current_data_path()}")
    if should_open_browser():
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


def _report_background_error():
    print("提醒后台任务发生错误，已跳过并继续运行：", file=sys.stderr)
    traceback.print_exc()


class _NullLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


if __name__ == "__main__":
    main()
