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
    script = _toast_script(encoded_title, encoded_message)
    encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        process = subprocess.Popen(
            [
                "powershell.exe",
                "-STA",
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


def _toast_script(encoded_title, encoded_message):
    return "\n".join(
        [
            f"$titleBytes = [Convert]::FromBase64String('{encoded_title}')",
            f"$messageBytes = [Convert]::FromBase64String('{encoded_message}')",
            "$title = [Text.Encoding]::UTF8.GetString($titleBytes)",
            "$message = [Text.Encoding]::UTF8.GetString($messageBytes)",
            "Add-Type -AssemblyName PresentationFramework",
            "Add-Type -AssemblyName PresentationCore",
            "$window = New-Object System.Windows.Window",
            "$window.Title = $title",
            "$window.Width = 390",
            "$window.Height = 220",
            "$window.WindowStartupLocation = 'Manual'",
            "$window.ResizeMode = 'NoResize'",
            "$window.WindowStyle = 'None'",
            "$window.AllowsTransparency = $true",
            "$window.Background = 'Transparent'",
            "$window.Topmost = $true",
            "$window.ShowInTaskbar = $false",
            "$area = [System.Windows.SystemParameters]::WorkArea",
            "$window.Left = $area.Right - $window.Width - 28",
            "$window.Top = $area.Bottom - $window.Height - 34",
            "$shadow = New-Object System.Windows.Media.Effects.DropShadowEffect",
            "$shadow.Color = [System.Windows.Media.Color]::FromRgb(70, 42, 24)",
            "$shadow.BlurRadius = 26",
            "$shadow.ShadowDepth = 8",
            "$shadow.Opacity = 0.28",
            "$border = New-Object System.Windows.Controls.Border",
            "$border.CornerRadius = 22",
            "$border.Padding = 20",
            "$border.Background = '#FFF8ED'",
            "$border.BorderBrush = '#E4CDAE'",
            "$border.BorderThickness = 1",
            "$border.Effect = $shadow",
            "$border.Add_MouseLeftButtonDown({ try { $window.DragMove() } catch {} })",
            "$stack = New-Object System.Windows.Controls.StackPanel",
            "$header = New-Object System.Windows.Controls.TextBlock",
            "$header.Text = '到期提醒'",
            "$header.Foreground = '#C84D2E'",
            "$header.FontSize = 13",
            "$header.FontWeight = 'Bold'",
            "$header.Margin = '0,0,0,8'",
            "$titleText = New-Object System.Windows.Controls.TextBlock",
            "$titleText.Text = $title",
            "$titleText.Foreground = '#24211D'",
            "$titleText.FontSize = 21",
            "$titleText.FontWeight = 'Bold'",
            "$titleText.TextWrapping = 'Wrap'",
            "$messageText = New-Object System.Windows.Controls.TextBlock",
            "$messageText.Text = $message",
            "$messageText.Foreground = '#746C60'",
            "$messageText.FontSize = 14",
            "$messageText.LineHeight = 20",
            "$messageText.TextWrapping = 'Wrap'",
            "$messageText.Margin = '0,10,0,16'",
            "$button = New-Object System.Windows.Controls.Button",
            "$button.Content = '知道了'",
            "$button.Width = 96",
            "$button.Height = 34",
            "$button.HorizontalAlignment = 'Left'",
            "$button.Foreground = 'White'",
            "$button.Background = '#C84D2E'",
            "$button.BorderThickness = 0",
            "$button.FontWeight = 'Bold'",
            "$button.Add_Click({ $window.Close() })",
            "$stack.Children.Add($header) | Out-Null",
            "$stack.Children.Add($titleText) | Out-Null",
            "$stack.Children.Add($messageText) | Out-Null",
            "$stack.Children.Add($button) | Out-Null",
            "$border.Child = $stack",
            "$window.Content = $border",
            "$window.ShowDialog() | Out-Null",
        ]
    )
