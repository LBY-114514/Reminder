import base64
import subprocess
import sys


DEFAULT_MESSAGE = "记得查看这条记录。"
MAX_MESSAGE_LENGTH = 500
STARTUP_TIMEOUT_SECONDS = 0.3


def notify_issue(issue):
    title = f"挑战杯提醒：{issue['title']}"
    detail = issue.get("detail") or DEFAULT_MESSAGE
    message = str(detail)[:MAX_MESSAGE_LENGTH]

    if sys.platform != "win32":
        return False

    encoded_title = base64.b64encode(title.encode("utf-8")).decode("ascii")
    encoded_message = base64.b64encode(message.encode("utf-8")).decode("ascii")
    script = "\n".join(
        [
            f"$titleBytes = [Convert]::FromBase64String('{encoded_title}')",
            f"$messageBytes = [Convert]::FromBase64String('{encoded_message}')",
            "$title = [Text.Encoding]::UTF8.GetString($titleBytes)",
            "$message = [Text.Encoding]::UTF8.GetString($messageBytes)",
            "Add-Type -AssemblyName PresentationFramework",
            "[System.Windows.MessageBox]::Show($message, $title) | Out-Null",
        ]
    )
    encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        process = subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                encoded_script,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except OSError:
        return False

    try:
        process.wait(timeout=STARTUP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return True

    return False
