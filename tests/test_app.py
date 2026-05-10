import subprocess
import threading
import unittest
from unittest.mock import patch

import app
from app import reminder_loop
from challenge_reminder.notifications import notify_issue


class FakeStore:
    def __init__(self, issues):
        self.issues = issues
        self.notified_ids = []

    def list_issues(self):
        return [issue.copy() for issue in self.issues]

    def mark_notified(self, issue_id):
        self.notified_ids.append(issue_id)
        for issue in self.issues:
            if issue["id"] == issue_id:
                issue["notified"] = True
                return issue
        raise KeyError(issue_id)


class ReminderLoopTests(unittest.TestCase):
    def test_successful_notification_marks_issue_notified(self):
        store = FakeStore([due_issue("success")])

        reminder_loop(store, notify=lambda issue: True, run_once=True, on_error=ignore_error)

        self.assertEqual(["success"], store.notified_ids)

    def test_failed_notification_does_not_mark_issue_notified(self):
        store = FakeStore([due_issue("failed")])

        reminder_loop(store, notify=lambda issue: False, run_once=True, on_error=ignore_error)

        self.assertEqual([], store.notified_ids)

    def test_notification_exception_does_not_block_other_issues(self):
        store = FakeStore([due_issue("raises"), due_issue("success")])

        def notify(issue):
            if issue["id"] == "raises":
                raise RuntimeError("boom")
            return True

        reminder_loop(store, notify=notify, run_once=True, on_error=ignore_error)

        self.assertEqual(["success"], store.notified_ids)

    def test_notify_runs_outside_shared_lock(self):
        store = FakeStore([due_issue("success")])
        lock = TrackingLock()
        lock_states = []

        def notify(issue):
            lock_states.append(lock.locked)
            return True

        reminder_loop(store, notify=notify, run_once=True, store_lock=lock, on_error=ignore_error)

        self.assertEqual([False], lock_states)


class NotificationTests(unittest.TestCase):
    def test_powershell_fast_success_returns_false(self):
        class ExitedProcess:
            returncode = 0

            def wait(self, timeout):
                return self.returncode

        with patch("challenge_reminder.notifications.sys.platform", "win32"), patch(
            "challenge_reminder.notifications.subprocess.Popen",
            return_value=ExitedProcess(),
        ):
            self.assertFalse(notify_issue(due_issue("fast-exit")))

    def test_powershell_fast_failure_returns_false(self):
        class FailedProcess:
            returncode = 1

            def wait(self, timeout):
                return self.returncode

        with patch("challenge_reminder.notifications.sys.platform", "win32"), patch(
            "challenge_reminder.notifications.subprocess.Popen",
            return_value=FailedProcess(),
        ):
            self.assertFalse(notify_issue(due_issue("failed-launch")))

    def test_powershell_still_running_returns_true(self):
        class RunningProcess:
            def wait(self, timeout):
                raise subprocess.TimeoutExpired("powershell.exe", timeout)

        with patch("challenge_reminder.notifications.sys.platform", "win32"), patch(
            "challenge_reminder.notifications.subprocess.Popen",
            return_value=RunningProcess(),
        ):
            self.assertTrue(notify_issue(due_issue("running")))


class PackagedPathTests(unittest.TestCase):
    def test_source_run_uses_project_data_and_web_dirs(self):
        with patch("app.sys.frozen", False, create=True):
            self.assertEqual(app.PROJECT_ROOT / "data" / "issues.json", app.get_data_path())
            self.assertEqual(app.PROJECT_ROOT / "web", app.get_web_dir())

    def test_packaged_run_uses_meipass_for_web_and_local_app_data_for_data(self):
        with patch("app.sys.frozen", True, create=True), patch(
            "app.sys._MEIPASS",
            "C:\\Temp\\_MEI123",
            create=True,
        ), patch.dict("app.os.environ", {"LOCALAPPDATA": "C:\\Users\\Test\\AppData\\Local"}):
            self.assertEqual(
                app.Path("C:\\Temp\\_MEI123") / "web",
                app.get_web_dir(),
            )
            self.assertEqual(
                app.Path("C:\\Users\\Test\\AppData\\Local") / app.APP_NAME / "data" / "issues.json",
                app.get_data_path(),
            )

    def test_browser_opens_by_default_unless_disabled_for_tests(self):
        with patch.dict("app.os.environ", {}, clear=True):
            self.assertTrue(app.should_open_browser())

        with patch.dict("app.os.environ", {"CHALLENGE_REMINDER_NO_BROWSER": "1"}):
            self.assertFalse(app.should_open_browser())


def due_issue(issue_id):
    return {
        "id": issue_id,
        "title": issue_id,
        "status": "pending",
        "notified": False,
        "remind_at": "2026-05-10T00:00:00+00:00",
    }


def ignore_error():
    return None


class TrackingLock:
    def __init__(self):
        self._lock = threading.RLock()
        self.locked = False

    def __enter__(self):
        self._lock.acquire()
        self.locked = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.locked = False
        self._lock.release()
        return False


if __name__ == "__main__":
    unittest.main()
