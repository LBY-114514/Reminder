import http.client
import base64
import json
import socket
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

from challenge_reminder.server import create_server


class FakeStore:
    def __init__(self):
        self.data_location_selected = False
        self.issues = [
            {
                "id": "issue-1",
                "title": "准备材料",
                "detail": "整理申报材料",
                "remind_at": "2026-05-10T18:30:00+08:00",
                "status": "pending",
                "notified": False,
            }
        ]

    def list_issues(self):
        return self.issues

    def add_issue(self, title, detail, remind_at):
        if not title:
            raise ValueError("title must not be empty")
        issue = {
            "id": f"issue-{len(self.issues) + 1}",
            "title": title,
            "detail": detail,
            "remind_at": remind_at,
            "status": "pending",
            "notified": False,
        }
        self.issues.append(issue)
        return issue

    def update_issue(self, issue_id, payload):
        issue = self.find_issue(issue_id)
        issue.update(payload)
        return issue

    def delete_issue(self, issue_id):
        self.find_issue(issue_id)
        self.issues = [issue for issue in self.issues if issue["id"] != issue_id]

    def mark_done(self, issue_id):
        issue = self.find_issue(issue_id)
        issue["status"] = "done"
        return issue

    def mark_notified(self, issue_id):
        issue = self.find_issue(issue_id)
        issue["notified"] = True
        return issue

    def find_issue(self, issue_id):
        for issue in self.issues:
            if issue["id"] == issue_id:
                return issue
        raise KeyError(issue_id)

    def data_location_info(self):
        return {
            "path": "C:\\Data\\issues.json",
            "folder": "C:\\Data",
            "configured": False,
            "config_path": "C:\\Config\\config.json",
        }

    def choose_data_folder(self):
        self.data_location_selected = True
        return {
            "path": "D:\\Chosen\\issues.json",
            "folder": "D:\\Chosen",
            "configured": True,
            "config_path": "C:\\Config\\config.json",
            "cancelled": False,
            "migrated": True,
        }

    def set_data_folder(self, folder):
        return {
            "path": f"{folder}\\issues.json",
            "folder": folder,
            "configured": True,
            "config_path": "C:\\Config\\config.json",
            "cancelled": False,
            "migrated": True,
        }

    def sound_settings(self):
        return {
            "enabled": False,
            "path": "C:\\Data\\reminder-sound.mp3",
            "exists": False,
            "file_name": "reminder-sound.mp3",
        }

    def set_sound_enabled(self, enabled):
        info = self.sound_settings()
        info["enabled"] = enabled
        return info

    def save_sound_file(self, filename, content):
        if filename != "ok.mp3":
            raise ValueError("sound file must be an mp3")
        info = self.sound_settings()
        info["enabled"] = True
        info["exists"] = True
        info["size"] = len(content)
        return info


class RaceyStore(FakeStore):
    def __init__(self):
        self.issues = []

    def add_issue(self, title, detail, remind_at):
        issues = list(self.issues)
        time.sleep(0.02)
        issue = {
            "id": title,
            "title": title,
            "detail": detail,
            "remind_at": remind_at,
            "status": "pending",
            "notified": False,
        }
        issues.append(issue)
        self.issues = issues
        return issue


