# Challenge Cup Local Reminder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete first version of a local Challenge Cup issue recorder that starts from a desktop shortcut/script, stores data in this project folder, and reminds the user on the computer at scheduled times.

**Architecture:** Use a dependency-light Python standard-library local HTTP server with focused modules for storage, reminder detection, and notification delivery. The frontend is plain HTML/CSS/JavaScript served from `web/`, communicating with JSON APIs. Data lives in `data/issues.json` inside the repository so it can be backed up and uploaded to GitHub without user records if ignored.

**Tech Stack:** Python 3 standard library, `unittest`, `http.server`, JSON file storage, plain HTML/CSS/JavaScript, Windows `.bat` startup script.

---

## File Structure

- Create `challenge_reminder/__init__.py`: package marker.
- Create `challenge_reminder/store.py`: JSON file creation, loading, backup, validation, CRUD operations.
- Create `challenge_reminder/reminders.py`: identify due reminders and mark records as notified.
- Create `challenge_reminder/notifications.py`: local computer notification helper with PowerShell message box fallback.
- Create `challenge_reminder/server.py`: local HTTP server and JSON API routes.
- Create `app.py`: entry point; starts server, opens browser, runs reminder loop.
- Create `web/index.html`: app shell.
- Create `web/styles.css`: first-version usable UI.
- Create `web/app.js`: frontend state, API calls, form handling, reminder polling.
- Create `data/.gitkeep`: keep data directory in Git while ignoring personal JSON data.
- Create `tests/test_store.py`: TDD tests for storage.
- Create `tests/test_reminders.py`: TDD tests for reminder selection.
- Create `README.md`: local usage and GitHub setup instructions.
- Create `.gitignore`: ignore runtime data, caches, and local brainstorm files.
- Create `start.bat`: double-click startup script using `conda activate forskills`.

## Commands

All Python commands must be run after activating the required environment:

```bat
conda activate forskills
```

For PowerShell:

```powershell
conda activate forskills
python -m unittest discover -s tests -v
```

---

### Task 1: Storage Module

**Files:**
- Create: `challenge_reminder/__init__.py`
- Create: `challenge_reminder/store.py`
- Create: `tests/test_store.py`

- [ ] **Step 1: Write failing storage tests**

Create `tests/test_store.py`:

```python
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from challenge_reminder.store import IssueStore


class IssueStoreTest(unittest.TestCase):
    def test_missing_file_is_created_as_empty_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "data" / "issues.json"
            store = IssueStore(path)

            self.assertEqual(store.list_issues(), [])
            self.assertTrue(path.exists())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), [])

    def test_add_issue_persists_required_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "issues.json"
            store = IssueStore(path)

            issue = store.add_issue(
                title="PPT 逻辑不顺",
                detail="第二部分和第三部分衔接不好",
                remind_at="2026-05-10T20:30:00+08:00",
            )

            saved = store.list_issues()
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]["id"], issue["id"])
            self.assertEqual(saved[0]["title"], "PPT 逻辑不顺")
            self.assertEqual(saved[0]["detail"], "第二部分和第三部分衔接不好")
            self.assertEqual(saved[0]["remind_at"], "2026-05-10T20:30:00+08:00")
            self.assertEqual(saved[0]["status"], "pending")
            self.assertFalse(saved[0]["notified"])
            self.assertIn("created_at", saved[0])
            self.assertIn("updated_at", saved[0])

    def test_update_remind_at_resets_notified(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "issues.json"
            store = IssueStore(path)
            issue = store.add_issue("标题", "", "2026-05-10T20:30:00+08:00")
            store.mark_notified(issue["id"])

            updated = store.update_issue(
                issue["id"],
                {
                    "title": "标题",
                    "detail": "",
                    "remind_at": "2026-05-11T09:00:00+08:00",
                },
            )

            self.assertEqual(updated["remind_at"], "2026-05-11T09:00:00+08:00")
            self.assertFalse(updated["notified"])

    def test_done_issue_is_persisted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "issues.json"
            store = IssueStore(path)
            issue = store.add_issue("标题", "", "2026-05-10T20:30:00+08:00")

            done = store.mark_done(issue["id"])

            self.assertEqual(done["status"], "done")
            self.assertEqual(store.list_issues()[0]["status"], "done")

    def test_corrupt_json_is_backed_up_and_replaced(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "issues.json"
            path.write_text("{bad json", encoding="utf-8")

            store = IssueStore(path)

            self.assertEqual(store.list_issues(), [])
            backups = list(path.parent.glob("issues.json.corrupt-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), [])

    def test_empty_title_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "issues.json"
            store = IssueStore(path)

            with self.assertRaises(ValueError):
                store.add_issue("", "", "2026-05-10T20:30:00+08:00")

    def test_invalid_remind_at_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "issues.json"
            store = IssueStore(path)

            with self.assertRaises(ValueError):
                store.add_issue("标题", "", "not-a-date")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
conda activate forskills
python -m unittest tests.test_store -v
```

