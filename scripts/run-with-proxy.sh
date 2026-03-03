#!/bin/bash
# Cron environment wrapper - sets up complete environment for cron tasks.
#
# Usage as wrapper:  scripts/run-with-proxy.sh <command> [args...]
# Usage as source:   source scripts/run-with-proxy.sh  (only sets env, no exec)
#
# Ensures HOME, PATH, proxy, and other env vars are available so that
# Python scripts and Claude CLI work correctly under cron's minimal env.
#
# All crontab entries should use this wrapper:
#   0 8 * * 1-5 cd $PROJECT && scripts/run-with-proxy.sh .venv/bin/python scripts/cron_workflow.py sync

# --- Core environment ---
export HOME="/Users/dyson"
export USER="dyson"
export LANG="en_US.UTF-8"
export LC_ALL="en_US.UTF-8"

# --- PATH: asdf (python/node), homebrew, system ---
export PATH="/Users/dyson/.asdf/shims:/Users/dyson/.asdf/installs/nodejs/22.11.0/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin"

# --- Proxy for Claude CLI / web access ---
export HTTP_PROXY="http://127.0.0.1:8118"
export HTTPS_PROXY="http://127.0.0.1:8118"
export ALL_PROXY="http://127.0.0.1:8118"
export http_proxy="http://127.0.0.1:8118"
export https_proxy="http://127.0.0.1:8118"
export all_proxy="http://127.0.0.1:8118"
export NO_PROXY="localhost,127.0.0.1"
export no_proxy="localhost,127.0.0.1"

# --- Allow Claude CLI to run even inside a Claude Code session ---
unset CLAUDECODE

# Only exec when called as a script (not sourced)
if [ "$0" = "${BASH_SOURCE[0]}" ] && [ $# -gt 0 ]; then
    exec "$@"
fi
