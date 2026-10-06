from datetime import datetime, timezone


LOGS: list[dict] = []


def add_log(
    level: str,
    service: str,
    message: str,
):

    entry = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),

        "level": level,

        "service": service,

        "message": message,
    }

    LOGS.append(entry)

    return entry


def get_logs(
    level: str | None = None,
    service: str | None = None,
    limit: int = 100,
):

    logs = LOGS

    if level:
        logs = [
            x for x in logs
            if x["level"] == level
        ]

    if service:
        logs = [
            x for x in logs
            if x["service"] == service
        ]

    return logs[-limit:]