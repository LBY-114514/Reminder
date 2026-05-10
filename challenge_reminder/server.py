import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


class ChallengeReminderHandler(BaseHTTPRequestHandler):
    store = None
    store_lock = None
    web_dir = None

    def do_GET(self):
        if self.path_info == "/api/issues":
            with self.store_lock:
                issues = self.store.list_issues()
            self._send_json(200, issues)
            return

        if self._is_api_path():
            self._send_json_error(404, "not found")
            return

        self._serve_static()

    def do_POST(self):
        if self.path_info == "/api/issues":
            payload = self._read_json_body()
            if payload is None:
                return

            try:
                with self.store_lock:
                    issue = self.store.add_issue(
                        payload.get("title"),
                        payload.get("detail"),
                        payload.get("remind_at"),
                    )
            except ValueError as exc:
                self._send_json_error(400, str(exc))
                return

            self._send_json(201, issue)
            return

        issue_id, action = self._issue_route()
        if issue_id and action == "done":
            try:
                with self.store_lock:
                    issue = self.store.mark_done(issue_id)
            except KeyError:
                self._send_json_error(404, "not found")
                return

            self._send_json(200, issue)
            return

        self._send_json_error(404, "not found")

    def do_PUT(self):
        issue_id, action = self._issue_route()
        if not issue_id or action is not None:
            self._send_json_error(404, "not found")
            return

        payload = self._read_json_body()
        if payload is None:
            return

        try:
            with self.store_lock:
                issue = self.store.update_issue(issue_id, payload)
        except ValueError as exc:
            self._send_json_error(400, str(exc))
            return
        except KeyError:
            self._send_json_error(404, "not found")
            return

        self._send_json(200, issue)

    def do_DELETE(self):
        issue_id, action = self._issue_route()
        if not issue_id or action is not None:
            self._send_json_error(404, "not found")
            return

        try:
            with self.store_lock:
                self.store.delete_issue(issue_id)
        except KeyError:
            self._send_json_error(404, "not found")
            return

        self._send_json(200, {"ok": True})

    def do_HEAD(self):
        if self._is_api_path():
            self._send_json_error(405, "method not allowed", include_body=False)
            return

        self.send_error(405)

    def do_PATCH(self):
        if self._is_api_path():
            self._send_json_error(405, "method not allowed")
            return

        self.send_error(405)

    @property
    def path_info(self):
        return urlparse(self.path).path

    def _issue_route(self):
        parts = self.path_info.lstrip("/").split("/")
        if len(parts) == 3 and parts[:2] == ["api", "issues"]:
            return parts[2], None
        if len(parts) == 4 and parts[:2] == ["api", "issues"]:
            return parts[2], parts[3]
        return None, None

    def _is_api_path(self):
        return self.path_info == "/api" or self.path_info.startswith("/api/")

    def _read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._send_json_error(400, "invalid content length")
            return None

        if length < 0:
            self._send_json_error(400, "invalid content length")
            return None

        if length == 0:
            return {}

        raw_body = self.rfile.read(length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json_error(400, "invalid json")
            return None

        if not isinstance(payload, dict):
            self._send_json_error(400, "json body must be an object")
            return None

        return payload

    def _serve_static(self):
        path = self.path_info
        if path == "/":
            path = "/index.html"

        relative_path = unquote(path.lstrip("/"))
        root = Path(self.web_dir).resolve()
        file_path = (root / relative_path).resolve()

        if not self._is_relative_to(file_path, root) or not file_path.is_file():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _is_relative_to(self, path, root):
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return True

    def _send_json(self, status, payload, include_body=True):
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if include_body:
            self.wfile.write(content)

    def _send_json_error(self, status, message, include_body=True):
        self._send_json(status, {"error": message}, include_body=include_body)

    def send_error(self, code, message=None, explain=None):
        if self._is_api_path():
            status = 405 if code == 501 else code
            error = "method not allowed" if status == 405 else message or "not found"
            self._send_json_error(status, error, include_body=self.command != "HEAD")
            return

        super().send_error(code, message=message, explain=explain)

    def log_message(self, format, *args):
        return


def create_server(host, port, store, web_dir):
    class Handler(ChallengeReminderHandler):
        pass

    Handler.store = store
    Handler.store_lock = threading.RLock()
    Handler.web_dir = Path(web_dir)
    return ThreadingHTTPServer((host, port), Handler)
