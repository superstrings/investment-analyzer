#!/bin/bash
# Claude CLI auth keepalive - periodically check and refresh OAuth token.
# Designed to run via crontab every 2 hours to prevent token expiry.
#
# How it works:
#   1. Calls `claude auth status` to check current login state
#   2. If logged in, runs a minimal `claude -p` to trigger OAuth token refresh
#   3. If not logged in, checks Keychain to distinguish service outage vs real expiry
#   4. All results logged to logs/claude_auth.log
#
# Crontab entry (every 2 hours, 6am-11pm on weekdays):
#   0 6,8,10,12,14,16,18,20,22 * * 1-5 cd /path/to/project && scripts/claude_auth_keepalive.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/claude_auth.log"

# Source shared cron environment (sets HOME, PATH, proxy, etc.)
source "$SCRIPT_DIR/run-with-proxy.sh"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Check if Keychain has a non-expired OAuth token.
# Returns 0 if valid token exists, 1 otherwise.
check_keychain_token() {
    security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null \
        | "$PROJECT_DIR/.venv/bin/python" -c "
import json, sys, time
try:
    data = json.loads(sys.stdin.read())
    expires = data.get('claudeAiOauth', {}).get('expiresAt', 0)
    now_ms = int(time.time() * 1000)
    sys.exit(0 if expires > now_ms else 1)
except:
    sys.exit(1)
"
}

# Resolve actual claude binary (bypass asdf shim)
CLAUDE_BIN="$(ls -1t "$HOME/.asdf/installs/nodejs"/*/bin/claude 2>/dev/null | head -1)"
if [ -z "$CLAUDE_BIN" ]; then
    CLAUDE_BIN="claude"  # fallback
fi

# Step 1: Check auth status (local check, no network needed)
AUTH_OUTPUT=$($CLAUDE_BIN auth status 2>&1) || true

if echo "$AUTH_OUTPUT" | grep -q '"loggedIn": true'; then
    # Step 2: Trigger token refresh with a minimal prompt
    REFRESH_OUTPUT=$(timeout 30 $CLAUDE_BIN -p "ok" --output-format text --max-turns 1 2>&1) || true

    if [ -n "$REFRESH_OUTPUT" ] && [ ${#REFRESH_OUTPUT} -gt 0 ]; then
        log "AUTH_OK - token refreshed (${#REFRESH_OUTPUT} chars)"
    else
        log "AUTH_WARN - logged in but refresh returned empty"
    fi
else
    # Step 3: Distinguish service outage vs real auth expiry
    if check_keychain_token; then
        log "AUTH_WARN - claude auth status reports not logged in, but Keychain token still valid. Likely Claude service outage. Output: $AUTH_OUTPUT"
    else
        log "AUTH_FAIL - not logged in, Keychain token expired/missing. Output: $AUTH_OUTPUT"

        # Send DingTalk alert only for real auth expiry
        if [ -f "$PROJECT_DIR/.venv/bin/python" ]; then
            "$PROJECT_DIR/.venv/bin/python" -c "
import sys; sys.path.insert(0, '$PROJECT_DIR')
try:
    from services.dingtalk_service import create_dingtalk_service
    d = create_dingtalk_service()
    d.send_markdown('Claude CLI 认证过期', '## Claude CLI 认证过期\n\n请在本机执行 \`claude /login\` 重新登录')
except: pass
" 2>/dev/null || true
        fi
    fi
fi
