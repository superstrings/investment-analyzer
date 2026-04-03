"""Market hours utility for HK, US, and A-share markets."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


MARKET_SESSIONS = {
    "HK": {
        "tz": ZoneInfo("Asia/Hong_Kong"),
        "sessions": [
            (time(9, 30), time(12, 0)),
            (time(13, 0), time(16, 0)),
        ],
    },
    "US": {
        "tz": ZoneInfo("America/New_York"),
        "sessions": [
            (time(9, 30), time(16, 0)),
        ],
    },
    "A": {
        "tz": ZoneInfo("Asia/Shanghai"),
        "sessions": [
            (time(9, 30), time(11, 30)),
            (time(13, 0), time(15, 0)),
        ],
    },
}


def is_market_open(market: str, now: datetime | None = None) -> bool:
    """Check if the given market is currently in a trading session."""
    config = MARKET_SESSIONS.get(market)
    if not config:
        return False

    tz = config["tz"]
    local_now = (now or datetime.now(tz)).astimezone(tz)

    # Skip weekends
    if local_now.weekday() >= 5:
        return False

    current_time = local_now.time()
    for session_start, session_end in config["sessions"]:
        if session_start <= current_time < session_end:
            return True
    return False


def next_market_open(market: str, now: datetime | None = None) -> datetime:
    """Return the next market open time as a timezone-aware datetime."""
    config = MARKET_SESSIONS.get(market)
    if not config:
        raise ValueError(f"Unknown market: {market}")

    tz = config["tz"]
    local_now = (now or datetime.now(tz)).astimezone(tz)

    # Try today and next 7 days
    for day_offset in range(8):
        check_date = local_now.date() + timedelta(days=day_offset)
        check_dt = datetime.combine(check_date, time(0, 0), tzinfo=tz)

        # Skip weekends
        if check_dt.weekday() >= 5:
            continue

        for session_start, _ in config["sessions"]:
            open_dt = datetime.combine(check_date, session_start, tzinfo=tz)
            if open_dt > local_now:
                return open_dt

    # Fallback: next Monday morning
    days_until_monday = (7 - local_now.weekday()) % 7 or 7
    next_monday = local_now.date() + timedelta(days=days_until_monday)
    first_session_start = config["sessions"][0][0]
    return datetime.combine(next_monday, first_session_start, tzinfo=tz)


def seconds_until_market_open(market: str, now: datetime | None = None) -> float:
    """Return seconds until the next market open for the given market."""
    if is_market_open(market, now):
        return 0.0
    next_open = next_market_open(market, now)
    tz = MARKET_SESSIONS[market]["tz"]
    local_now = (now or datetime.now(tz)).astimezone(tz)
    return max(0.0, (next_open - local_now).total_seconds())


def get_active_markets(now: datetime | None = None) -> list[str]:
    """Return list of markets that are currently open."""
    return [m for m in MARKET_SESSIONS if is_market_open(m, now)]
