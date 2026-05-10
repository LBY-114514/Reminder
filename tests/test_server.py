import http.client
import json
import socket
import tempfile
import threading
import unittest
from pathlib import Path

from challenge_reminder.server import create_server


class FakeStore:
    def __init__(self):
        self.issues = [
            {
                "id": "issue-1",
                "title": "准备材料",
                "detail": "整理申报材料",
                "remind_at": "2026-05-10T18:30:00+08:00",
                "status": "pending",
            }
        ]

    def list_issues(self):
        return self.issues

    def add_issue(self, title, detail, remind_at):
        if not title:
            raise ValueError("title must not be empty")
        issue = {"id": "issue-2", "title": title, "detail": detail, "remind_at": remind_at}
        self.issues.append(issue)
        return issue

    def update_issue(self, issue_id, payload):
        if issue_id != "issue-1":
            raise KeyError(issue_id)
        issue = dict(self.issues[0])
        issue.update(payload)
        return issue

    def delete_issue(self, issue_id):
        if issue_id != "issue-1":
            raise KeyError(issue_id)

    def mark_done(self, issue_id):
        if issue_id != "issue-1":
            raise KeyError(issue_id)
        return {**self.issues[0], "status": "done"}


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.web_dir = Path(self.temp_dir.name) / "web"
        self.web_dir.mkdir()
        (self.web_dir / "index.html").write_text("<h1>首页</h1>", encoding="utf-8")
        (self.web_dir / "app.js").write_text("console.log('ok');", encoding="utf-8")
        (Path(self.temp_dir.name) / "secret.txt").write_text("secret", encoding="utf-8")

        self.server = create_server("127.0.0.1", 0, FakeStore(), self.web_dir)
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

    def test_non_integer_content_length_returns_json_400(self):
        with socket.create_connection((self.host, self.port), timeout=5) as client:
            client.sendall(
                b"POST /api/issues HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: nope\r\n"
                b"\r\n"
                b"{}"
            )
            chunks = []
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
            raw_response = b"".join(chunks)

        self.assertIn(b"HTTP/1.0 400", raw_response)
        self.assertIn(b"Content-Type: application/json; charset=utf-8", raw_response)
        self.assertIn(b'{"error": "invalid content length"}', raw_response)

    def test_unsupported_api_methods_return_json_error(self):
        response, data = self.request("PATCH", "/api/issues")

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


if __name__ == "__main__":
    unittest.main()