Expected: fails with `ModuleNotFoundError` or missing `IssueStore`.

- [ ] **Step 3: Create minimal storage implementation**

Create `challenge_reminder/__init__.py` as an empty file.

Create `challenge_reminder/store.py`:

```python
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path


class IssueStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def list_issues(self):
        return self._read()

    def add_issue(self, title, detail, remind_at):
        title = self._validate_title(title)
        remind_at = self._validate_datetime(remind_at)
        now = self._now()
        issue = {
            "id": str(uuid.uuid4()),
            "title": title,
            "detail": detail or "",
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
        for issue in issues:
            if issue["id"] == issue_id:
                old_remind_at = issue["remind_at"]
                issue["title"] = self._validate_title(fields.get("title", issue["title"]))
                issue["detail"] = fields.get("detail", issue.get("detail", "")) or ""
                issue["remind_at"] = self._validate_datetime(fields.get("remind_at", issue["remind_at"]))
                if issue["remind_at"] != old_remind_at:
                    issue["notified"] = False
                issue["updated_at"] = self._now()
                self._write(issues)
                return issue
        raise KeyError(issue_id)

    def delete_issue(self, issue_id):
        issues = self._read()
        next_issues = [issue for issue in issues if issue["id"] != issue_id]
        if len(next_issues) == len(issues):
            raise KeyError(issue_id)
        self._write(next_issues)

    def mark_done(self, issue_id):
        issues = self._read()
        for issue in issues:
            if issue["id"] == issue_id:
                issue["status"] = "done"
                issue["updated_at"] = self._now()
                self._write(issues)
                return issue
        raise KeyError(issue_id)

    def mark_notified(self, issue_id):
        issues = self._read()
        for issue in issues:
            if issue["id"] == issue_id:
                issue["notified"] = True
                issue["updated_at"] = self._now()
                self._write(issues)
                return issue
        raise KeyError(issue_id)

    def _ensure_file(self):
        if not self.path.exists():
            self._write([])
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("issues json must be a list")
        except Exception:
            backup = self.path.with_name(
                f"{self.path.name}.corrupt-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )
            shutil.copy2(self.path, backup)
            self._write([])

    def _read(self):
        self._ensure_file()
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, issues):
        self.path.write_text(
            json.dumps(issues, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _validate_title(self, title):
        title = (title or "").strip()
        if not title:
            raise ValueError("标题不能为空")
        return title

    def _validate_datetime(self, value):
        value = (value or "").strip()
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("提醒时间格式不正确") from exc
        if parsed.tzinfo is None:
            raise ValueError("提醒时间必须包含时区")
        return value

    def _now(self):
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```powershell
conda activate forskills
python -m unittest tests.test_store -v
```

Expected: all `tests.test_store` tests pass.

- [ ] **Step 5: Commit storage module**

Run:

```powershell
git add challenge_reminder/__init__.py challenge_reminder/store.py tests/test_store.py
git commit -m "feat: add issue storage"
```

---

### Task 2: Reminder Selection Logic

**Files:**
- Create: `challenge_reminder/reminders.py`
- Create: `tests/test_reminders.py`

- [ ] **Step 1: Write failing reminder tests**

Create `tests/test_reminders.py`:

```python
import unittest
from datetime import datetime

from challenge_reminder.reminders import due_issues


