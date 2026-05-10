import json
import shutil
import tempfile
from pathlib import Path

from challenge_reminder.store import IssueStore


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
        migrated = False

        if old_path.resolve() != target_path.resolve() and old_path.exists() and not target_path.exists():
            shutil.copy2(old_path, target_path)
            migrated = True

        self._write_config(target_path)
        self.store = IssueStore(target_path)

        info = self.data_location_info()
        info["cancelled"] = False
        info["migrated"] = migrated
        return info

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
        if not self.config_path.exists():
            return None

        try:
            config = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        data_path = config.get("data_path")
        if not isinstance(data_path, str) or not data_path.strip():
            return None
        return Path(data_path)

    def _write_config(self, data_path):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"data_path": str(data_path)}, ensure_ascii=False, indent=2)
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
