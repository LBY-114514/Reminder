import json
import tempfile
import unittest
from pathlib import Path

from challenge_reminder.data_location import ConfigurableIssueStore


class ConfigurableIssueStoreTest(unittest.TestCase):
    def test_uses_default_data_path_without_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = ConfigurableIssueStore(
                root / "default" / "issues.json",
                root / "config.json",
                folder_picker=lambda _initial: "",
            )

            self.assertEqual(root / "default" / "issues.json", store.current_data_path())
            self.assertFalse(store.data_location_info()["configured"])

    def test_set_data_folder_migrates_existing_data_and_writes_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            default_path = root / "default" / "issues.json"
            config_path = root / "config.json"
            target_folder = root / "selected"
            store = ConfigurableIssueStore(default_path, config_path, folder_picker=lambda _initial: "")
            issue = store.add_issue("标题", "详情", "2026-05-10T18:30:00+08:00")

            info = store.set_data_folder(target_folder)

            self.assertTrue(info["configured"])
            self.assertTrue(info["migrated"])
            self.assertEqual(target_folder / "issues.json", store.current_data_path())
            self.assertEqual(issue["id"], store.list_issues()[0]["id"])
            self.assertEqual(
                str(target_folder / "issues.json"),
                json.loads(config_path.read_text(encoding="utf-8"))["data_path"],
            )

    def test_existing_target_data_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target_folder = root / "selected"
            target_folder.mkdir()
            target_path = target_folder / "issues.json"
            target_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "existing",
                            "title": "已有数据",
                            "detail": "",
                            "remind_at": "2026-05-10T18:30:00+08:00",
                            "status": "pending",
                            "created_at": "2026-05-10T00:00:00+08:00",
                            "updated_at": "2026-05-10T00:00:00+08:00",
                            "notified": False,
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            store = ConfigurableIssueStore(root / "default" / "issues.json", root / "config.json")
            store.add_issue("默认数据", "", "2026-05-10T18:30:00+08:00")

            info = store.set_data_folder(target_folder)

            self.assertFalse(info["migrated"])
            self.assertEqual(["existing"], [issue["id"] for issue in store.list_issues()])

    def test_cancelled_folder_picker_keeps_current_location(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = ConfigurableIssueStore(
                root / "default" / "issues.json",
                root / "config.json",
                folder_picker=lambda _initial: "",
            )

            info = store.choose_data_folder()

            self.assertTrue(info["cancelled"])
            self.assertFalse(info["migrated"])
            self.assertEqual(root / "default" / "issues.json", store.current_data_path())

    def test_save_sound_file_copies_mp3_to_current_data_folder_and_enables_sound(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = ConfigurableIssueStore(root / "default" / "issues.json", root / "config.json")

            info = store.save_sound_file("提醒.mp3", b"mp3 bytes")

            sound_path = root / "default" / "reminder-sound.mp3"
            self.assertTrue(info["enabled"])
            self.assertTrue(info["exists"])
            self.assertEqual(sound_path, store.notification_sound_path())
            self.assertEqual(b"mp3 bytes", sound_path.read_bytes())

    def test_save_sound_file_rejects_non_mp3_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = ConfigurableIssueStore(root / "default" / "issues.json", root / "config.json")

            with self.assertRaises(ValueError):
                store.save_sound_file("提醒.wav", b"not mp3")

    def test_sound_file_migrates_when_data_folder_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = ConfigurableIssueStore(root / "default" / "issues.json", root / "config.json")
            store.save_sound_file("提醒.mp3", b"mp3 bytes")

            info = store.set_data_folder(root / "selected")

            migrated_sound = root / "selected" / "reminder-sound.mp3"
            self.assertTrue(info["sound_migrated"])
            self.assertEqual(migrated_sound, store.notification_sound_path())
            self.assertEqual(b"mp3 bytes", migrated_sound.read_bytes())


if __name__ == "__main__":
    unittest.main()