class ReminderTest(unittest.TestCase):
    def test_pending_unnotified_issue_due_before_now_is_returned(self):
        issues = [
            {
                "id": "1",
                "title": "该提醒",
                "remind_at": "2026-05-10T20:00:00+08:00",
                "status": "pending",
                "notified": False,
            }
        ]
        now = datetime.fromisoformat("2026-05-10T20:30:00+08:00")

        result = due_issues(issues, now)

        self.assertEqual([issue["id"] for issue in result], ["1"])

    def test_done_notified_and_future_issues_are_ignored(self):
        issues = [
            {
                "id": "done",
                "title": "已处理",
                "remind_at": "2026-05-10T20:00:00+08:00",
                "status": "done",
                "notified": False,
            },
            {
                "id": "notified",
                "title": "已提醒",
                "remind_at": "2026-05-10T20:00:00+08:00",
                "status": "pending",
                "notified": True,
            },
            {
                "id": "future",
                "title": "未来",
                "remind_at": "2026-05-10T21:00:00+08:00",
                "status": "pending",
                "notified": False,
            },
        ]
        now = datetime.fromisoformat("2026-05-10T20:30:00+08:00")

        result = due_issues(issues, now)

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
conda activate forskills
python -m unittest tests.test_reminders -v
```

Expected: fails because `challenge_reminder.reminders` or `due_issues` does not exist.

- [ ] **Step 3: Implement reminder selection**

Create `challenge_reminder/reminders.py`:

```python
from datetime import datetime


def due_issues(issues, now):
    due = []
    for issue in issues:
        if issue.get("status") != "pending":
            continue
        if issue.get("notified"):
            continue
        remind_at = datetime.fromisoformat(issue["remind_at"])
        if remind_at <= now:
            due.append(issue)
    return due
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```powershell
conda activate forskills
python -m unittest tests.test_reminders -v
```

Expected: all reminder tests pass.

- [ ] **Step 5: Commit reminder logic**

Run:

```powershell
git add challenge_reminder/reminders.py tests/test_reminders.py
git commit -m "feat: add reminder selection"
```

---

### Task 3: Notification Helper

**Files:**
- Create: `challenge_reminder/notifications.py`

- [ ] **Step 1: Write a small manual notification helper**

Create `challenge_reminder/notifications.py`:

```python
import subprocess


def notify_issue(issue):
    title = f"挑战杯提醒：{issue['title']}"
    detail = issue.get("detail") or "记得查看这条记录。"
    message = detail[:500]
    try:
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                (
                    "Add-Type -AssemblyName PresentationFramework; "
                    f"[System.Windows.MessageBox]::Show({message!r}, {title!r})"
                ),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False
```

- [ ] **Step 2: Smoke test notification helper**

Run:

```powershell
conda activate forskills
python -c "from challenge_reminder.notifications import notify_issue; notify_issue({'title':'测试提醒','detail':'如果看到这个窗口，提醒可用。'})"
```

Expected: a Windows message box appears. Close it after confirming.

- [ ] **Step 3: Commit notification helper**

Run:

```powershell
git add challenge_reminder/notifications.py
git commit -m "feat: add local notification helper"
```

---

### Task 4: Local HTTP API Server

**Files:**
- Create: `challenge_reminder/server.py`

- [ ] **Step 1: Implement JSON API server**

Create `challenge_reminder/server.py`:

```python
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


class ChallengeReminderHandler(BaseHTTPRequestHandler):
    store = None
    web_dir = None

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/issues":
            self._json(200, self.store.list_issues())
            return
        if path == "/":
            self._static("index.html")
            return
        self._static(path.lstrip("/"))

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/issues":
            payload = self._body()
            try:
                issue = self.store.add_issue(
                    payload.get("title", ""),
                    payload.get("detail", ""),
                    payload.get("remind_at", ""),
                )
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
                return
            self._json(201, issue)
            return
        if path.startswith("/api/issues/") and path.endswith("/done"):
            issue_id = path.split("/")[3]
            try:
                issue = self.store.mark_done(issue_id)
            except KeyError:
                self._json(404, {"error": "记录不存在"})
                return
            self._json(200, issue)
            return
        self._json(404, {"error": "接口不存在"})

    def do_PUT(self):
        path = urlparse(self.path).path
        if path.startswith("/api/issues/"):
            issue_id = path.split("/")[3]
            try:
                issue = self.store.update_issue(issue_id, self._body())
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
                return
            except KeyError:
                self._json(404, {"error": "记录不存在"})
                return
            self._json(200, issue)
            return
        self._json(404, {"error": "接口不存在"})

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/api/issues/"):
            issue_id = path.split("/")[3]
            try:
                self.store.delete_issue(issue_id)
            except KeyError:
                self._json(404, {"error": "记录不存在"})
                return
            self._json(200, {"ok": True})
            return
        self._json(404, {"error": "接口不存在"})

    def log_message(self, format, *args):
        return

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def _json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _static(self, relative_path):
        target = (Path(self.web_dir) / relative_path).resolve()
        web_root = Path(self.web_dir).resolve()
        if not str(target).startswith(str(web_root)) or not target.exists() or not target.is_file():
            self._json(404, {"error": "页面不存在"})
            return
        content = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def create_server(host, port, store, web_dir):
    ChallengeReminderHandler.store = store
    ChallengeReminderHandler.web_dir = str(web_dir)
    return ThreadingHTTPServer((host, port), ChallengeReminderHandler)
```

