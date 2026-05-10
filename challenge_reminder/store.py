import json
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4


class IssueStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def list_issues(self):
        return self._read()

    def add_issue(self, title, detail, remind_at):
        title = self._validate_title(title)
        self._validate_remind_at(remind_at)
        now = self._now()
        issue = {
            "id": uuid4().hex,
            "title": title,
            "detail": detail,
            "remind_at": remind_at,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
            "notified": False,
        }
        issues = self._read()
        issues.append(issue)
        self._write(issues)
        return issue

    def update_issue(self, issue_id, fields):
        issues = self._read()
        issue = self._find(issues, issue_id)

        if "title" in fields:
            issue["title"] = self._validate_title(fields["title"])
        if "detail" in fields:
            issue["detail"] = fields["detail"]
        if "remind_at" in fields:
            self._validate_remind_at(fields["remind_at"])
            issue["remind_at"] = fields["remind_at"]
            issue["notified"] = False
        if "status" in fields:
            issue["status"] = fields["status"]
        if "notified" in fields:
            issue["notified"] = bool(fields["notified"])

        issue["updated_at"] = self._now()
        self._write(issues)
        return issue

    def delete_issue(self, issue_id):
        issues = self._read()
        self._find(issues, issue_id)
        remaining = [issue for issue in issues if issue["id"] != issue_id]
        self._write(remaining)

    def mark_done(self, issue_id):
        return self.update_issue(issue_id, {"status": "done"})

    def mark_notified(self, issue_id):
        return self.update_issue(issue_id, {"notified": True})

    def _ensure_file(self):
        if not self.path.exists():
            self._write([])
            return

        try:
            issues = self._read()
        except json.JSONDecodeError:
            backup = self.path.with_name(
                f"{self.path.name}.corrupt-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )
            shutil.copy2(self.path, backup)
            self._write([])
            return

        if not isinstance(issues, list):
            self._write([])

    def _read(self):
        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write(self, issues):
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(issues, file, ensure_ascii=False, indent=2)
            file.write("\n")

    def _find(self, issues, issue_id):
        for issue in issues:
            if issue.get("id") == issue_id:
                return issue
        raise KeyError(issue_id)

    def _validate_title(self, title):
        if not str(title).strip():
            raise ValueError("title must not be empty")
        return str(title).strip()

    def _validate_remind_at(self, remind_at):
        try:
            parsed = datetime.fromisoformat(remind_at)
        except (TypeError, ValueError) as exc:
            raise ValueError("remind_at must be an ISO datetime") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("remind_at must include timezone")

    def _now(self):
        return datetime.now().astimezone().replace(microsecond=0).isoformat()
