import unittest
from datetime import datetime, timezone

from challenge_reminder.reminders import due_issues


class DueIssuesTests(unittest.TestCase):
    def test_returns_pending_unnotified_issues_due_at_or_before_now(self):
        now = datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc)
        earlier_issue = {
            "id": "earlier",
            "status": "pending",
            "notified": False,
            "remind_at": "2026-05-10T11:59:00+00:00",
        }
        equal_issue = {
            "id": "equal",
            "status": "pending",
            "notified": False,
            "remind_at": "2026-05-10T12:00:00+00:00",
        }

        self.assertEqual(due_issues([earlier_issue, equal_issue], now), [earlier_issue, equal_issue])

    def test_ignores_done_notified_and_future_issues(self):
        now = datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc)
        done_issue = {
            "id": "done",
            "status": "done",
            "notified": False,
            "remind_at": "2026-05-10T11:00:00+00:00",
        }
        notified_issue = {
            "id": "notified",
            "status": "pending",
            "notified": True,
            "remind_at": "2026-05-10T11:00:00+00:00",
        }
        future_issue = {
            "id": "future",
            "status": "pending",
            "notified": False,
            "remind_at": "2026-05-10T12:01:00+00:00",
        }

        self.assertEqual(due_issues([done_issue, notified_issue, future_issue], now), [])


if __name__ == "__main__":
    unittest.main()