- [ ] **Step 2: Manual API smoke test after app entry exists**

This task is verified in Task 6 after `app.py` starts the server.

- [ ] **Step 3: Commit API server**

Run:

```powershell
git add challenge_reminder/server.py
git commit -m "feat: add local api server"
```

---

### Task 5: Frontend Page

**Files:**
- Create: `web/index.html`
- Create: `web/styles.css`
- Create: `web/app.js`

- [ ] **Step 1: Create HTML shell**

Create `web/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>挑战杯问题记录</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <main class="app">
    <header class="hero">
      <div>
        <p class="eyebrow">Challenge Cup Reminder</p>
        <h1>挑战杯问题记录</h1>
        <p>把卡住的问题记下来，设个时间提醒自己回来处理。</p>
      </div>
      <div class="next-card">
        <span>下一步</span>
        <strong id="nextReminder">暂无待提醒问题</strong>
      </div>
    </header>

    <section id="alertBox" class="alert hidden"></section>

    <section class="panel">
      <h2 id="formTitle">新增问题</h2>
      <form id="issueForm">
        <input type="hidden" id="issueId">
        <label>
          问题标题
          <input id="title" required placeholder="例如：答辩 PPT 逻辑不顺">
        </label>
        <label>
          详细说明
          <textarea id="detail" rows="4" placeholder="记录背景、卡住的点、要问谁或要查什么"></textarea>
        </label>
        <label>
          提醒时间
          <input id="remindAt" type="datetime-local" required>
        </label>
        <div class="actions">
          <button type="submit">保存</button>
          <button type="button" id="cancelEdit" class="secondary hidden">取消编辑</button>
        </div>
      </form>
    </section>

    <section class="toolbar">
      <button data-filter="all" class="active">全部</button>
      <button data-filter="pending">待处理</button>
      <button data-filter="done">已处理</button>
    </section>

    <section id="issueList" class="list"></section>
  </main>
  <script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create usable CSS**

Create `web/styles.css`:

```css
:root {
  color-scheme: light;
  --bg: #f5f7fb;
  --card: #ffffff;
  --text: #172033;
  --muted: #667085;
  --line: #d9e2ef;
  --primary: #2563eb;
  --primary-dark: #1d4ed8;
  --danger: #dc2626;
  --success: #16a34a;
  font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: linear-gradient(135deg, #edf4ff, var(--bg));
  color: var(--text);
}

.app {
  max-width: 1040px;
  margin: 0 auto;
  padding: 32px 20px 56px;
}

.hero {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 20px;
  align-items: stretch;
  margin-bottom: 22px;
}

.hero h1 {
  margin: 8px 0;
  font-size: 42px;
}

.hero p {
  margin: 0;
  color: var(--muted);
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 12px;
  font-weight: 700;
}

.next-card,
.panel,
.alert,
.toolbar,
.issue-card {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--line);
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(25, 45, 90, 0.08);
}

.next-card {
  padding: 22px;
}

.next-card span {
  color: var(--muted);
  display: block;
  margin-bottom: 12px;
}

.panel {
  padding: 22px;
}

label {
  display: block;
  margin: 14px 0;
  color: var(--muted);
  font-weight: 700;
}

input,
textarea {
  width: 100%;
  margin-top: 8px;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px 14px;
  font: inherit;
  color: var(--text);
}