class FakeStartupManager:
    def __init__(self):
        self.enabled = False
        self.actions = []

    def status(self):
        return {
            "available": True,
            "enabled": self.enabled,
            "path": "C:\\Startup\\挑战杯提醒.cmd",
            "app_path": "D:\\Apps\\挑战杯提醒.exe",
        }

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.actions.append(enabled)
        return self.status()


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.web_dir = Path(self.temp_dir.name) / "web"
        self.web_dir.mkdir()
        (self.web_dir / "index.html").write_text("<h1>首页</h1>", encoding="utf-8")
        (self.web_dir / "app.js").write_text("console.log('ok');", encoding="utf-8")
        (Path(self.temp_dir.name) / "secret.txt").write_text("secret", encoding="utf-8")

        self.startup_manager = FakeStartupManager()
        self.server = create_server(
            "127.0.0.1",
            0,
            FakeStore(),
            self.web_dir,
            startup_manager=self.startup_manager,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection(self.host, self.port, timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        data = response.read()
        connection.close()
        return response, data

    def assert_json_response(self, response, data, status):
        self.assertEqual(status, response.status)
        self.assertEqual("application/json; charset=utf-8", response.getheader("Content-Type"))
        return json.loads(data.decode("utf-8")) if data else None

    def test_get_api_issues_returns_json(self):
        response, data = self.request("GET", "/api/issues")

        payload = self.assert_json_response(response, data, 200)
        self.assertEqual("准备材料", payload[0]["title"])

    def test_unknown_api_paths_return_json_404(self):
        for path in ["/api", "/api/missing", "/api/issues//abc"]:
            with self.subTest(path=path):
                response, data = self.request("GET", path)

                payload = self.assert_json_response(response, data, 404)
                self.assertEqual({"error": "not found"}, payload)

    def test_invalid_json_body_returns_json_400(self):
        response, data = self.request(
            "POST",
            "/api/issues",
            body="{broken",
            headers={"Content-Type": "application/json"},
        )

        payload = self.assert_json_response(response, data, 400)
        self.assertEqual({"error": "invalid json"}, payload)

    def test_post_api_issues_creates_issue(self):
        response, data = self.request(
            "POST",
            "/api/issues",
            body=json.dumps(
                {
                    "title": "提交申报书",
                    "detail": "上传附件",
                    "remind_at": "2026-05-10T18:30:00+08:00",
                }
            ),
            headers={"Content-Type": "application/json"},
        )

        payload = self.assert_json_response(response, data, 201)
        self.assertEqual("提交申报书", payload["title"])
        self.assertEqual("pending", payload["status"])

    def test_put_api_issue_updates_issue(self):
        response, data = self.request(
            "PUT",
            "/api/issues/issue-1",
            body=json.dumps({"title": "更新标题"}),
            headers={"Content-Type": "application/json"},
        )

        payload = self.assert_json_response(response, data, 200)
        self.assertEqual("更新标题", payload["title"])

    def test_delete_api_issue_removes_issue(self):
        response, data = self.request("DELETE", "/api/issues/issue-1")

        payload = self.assert_json_response(response, data, 200)
        self.assertEqual({"ok": True}, payload)

        response, data = self.request("GET", "/api/issues")
        payload = self.assert_json_response(response, data, 200)
        self.assertEqual([], payload)

    def test_post_api_issue_done_marks_done(self):
        response, data = self.request("POST", "/api/issues/issue-1/done")

        payload = self.assert_json_response(response, data, 200)
        self.assertEqual("done", payload["status"])

    def test_get_due_reminders_returns_due_items_for_in_page_alerts_even_after_native_notification(self):
        now = datetime.now().astimezone()
        self.server.RequestHandlerClass.store.issues = [
            {
                "id": "due",
                "title": "到点提醒",
                "detail": "",
                "remind_at": (now - timedelta(minutes=1)).isoformat(),
                "status": "pending",
                "notified": False,
            },
            {
                "id": "future",
                "title": "未来提醒",
                "detail": "",
                "remind_at": (now + timedelta(minutes=1)).isoformat(),
                "status": "pending",
                "notified": False,
            },
            {
                "id": "done",
                "title": "已完成",
                "detail": "",
                "remind_at": (now - timedelta(minutes=1)).isoformat(),
                "status": "done",
                "notified": False,
            },
            {
                "id": "notified",
                "title": "已通知",
                "detail": "",
                "remind_at": (now - timedelta(minutes=1)).isoformat(),
                "status": "pending",
                "notified": True,
            },
        ]

        response, data = self.request("GET", "/api/reminders/due")

        payload = self.assert_json_response(response, data, 200)
        self.assertEqual(["due", "notified"], [issue["id"] for issue in payload])
        self.assertFalse(self.server.RequestHandlerClass.store.find_issue("due")["notified"])

        response, data = self.request("GET", "/api/reminders/due")

        payload = self.assert_json_response(response, data, 200)
        self.assertEqual(["due", "notified"], [issue["id"] for issue in payload])

        self.server.RequestHandlerClass.store.mark_notified("due")

        response, data = self.request("GET", "/api/reminders/due")

        payload = self.assert_json_response(response, data, 200)
        self.assertEqual(["due", "notified"], [issue["id"] for issue in payload])

    def test_get_data_location_returns_json(self):
        response, data = self.request("GET", "/api/data-location")

        payload = self.assert_json_response(response, data, 200)
        self.assertEqual("C:\\Data\\issues.json", payload["path"])
        self.assertFalse(payload["configured"])

    def test_get_startup_returns_status(self):
        response, data = self.request("GET", "/api/startup")

        payload = self.assert_json_response(response, data, 200)
        self.assertEqual(
            {
                "available": True,
                "enabled": False,
                "path": "C:\\Startup\\挑战杯提醒.cmd",
                "app_path": "D:\\Apps\\挑战杯提醒.exe",
            },
            payload,
        )

    def test_post_startup_enables_and_disables_startup(self):
        response, data = self.request(
            "POST",
            "/api/startup",
            body=json.dumps({"enabled": True}),
            headers={"Content-Type": "application/json"},
        )

        payload = self.assert_json_response(response, data, 200)
        self.assertTrue(payload["enabled"])

        response, data = self.request(
            "POST",
            "/api/startup",
            body=json.dumps({"enabled": False}),
            headers={"Content-Type": "application/json"},
        )

        payload = self.assert_json_response(response, data, 200)
        self.assertFalse(payload["enabled"])
        self.assertEqual([True, False], self.startup_manager.actions)

    def test_post_startup_requires_boolean_enabled(self):
        response, data = self.request(
            "POST",
            "/api/startup",
            body=json.dumps({"enabled": "yes"}),
            headers={"Content-Type": "application/json"},
        )

        payload = self.assert_json_response(response, data, 400)
        self.assertEqual({"error": "enabled must be boolean"}, payload)

    def test_post_data_location_select_returns_selected_folder_info(self):
        response, data = self.request("POST", "/api/data-location/select")

        payload = self.assert_json_response(response, data, 200)
        self.assertEqual("D:\\Chosen\\issues.json", payload["path"])
        self.assertTrue(payload["configured"])
        self.assertTrue(self.server.RequestHandlerClass.store.data_location_selected)

    def test_post_data_location_sets_manual_folder_path(self):
        response, data = self.request(
            "POST",
            "/api/data-location",
            body=json.dumps({"folder": "E:\\ReminderData"}),
            headers={"Content-Type": "application/json"},
        )

        payload = self.assert_json_response(response, data, 200)
        self.assertEqual("E:\\ReminderData", payload["folder"])
        self.assertEqual("E:\\ReminderData\\issues.json", payload["path"])

    def test_post_data_location_rejects_empty_folder_path(self):
        response, data = self.request(
            "POST",
            "/api/data-location",
            body=json.dumps({"folder": "  "}),
            headers={"Content-Type": "application/json"},
        )

        payload = self.assert_json_response(response, data, 400)
        self.assertEqual({"error": "folder is required"}, payload)

    def test_get_sound_returns_settings(self):
        response, data = self.request("GET", "/api/sound")

        payload = self.assert_json_response(response, data, 200)
        self.assertEqual("C:\\Data\\reminder-sound.mp3", payload["path"])
        self.assertFalse(payload["enabled"])

    def test_post_sound_enabled_updates_boolean_setting(self):
        response, data = self.request(
            "POST",
            "/api/sound/enabled",
            body=json.dumps({"enabled": True}),
            headers={"Content-Type": "application/json"},
        )

        payload = self.assert_json_response(response, data, 200)
        self.assertTrue(payload["enabled"])

    def test_post_sound_file_decodes_mp3_upload(self):
        response, data = self.request(
            "POST",
            "/api/sound/file",
            body=json.dumps(
                {
                    "filename": "ok.mp3",
                    "content_base64": base64.b64encode(b"mp3 bytes").decode("ascii"),
                }
            ),
            headers={"Content-Type": "application/json"},
        )

        payload = self.assert_json_response(response, data, 200)
        self.assertTrue(payload["enabled"])
        self.assertTrue(payload["exists"])
        self.assertEqual(9, payload["size"])

    def raw_request(self, request):
        with socket.create_connection((self.host, self.port), timeout=5) as client:
            client.sendall(request)
            chunks = []
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks)

    def test_non_integer_content_length_returns_json_400(self):
        raw_response = self.raw_request(
            b"POST /api/issues HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: nope\r\n"
            b"\r\n"
            b"{}"
        )

        self.assertIn(b"HTTP/1.0 400", raw_response)
        self.assertIn(b"Content-Type: application/json; charset=utf-8", raw_response)
        self.assertIn(b'{"error": "invalid content length"}', raw_response)

    def test_negative_content_length_returns_json_400(self):
        raw_response = self.raw_request(
            b"POST /api/issues HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: -1\r\n"
            b"\r\n"
            b"{}"
        )

        self.assertIn(b"HTTP/1.0 400", raw_response)
        self.assertIn(b"Content-Type: application/json; charset=utf-8", raw_response)
        self.assertIn(b'{"error": "invalid content length"}', raw_response)

    def test_unsupported_api_methods_return_json_error(self):
        for method in ["PATCH", "OPTIONS"]:
            with self.subTest(method=method):
                response, data = self.request(method, "/api/issues")

                payload = self.assert_json_response(response, data, 405)
                self.assertEqual({"error": "method not allowed"}, payload)

        response, data = self.request("HEAD", "/api/issues")

        self.assertEqual(405, response.status)
        self.assertEqual("application/json; charset=utf-8", response.getheader("Content-Type"))
        self.assertEqual(b"", data)

    def test_malformed_issue_path_returns_json_404(self):
        response, data = self.request(
            "PUT",
            "/api/issues//issue-1",
            body=json.dumps({"title": "误匹配"}),
            headers={"Content-Type": "application/json"},
        )

        payload = self.assert_json_response(response, data, 404)
        self.assertEqual({"error": "not found"}, payload)

    def test_static_path_traversal_is_rejected(self):
        response, data = self.request("GET", "/%2e%2e/secret.txt")

        self.assertEqual(404, response.status)
        self.assertNotEqual(b"secret", data)

    def test_static_file_is_served(self):
        response, data = self.request("GET", "/app.js")

        self.assertEqual(200, response.status)
        self.assertEqual("application/javascript", response.getheader("Content-Type"))
        self.assertEqual(b"console.log('ok');", data)

    def test_concurrent_posts_are_serialized_without_lost_records(self):
        self.server.RequestHandlerClass.store = RaceyStore()

        def post_issue(index):
            response, data = self.request(
                "POST",
                "/api/issues",
                body=json.dumps(
                    {
                        "title": f"issue-{index}",
                        "detail": "",
                        "remind_at": "2026-05-10T18:30:00+08:00",
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
            return response.status, data

        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(post_issue, range(20)))

        self.assertTrue(all(status == 201 for status, _data in results))
        response, data = self.request("GET", "/api/issues")
        payload = self.assert_json_response(response, data, 200)
        self.assertEqual(20, len(payload))


if __name__ == "__main__":
    unittest.main()
