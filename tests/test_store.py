import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from challenge_reminder.store import IssueStore


class IssueStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "issues.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def read_issues(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_missing_file_is_created_with_empty_array(self):
        IssueStore(self.path)

        self.assertTrue(self.path.exists())
        self.assertEqual([], self.read_issues())

    def test_add_issue_persists_required_fields(self):
        store = IssueStore(self.path)

        issue = store.add_issue(
            "准备材料",
            "整理挑战杯申报材料",
            "2026-05-10T18:30:00+08:00",
        )

        [saved] = self.read_issues()
        self.assertEqual(issue, saved)
        self.assertEqual("准备材料", saved["title"])
        self.assertEqual("整理挑战杯申报材料", saved["detail"])
        self.assertEqual("2026-05-10T18:30:00+08:00", saved["remind_at"])
        self.assertEqual("pending", saved["status"])
        self.assertFalse(saved["notified"])
        self.assertTrue(saved["id"])
        datetime.fromisoformat(saved["created_at"])
        datetime.fromisoformat(saved["updated_at"])

    def test_update_remind_at_resets_notified(self):
        store = IssueStore(self.path)
        issue = store.add_issue("准备材料", "", "2026-05-10T18:30:00+08:00")
        store.mark_notified(issue["id"])

        updated = store.update_issue(
            issue["id"],
            {"remind_at": "2026-05-11T09:00:00+08:00"},
        )

        self.assertFalse(updated["notified"])
        [saved] = self.read_issues()
        self.assertFalse(saved["notified"])
        self.assertEqual("2026-05-11T09:00:00+08:00", saved["remind_at"])

    def test_mark_done_persists_done_status(self):
        store = IssueStore(self.path)
        issue = store.add_issue("准备材料", "", "2026-05-10T18:30:00+08:00")

        done = store.mark_done(issue["id"])

        self.assertEqual("done", done["status"])
        [saved] = self.read_issues()
        self.assertEqual("done", saved["status"])

    def test_delete_issue_removes_issue_from_storage(self):
        store = IssueStore(self.path)
        issue = store.add_issue("准备材料", "", "2026-05-10T18:30:00+08:00")

        store.delete_issue(issue["id"])

        self.assertEqual([], store.list_issues())
        self.assertEqual([], self.read_issues())

    def test_missing_issue_id_raises_key_error(self):
        store = IssueStore(self.path)

        with self.assertRaises(KeyError):
            store.update_issue("missing", {"title": "新标题"})
        with self.assertRaises(KeyError):
            store.delete_issue("missing")
        with self.assertRaises(KeyError):
            store.mark_done("missing")
        with self.assertRaises(KeyError):
            store.mark_notified("missing")

    def test_corrupt_json_is_backed_up_and_recovered_as_empty_array(self):
        self.path.write_text("{broken", encoding="utf-8")

        store = IssueStore(self.path)

        self.assertEqual([], store.list_issues())
        self.assertEqual([], self.read_issues())
        backups = list(self.path.parent.glob("issues.json.corrupt-*"))
        self.assertEqual(1, len(backups))
        self.assertEqual("{broken", backups[0].read_text(encoding="utf-8"))

    def test_empty_title_raises_value_error(self):
        store = IssueStore(self.path)

        with self.assertRaises(ValueError):
            store.add_issue("  ", "", "2026-05-10T18:30:00+08:00")

    def test_invalid_remind_at_raises_value_error(self):
        store = IssueStore(self.path)

        with self.assertRaises(ValueError):
            store.add_issue("准备材料", "", "2026-05-10T18:30:00")


if __name__ == "__main__":
    unittest.main()
