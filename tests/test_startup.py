import tempfile
import unittest
from pathlib import Path

from challenge_reminder.startup import StartupManager


class StartupManagerTest(unittest.TestCase):
    def test_enable_writes_startup_command_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_path = root / "挑战杯提醒.exe"
            app_path.write_text("exe", encoding="utf-8")
            startup_dir = root / "Startup"
            manager = StartupManager(app_path, startup_dir=startup_dir, packaged=True, platform="win32")

            info = manager.set_enabled(True)

            self.assertTrue(info["enabled"])
            self.assertEqual(str(app_path), info["app_path"])
            command_file = startup_dir / "挑战杯提醒.cmd"
            self.assertTrue(command_file.is_file())
            self.assertIn(f'start "" "{app_path}"', command_file.read_text(encoding="utf-8"))

    def test_disable_removes_startup_command_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_path = root / "挑战杯提醒.exe"
            app_path.write_text("exe", encoding="utf-8")
            startup_dir = root / "Startup"
            manager = StartupManager(app_path, startup_dir=startup_dir, packaged=True, platform="win32")
            manager.set_enabled(True)

            info = manager.set_enabled(False)

            self.assertFalse(info["enabled"])
            self.assertFalse((startup_dir / "挑战杯提醒.cmd").exists())

    def test_source_mode_is_unavailable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manager = StartupManager(root / "app.py", startup_dir=root / "Startup", packaged=False, platform="win32")

            info = manager.status()

            self.assertFalse(info["available"])
            self.assertFalse(info["enabled"])


if __name__ == "__main__":
    unittest.main()
