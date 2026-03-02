#!/bin/bash
# Wrapper script to run commands with HTTP proxy enabled.
# Usage: scripts/run-with-proxy.sh <command> [args...]
#
# Used by crontab for Claude CLI tasks that need proxy access.

# Ensure asdf/node paths are available (cron has minimal PATH)
export PATH="/Users/dyson/.asdf/shims:/Users/dyson/.asdf/installs/nodejs/22.11.0/bin:/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"

# Allow Claude CLI to run even if invoked from within a Claude Code session
unset CLAUDECODE

export HTTP_PROXY="http://127.0.0.1:8118"
export HTTPS_PROXY="http://127.0.0.1:8118"
export ALL_PROXY="http://127.0.0.1:8118"
export http_proxy="http://127.0.0.1:8118"
export https_proxy="http://127.0.0.1:8118"
export all_proxy="http://127.0.0.1:8118"
export NO_PROXY="localhost,127.0.0.1"
export no_proxy="localhost,127.0.0.1"

exec "$@"
