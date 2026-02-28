#!/usr/bin/env python3
"""
Preflight check script for Investment Analyzer.

Verifies all prerequisites are ready before starting the web service:
- PostgreSQL connection
- Futu OpenD connection
- Claude CLI login status
- Required directories
- DB migrations

Usage:
    python scripts/preflight.py          # Check only
    python scripts/preflight.py --start  # Check + restart web service
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

LAUNCHD_LABEL = "com.dyson.investment-analyzer"


def ok(msg: str):
    print(f"  {GREEN}✓{RESET} {msg}")


def fail(msg: str):
    print(f"  {RED}✗{RESET} {msg}")


def warn(msg: str):
    print(f"  {YELLOW}!{RESET} {msg}")


def check_postgres() -> bool:
    """Check PostgreSQL connection."""
    print(f"\n{BOLD}PostgreSQL{RESET}")
    try:
        from db.database import check_connection, engine

        if check_connection():
            url = str(engine.url)
            # Mask password if present
            ok(f"Connected: {url}")
            return True
        else:
            fail("Connection failed")
            return False
    except Exception as e:
        fail(f"Connection error: {e}")
        return False


def check_db_tables() -> bool:
    """Check that critical tables exist."""
    print(f"\n{BOLD}Database Tables{RESET}")
    try:
        from sqlalchemy import text

        from db.database import engine

        required_tables = [
            "users",
            "accounts",
            "positions",
            "trades",
            "klines",
            "signals",
            "trading_calendar",
        ]
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
            existing = {row[0] for row in result}

        missing = [t for t in required_tables if t not in existing]
        if missing:
            fail(f"Missing tables: {', '.join(missing)}")
            warn("Run: python scripts/init_db.py init")
            return False
        else:
            ok(f"All {len(required_tables)} required tables exist")
            return True
    except Exception as e:
        fail(f"Table check error: {e}")
        return False


def check_futu() -> bool:
    """Check Futu OpenD connection."""
    print(f"\n{BOLD}Futu OpenD{RESET}")
    try:
        from config import settings

        host = settings.futu.default_host
        port = settings.futu.default_port

        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            ok(f"Listening on {host}:{port}")
            return True
        else:
            fail(f"Not reachable at {host}:{port}")
            warn("Start Futu OpenD application first")
            return False
    except Exception as e:
        fail(f"Connection check error: {e}")
        return False


def check_claude_cli() -> bool:
    """Check Claude CLI is installed and logged in."""
    print(f"\n{BOLD}Claude CLI{RESET}")

    claude_path = shutil.which("claude")
    if not claude_path:
        fail("Claude CLI not found in PATH")
        warn("Install: npm install -g @anthropic-ai/claude-code")
        return False

    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version = result.stdout.strip()
        ok(f"Installed: {version} ({claude_path})")
    except Exception as e:
        fail(f"Version check failed: {e}")
        return False

    # Check login by doing a quick API test
    try:
        result = subprocess.run(
            ["claude", "-p", "reply with just 'ok'", "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and "ok" in result.stdout.lower():
            ok("Authenticated (API key valid)")
            return True
        else:
            stderr = result.stderr.strip()[:200]
            fail(f"Auth check failed: {stderr}")
            warn("Run: claude login")
            return False
    except subprocess.TimeoutExpired:
        warn("Auth check timed out (may still be valid)")
        return True
    except Exception as e:
        fail(f"Auth check error: {e}")
        return False


def check_env() -> bool:
    """Check .env file and key variables."""
    print(f"\n{BOLD}Environment{RESET}")

    env_path = PROJECT_DIR / ".env"
    if not env_path.exists():
        fail(".env file not found")
        warn("Copy .env.example to .env and configure")
        return False

    ok(f".env loaded: {env_path}")

    from config import settings

    issues = []
    if not settings.web.auth_token:
        issues.append("WEB_AUTH_TOKEN not set (auth disabled)")
    if not settings.dingtalk.webhook_url:
        issues.append("DINGTALK_WEBHOOK_URL not set")
    if not settings.web.base_url:
        issues.append("WEB_BASE_URL not set (no links in DingTalk)")

    for issue in issues:
        warn(issue)

    if settings.web.auth_token:
        ok(f"Auth: token-based, user={settings.web.default_user}")
    if settings.web.base_url:
        ok(f"Base URL: {settings.web.base_url}")
    if settings.dingtalk.enabled:
        ok("DingTalk: enabled")

    return len(issues) == 0


def check_directories() -> bool:
    """Ensure required directories exist."""
    print(f"\n{BOLD}Directories{RESET}")

    dirs = [
        PROJECT_DIR / "logs",
        PROJECT_DIR / "charts" / "output",
        PROJECT_DIR / "reports" / "output",
    ]

    all_ok = True
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            warn(f"Created: {d.relative_to(PROJECT_DIR)}")
        else:
            ok(f"{d.relative_to(PROJECT_DIR)}")

    return all_ok


def check_web_service() -> bool:
    """Check if web service is running."""
    print(f"\n{BOLD}Web Service{RESET}")
    try:
        result = subprocess.run(
            ["launchctl", "list", LAUNCHD_LABEL],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            # Parse PID from plist-like output
            pid = "?"
            for line in result.stdout.splitlines():
                if '"PID"' in line:
                    pid = line.split("=")[-1].strip().rstrip(";")
                    break
            ok(f"launchd service active (PID: {pid})")
            return True
        else:
            fail(f"launchd service not loaded")
            warn(f"Load: launchctl load deploy/{LAUNCHD_LABEL}.plist")
            return False
    except Exception as e:
        fail(f"Service check error: {e}")
        return False


def restart_web():
    """Restart the web service via launchd."""
    print(f"\n{BOLD}Restarting Web Service...{RESET}")
    try:
        subprocess.run(["launchctl", "stop", LAUNCHD_LABEL], capture_output=True)
        import time

        time.sleep(2)
        subprocess.run(["launchctl", "start", LAUNCHD_LABEL], capture_output=True)
        time.sleep(3)

        # Verify it's running
        import urllib.request

        try:
            resp = urllib.request.urlopen("http://localhost:8000/login", timeout=5)
            if resp.status == 200:
                ok("Web service restarted successfully")
                ok("Local: http://localhost:8000")
                from config import settings

                if settings.web.base_url:
                    ok(f"External: {settings.web.base_url}")
                return True
        except Exception:
            pass

        fail("Web service not responding after restart")
        warn("Check logs: tail -f logs/server.error.log")
        return False
    except Exception as e:
        fail(f"Restart failed: {e}")
        return False


def main():
    print(f"{BOLD}Investment Analyzer - Preflight Check{RESET}")
    print("=" * 45)

    start_service = "--start" in sys.argv

    results = {
        "env": check_env(),
        "dirs": check_directories(),
        "postgres": check_postgres(),
        "tables": check_db_tables(),
        "futu": check_futu(),
        "web": check_web_service(),
    }

    # Claude CLI is optional (only needed for cron workflows)
    if "--skip-claude" not in sys.argv:
        results["claude"] = check_claude_cli()

    # Summary
    print(f"\n{'=' * 45}")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    critical_ok = results.get("postgres", False) and results.get("env", False)

    if passed == total:
        print(f"{GREEN}{BOLD}All {total} checks passed!{RESET}")
    else:
        failed = total - passed
        color = YELLOW if critical_ok else RED
        print(f"{color}{BOLD}{passed}/{total} checks passed ({failed} issues){RESET}")

    if start_service:
        if critical_ok:
            restart_web()
        else:
            print(f"\n{RED}Cannot start: critical checks failed (PostgreSQL/env){RESET}")
            sys.exit(1)

    if not critical_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
