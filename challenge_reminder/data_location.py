import json
import shutil
import tempfile
from pathlib import Path

from challenge_reminder.store import IssueStore


SOUND_FILE_NAME = "reminder-sound.mp3"


class ConfigurableIssueStore:
    def __init__(self, default_data_path, config_path, folder_picker=None):
        self.default_data_path = Path(default_data_path)
        self.config_path = Path(config_path)
        self.folder_picker = folder_picker or pick_folder
        self.store = IssueStore(self.current_data_path())

    def current_data_path(self):
        configured_path = self._configured_data_path()
        return configured_path or self.default_data_path

    def data_location_info(self):
        data_path = self.current_data_path()
        return {
            "path": str(data_path),
            "folder": str(data_path.parent),
            "configured": self._configured_data_path() is not None,
            "config_path": str(self.config_path),
        }

    def choose_data_folder(self):
        selected_folder = self.folder_picker(str(self.current_data_path().parent))
        if not selected_folder:
            info = self.data_location_info()
            info["cancelled"] = True
            info["migrated"] = False
            return info
        return self.set_data_folder(selected_folder)

    def set_data_folder(self, folder):
        target_folder = Path(folder)
        target_folder.mkdir(parents=True, exist_ok=True)
        target_path = target_folder / "issues.json"
        old_path = self.current_data_path()
        old_sound_path = self._sound_path_for(old_path)
        target_sound_path = target_folder / SOUND_FILE_NAME
        migrated = False
        sound_migrated = False

        if old_path.resolve() != target_path.resolve() and old_path.exists() and not target_path.exists():
            shutil.copy2(old_path, target_path)
            migrated = True

        if (
            old_sound_path.resolve() != target_sound_path.resolve()
            and old_sound_path.exists()
            and not target_sound_path.exists()
        ):
            shutil.copy2(old_sound_path, target_sound_path)
            sound_migrated = True

        self._write_config(target_path)
        self.store = IssueStore(target_path)

        info = self.data_location_info()
        info["cancelled"] = False
        info["migrated"] = migrated
        info["sound_migrated"] = sound_migrated
        return info

    def sound_settings(self):
        config = self._read_config()
        sound_path = self._sound_path_for(self.current_data_path())
        return {
            "enabled": bool(config.get("sound_enabled", False)),
            "path": str(sound_path),
            "exists": sound_path.is_file(),
            "file_name": SOUND_FILE_NAME,
        }

    def set_sound_enabled(self, enabled):
        self._write_config(self.current_data_path(), sound_enabled=bool(enabled))
        return self.sound_settings()

    def save_sound_file(self, filename, content):
        if Path(str(filename)).suffix.lower() != ".mp3":
            raise ValueError("sound file must be an mp3")
        if not content:
            raise ValueError("sound file must not be empty")

        sound_path = self._sound_path_for(self.current_data_path())
        sound_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = sound_path.with_name(f".{sound_path.name}.tmp")
        temp_path.write_bytes(content)
        temp_path.replace(sound_path)
        self._write_config(self.current_data_path(), sound_enabled=True)

        info = self.sound_settings()
        info["size"] = sound_path.stat().st_size
        return info

    def notification_sound_path(self):
        info = self.sound_settings()
        if not info["enabled"] or not info["exists"]:
            return None
        return Path(info["path"])

    def list_issues(self):
        return self.store.list_issues()

    def add_issue(self, title, detail, remind_at):
        return self.store.add_issue(title, detail, remind_at)

    def update_issue(self, issue_id, fields):
        return self.store.update_issue(issue_id, fields)

    def delete_issue(self, issue_id):
        return self.store.delete_issue(issue_id)

    def mark_done(self, issue_id):
        return self.store.mark_done(issue_id)

    def mark_notified(self, issue_id):
        return self.store.mark_notified(issue_id)

    def _configured_data_path(self):
        config = self._read_config()
        data_path = config.get("data_path")
        if not isinstance(data_path, str) or not data_path.strip():
            return None
        return Path(data_path)

    def _read_config(self):
        if not self.config_path.exists():
            return {}

        try:
            config = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

        if not isinstance(config, dict):
            return {}
        return config

    def _write_config(self, data_path, **updates):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        config = self._read_config()
        config["data_path"] = str(data_path)
        config.update(updates)
        payload = json.dumps(config, ensure_ascii=False, indent=2)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.config_path.parent,
            prefix=f".{self.config_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(payload)
            temp_file.write("\n")
            temp_path = Path(temp_file.name)
        temp_path.replace(self.config_path)

    def _sound_path_for(self, data_path):
        return Path(data_path).parent / SOUND_FILE_NAME


def pick_folder(initial_dir):
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        return filedialog.askdirectory(
            title="选择提醒数据保存文件夹",
            initialdir=initial_dir,
            mustexist=False,
        )
    finally:
        root.destroy()