textarea {
  resize: vertical;
}

button {
  border: 0;
  border-radius: 12px;
  background: var(--primary);
  color: white;
  padding: 11px 16px;
  cursor: pointer;
  font-weight: 700;
}

button:hover {
  background: var(--primary-dark);
}

button.secondary {
  background: #e2e8f0;
  color: var(--text);
}

button.danger {
  background: var(--danger);
}

button.success {
  background: var(--success);
}

.actions,
.card-actions,
.toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.toolbar {
  margin: 18px 0;
  padding: 12px;
}

.toolbar button {
  background: #eaf0f8;
  color: var(--text);
}

.toolbar button.active {
  background: var(--primary);
  color: white;
}

.list {
  display: grid;
  gap: 14px;
}

.issue-card {
  padding: 18px;
}

.issue-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.issue-head h3 {
  margin: 0 0 8px;
}

.meta {
  color: var(--muted);
  font-size: 14px;
}

.detail {
  white-space: pre-wrap;
  line-height: 1.7;
}

.status {
  display: inline-flex;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 700;
  background: #dbeafe;
  color: #1e40af;
}

.status.done {
  background: #dcfce7;
  color: #166534;
}

.alert {
  margin-bottom: 18px;
  padding: 16px;
  border-color: #f59e0b;
  background: #fffbeb;
}

.hidden {
  display: none;
}

@media (max-width: 760px) {
  .hero {
    grid-template-columns: 1fr;
  }

  .hero h1 {
    font-size: 32px;
  }
}
```

- [ ] **Step 3: Create frontend JavaScript**

Create `web/app.js`:

```javascript
const form = document.querySelector("#issueForm");
const issueId = document.querySelector("#issueId");
const title = document.querySelector("#title");
const detail = document.querySelector("#detail");
const remindAt = document.querySelector("#remindAt");
const issueList = document.querySelector("#issueList");
const nextReminder = document.querySelector("#nextReminder");
const alertBox = document.querySelector("#alertBox");
const cancelEdit = document.querySelector("#cancelEdit");
const formTitle = document.querySelector("#formTitle");
let issues = [];
let filter = "all";

function localInputToIso(value) {
  const date = new Date(value);
  return date.toISOString();
}

function isoToLocalInput(value) {
  const date = new Date(value);
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60 * 1000);
  return local.toISOString().slice(0, 16);
}

function formatTime(value) {
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "请求失败");
  }
  return data;
}

async function loadIssues() {
  issues = await api("/api/issues");
  render();
}

function render() {
  renderNextReminder();
  const visible = issues.filter((issue) => filter === "all" || issue.status === filter);
  if (visible.length === 0) {
    issueList.innerHTML = `<div class="issue-card"><p class="meta">暂无记录。</p></div>`;
    return;
  }
  issueList.innerHTML = visible
    .sort((a, b) => new Date(a.remind_at) - new Date(b.remind_at))
    .map((issue) => `
      <article class="issue-card">
        <div class="issue-head">
          <div>
            <h3>${escapeHtml(issue.title)}</h3>
            <p class="meta">提醒：${formatTime(issue.remind_at)}</p>
          </div>
          <span class="status ${issue.status === "done" ? "done" : ""}">
            ${issue.status === "done" ? "已处理" : "待处理"}
          </span>
        </div>
        <p class="detail">${escapeHtml(issue.detail || "没有填写详情。")}</p>
        <div class="card-actions">
          <button onclick="editIssue('${issue.id}')">编辑</button>
          <button class="success" onclick="markDone('${issue.id}')">标记已处理</button>
          <button class="danger" onclick="deleteIssue('${issue.id}')">删除</button>
        </div>
      </article>
    `)
    .join("");
}

