from datetime import datetime


def due_issues(issues, now, include_notified=False):
    due = []
    for issue in issues:
        if issue.get("status") != "pending":
            continue
        if issue.get("notified") and not include_notified:
            continue
        remind_at = datetime.fromisoformat(issue["remind_at"])
        if remind_at <= now:
            due.append(issue)
    return due
