#!/bin/bash
# Claude CLI auth keepalive - periodically check and refresh OAuth token.
# Designed to run via crontab every 2 hours to prevent token expiry.
#
# How it works:
#   1. Calls `claude auth status` to check current login state
#   2. If logged in, runs a minimal `claude -p` to trigger OAuth token refresh
#   3. If not logged in, logs a warning (manual `claude /login` required)
#   4. All results logged to logs/claude_auth.log
#
# Crontab entry (every 2 hours, 6am-11pm on weekdays):
#   0 6,8,10,12,14,16,18,20,22 * * 1-5 cd /path/to/project && scripts/claude_auth_keepalive.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/claude_auth.log"

# Ensure HOME is set (cron may not provide it)
export HOME="/Users/dyson"

# Ensure PATH includes node/claude
export PATH="/Users/dyson/.asdf/shims:/Users/dyson/.asdf/installs/nodejs/22.11.0/bin:/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"

# Proxy for claude.ai access
export HTTP_PROXY="http://127.0.0.1:8118"
export HTTPS_PROXY="http://127.0.0.1:8118"
export NO_PROXY="localhost,127.0.0.1"

# Allow running even if a Claude Code session is active
unset CLAUDECODE

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Step 1: Check auth status (local check, no network needed)
AUTH_OUTPUT=$(claude auth status 2>&1) || true

if echo "$AUTH_OUTPUT" | grep -q '"loggedIn": true'; then
    # Step 2: Trigger token refresh with a minimal prompt
    REFRESH_OUTPUT=$(timeout 30 claude -p "ok" --output-format text --max-turns 1 2>&1) || true

    if [ -n "$REFRESH_OUTPUT" ] && [ ${#REFRESH_OUTPUT} -gt 0 ]; then
        log "AUTH_OK - token refreshed (${#REFRESH_OUTPUT} chars)"
    else
        log "AUTH_WARN - logged in but refresh returned empty"
    fi
else
    log "AUTH_FAIL - not logged in. Output: $AUTH_OUTPUT"

    # Send DingTalk alert
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
