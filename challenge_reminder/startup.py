import os
import sys
from pathlib import Path


class StartupManager:
    def __init__(self, app_path, startup_dir=None, packaged=False, platform=None):
        self.app_path = Path(app_path)
        self.startup_dir = Path(startup_dir) if startup_dir is not None else self._default_startup_dir()
        self.packaged = packaged
        self.platform = platform or sys.platform

    def status(self):
        available = self._is_available()
        return {
            "available": available,
            "enabled": available and self._startup_file_matches_app(),
            "path": str(self.startup_file),
            "app_path": str(self.app_path),
            "message": "" if available else "开机自启仅支持 Windows exe 版本。",
        }

    def set_enabled(self, enabled):
        if not self._is_available():
            raise OSError("开机自启仅支持 Windows exe 版本")

        if enabled:
            self.startup_dir.mkdir(parents=True, exist_ok=True)
            self.startup_file.write_text(self._command_content(), encoding="utf-8")
        elif self.startup_file.exists():
            self.startup_file.unlink()

        return self.status()

    @property
    def startup_file(self):
        return self.startup_dir / "挑战杯提醒.cmd"

    def _is_available(self):
        return self.platform.startswith("win") and self.packaged

    def _startup_file_matches_app(self):
        if not self.startup_file.is_file():
            return False
        try:
            return str(self.app_path) in self.startup_file.read_text(encoding="utf-8")
        except OSError:
            return False

    def _command_content(self):
        return f'@echo off\r\nstart "" "{self.app_path}"\r\n'

    def _default_startup_dir(self):
        app_data = os.environ.get("APPDATA")
        if app_data:
            return Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
