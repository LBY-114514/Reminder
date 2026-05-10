import threading
import unittest

from app import reminder_loop


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