function renderNextReminder() {
  const pending = issues
    .filter((issue) => issue.status === "pending")
    .sort((a, b) => new Date(a.remind_at) - new Date(b.remind_at));
  nextReminder.textContent = pending.length
    ? `${formatTime(pending[0].remind_at)} · ${pending[0].title}`
    : "暂无待提醒问题";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    title: title.value,
    detail: detail.value,
    remind_at: localInputToIso(remindAt.value),
  };
  try {
    if (issueId.value) {
      await api(`/api/issues/${issueId.value}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
    } else {
      await api("/api/issues", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    }
    resetForm();
    await loadIssues();
  } catch (error) {
    showAlert(error.message);
  }
});

cancelEdit.addEventListener("click", resetForm);

document.querySelectorAll("[data-filter]").forEach((button) => {
  button.addEventListener("click", () => {
    filter = button.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    render();
  });
});

window.editIssue = function editIssue(id) {
  const issue = issues.find((item) => item.id === id);
  if (!issue) return;
  issueId.value = issue.id;
  title.value = issue.title;
  detail.value = issue.detail || "";
  remindAt.value = isoToLocalInput(issue.remind_at);
  formTitle.textContent = "编辑问题";
  cancelEdit.classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
};

window.markDone = async function markDone(id) {
  await api(`/api/issues/${id}/done`, { method: "POST" });
  await loadIssues();
};

window.deleteIssue = async function deleteIssue(id) {
  if (!confirm("确定删除这条记录吗？")) return;
  await api(`/api/issues/${id}`, { method: "DELETE" });
  await loadIssues();
};

function resetForm() {
  issueId.value = "";
  title.value = "";
  detail.value = "";
  remindAt.value = "";
  formTitle.textContent = "新增问题";
  cancelEdit.classList.add("hidden");
}

function showAlert(message) {
  alertBox.textContent = message;
  alertBox.classList.remove("hidden");
  setTimeout(() => alertBox.classList.add("hidden"), 7000);
}

async function pollIssues() {
  await loadIssues();
  const now = Date.now();
  const due = issues.filter((issue) =>
    issue.status === "pending" &&
    !issue.notified &&
    new Date(issue.remind_at).getTime() <= now
  );
  if (due.length > 0) {
    showAlert(`提醒：${due.map((issue) => issue.title).join("、")}`);
  }
}

loadIssues();
setInterval(pollIssues, 30000);
```

- [ ] **Step 4: Commit frontend**

Run:

```powershell
git add web/index.html web/styles.css web/app.js
git commit -m "feat: add reminder web interface"
```

---

### Task 6: App Entry and Reminder Loop

**Files:**
- Create: `app.py`

- [ ] **Step 1: Create app entry**

Create `app.py`:

```python
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path

from challenge_reminder.notifications import notify_issue
from challenge_reminder.reminders import due_issues
from challenge_reminder.server import create_server
from challenge_reminder.store import IssueStore


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "issues.json"
WEB_DIR = ROOT / "web"
HOST = "127.0.0.1"
DEFAULT_PORT = 8787


def find_server(port=DEFAULT_PORT):
    store = IssueStore(DATA_PATH)
    for candidate in range(port, port + 20):
        try:
            server = create_server(HOST, candidate, store, WEB_DIR)
            return server, store, candidate
        except OSError:
            continue
    raise RuntimeError("没有可用端口，请关闭占用 8787-8806 的程序后重试。")


def reminder_loop(store, interval_seconds=20):
    while True:
        now = datetime.now().astimezone()
        for issue in due_issues(store.list_issues(), now):
            notify_issue(issue)
            store.mark_notified(issue["id"])
        time.sleep(interval_seconds)


def main():
    server, store, port = find_server()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    reminder_thread = threading.Thread(target=reminder_loop, args=(store,), daemon=True)
    reminder_thread.start()
    url = f"http://localhost:{port}"
    print(f"挑战杯问题记录已启动：{url}")
    webbrowser.open(url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()
        print("程序已退出。")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run all tests**

Run:

```powershell
conda activate forskills
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 3: Start app manually**

Run:

```powershell
conda activate forskills
python app.py
```

Expected: terminal prints `挑战杯问题记录已启动：http://localhost:8787` or a nearby port, and the browser opens.

- [ ] **Step 4: Manual API smoke test**

With `python app.py` running, open another PowerShell and run:

```powershell
Invoke-RestMethod -Uri http://localhost:8787/api/issues
```

Expected: returns an empty JSON array or existing issues.

- [ ] **Step 5: Commit app entry**

Run:

```powershell
git add app.py
git commit -m "feat: start local reminder app"
```

---

### Task 7: Startup Script and Repo Hygiene

**Files:**
- Create: `start.bat`
- Create: `data/.gitkeep`
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Create startup script**

Create `start.bat`:

```bat
@echo off
cd /d "%~dp0"
call conda activate forskills
python app.py
pause
```

- [ ] **Step 2: Create data directory marker**

Create `data/.gitkeep` as an empty file.

- [ ] **Step 3: Create `.gitignore`**

Create `.gitignore`:

```gitignore
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/

data/issues.json
data/issues.json.corrupt-*

.superpowers/brainstorm/
```

- [ ] **Step 4: Create README**

Create `README.md`:

```markdown
# 挑战杯问题记录本地提醒程序

一个本地运行的小工具，用来记录挑战杯准备过程中遇到的问题，并在设定时间提醒自己查看。

## 功能

- 新增、编辑、删除问题记录
- 每条记录设置独立提醒时间
- 标记已处理
- 数据保存在本项目的 `data/issues.json`
- 双击 `start.bat` 启动

## 使用方法

1. 确认电脑已安装 Conda，并且存在 `forskills` 环境。
2. 双击 `start.bat`。
3. 浏览器会自动打开本地页面。
4. 新增问题并设置提醒时间。
5. 保持程序窗口运行，到点后电脑会弹出提醒。

## 数据说明

个人数据保存在：

```text
data/issues.json
```

该文件已被 `.gitignore` 忽略，不会上传到 GitHub。

## 开发测试

```powershell
conda activate forskills
python -m unittest discover -s tests -v
```
```

- [ ] **Step 5: Run tests**

Run:

```powershell
conda activate forskills
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit startup and docs**

Run:

```powershell
git add start.bat data/.gitkeep .gitignore README.md
git commit -m "docs: add startup and usage instructions"
```

---

### Task 8: End-to-End Manual Verification

**Files:**
- No new files.

- [ ] **Step 1: Start app from script**

Run:

```powershell
.\start.bat
```

Expected: app starts, browser opens, no Python traceback appears.

- [ ] **Step 2: Verify create and persist**

In the browser:

1. Add title `测试：挑战杯提醒`.
2. Add detail `这是端到端测试记录`.
3. Set reminder time to two minutes from now.
4. Save.
5. Refresh browser.

Expected: record is still visible after refresh.

- [ ] **Step 3: Verify JSON file location**

Run:

```powershell
Get-Content -Raw data\issues.json
```

Expected: JSON contains the test issue and lives inside this project folder.

- [ ] **Step 4: Verify reminder**

Keep the app running until the reminder time.

Expected: a Windows message box appears with the issue title/detail. The page also shows a reminder message within the next polling interval.

- [ ] **Step 5: Verify mark done**

In the browser, click `标记已处理`.

Expected: issue status changes to `已处理`, and it no longer appears under `待处理`.

- [ ] **Step 6: Commit final verification note if README changed**

If README needs an extra troubleshooting note discovered during verification, update it and run:

```powershell
git add README.md
git commit -m "docs: add verification notes"
```

---

### Task 9: GitHub Upload

**Files:**
- Uses existing repository files.

- [ ] **Step 1: Confirm Git state**

Run:

```powershell
git status
```

Expected: clean working tree except personal runtime files ignored by `.gitignore`.

- [ ] **Step 2: Confirm or create GitHub repository**

Use one of these exact options:

Option A, user already has a GitHub repository URL:

```powershell
git remote add origin https://github.com/<your-user>/<your-repo>.git
```

Option B, GitHub CLI is installed and user wants a new private repository:

```powershell
gh repo create challenge-cup-reminder --private --source . --remote origin
```

Option C, GitHub CLI is installed and user wants a new public repository:

```powershell
gh repo create challenge-cup-reminder --public --source . --remote origin
```

- [ ] **Step 3: Push to GitHub**

Run:

```powershell
git branch -M main
git push -u origin main
```

Expected: GitHub shows the project files. `data/issues.json` is not uploaded.

---

## Self-Review

- Spec coverage: storage, local startup, JSON in project folder, browser UI, per-issue reminder, local notification fallback, testing, and GitHub upload are all mapped to tasks.
- Placeholder scan: no unresolved placeholders or undefined implementation tasks remain.
- Type consistency: issue fields are consistently `id`, `title`, `detail`, `remind_at`, `status`, `created_at`, `updated_at`, `notified`.
- Scope check: this is a single local MVP. UI beautification remains outside this initial complete version by user preference.
