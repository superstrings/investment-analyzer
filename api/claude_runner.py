"""
Claude CLI runner for background analysis tasks.

Invokes `claude -p` as a subprocess and handles results asynchronously.
Uses asyncio.create_subprocess_exec for safe process execution.
"""

import asyncio
import glob
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from config import settings

logger = logging.getLogger(__name__)

PROJECT_DIR = str(Path(__file__).parent.parent)


def _find_claude_binary() -> str:
    """Find the actual claude binary, bypassing asdf shims."""
    # 1. Try shutil.which (works if PATH has the real binary)
    found = shutil.which("claude")
    if found:
        real = os.path.realpath(found)
        # If it's NOT a shim (i.e. not a shell script), use it directly
        if not real.endswith("/shims/claude"):
            return real

    # 2. Look in asdf installs (handles asdf shim issue in non-interactive shells)
    home = os.environ.get("HOME", os.path.expanduser("~"))
    matches = sorted(
        glob.glob(os.path.join(home, ".asdf/installs/nodejs/*/bin/claude")),
        reverse=True,
    )
    if matches:
        return matches[0]

    # 3. Common global install locations
    for candidate in ["/usr/local/bin/claude", "/opt/homebrew/bin/claude"]:
        if os.path.isfile(candidate):
            return candidate

    return "claude"  # fallback


CLAUDE_BIN = _find_claude_binary()
logger.info("Claude CLI resolved to: %s", CLAUDE_BIN)


async def run_claude(
    prompt: str,
    callback: Optional[Callable] = None,
    timeout: int = 300,
) -> str:
    """
    Run claude CLI with a prompt and optional callback.

    Uses asyncio.create_subprocess_exec (not shell) for safety.

    Args:
        prompt: The prompt to send to Claude
        callback: Async function to call with the result
        timeout: Timeout in seconds

    Returns:
        Claude's text response
    """
    process = None
    try:
        # Using create_subprocess_exec avoids shell injection
        process = await asyncio.create_subprocess_exec(
            CLAUDE_BIN,
            "-p",
            prompt,
            "--output-format",
            "text",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=PROJECT_DIR,
            env=settings.proxy.get_subprocess_env(),
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

        output = stdout.decode("utf-8").strip()

        if process.returncode != 0:
            error = stderr.decode("utf-8").strip()
            logger.error("Claude CLI error (rc=%d): %s", process.returncode, error)
            output = f"分析出错: {error}" if error else "分析出错"

        if callback:
            await callback(output)

        return output

    except asyncio.TimeoutError:
        logger.error("Claude CLI timed out after %ds", timeout)
        # Kill the subprocess to avoid zombie processes
        if process and process.returncode is None:
            try:
                process.terminate()
                await asyncio.sleep(2)
                if process.returncode is None:
                    process.kill()
            except ProcessLookupError:
                pass
        error_msg = f"分析超时 ({timeout}秒)"
        if callback:
            await callback(error_msg)
        return error_msg

    except FileNotFoundError:
        logger.error("Claude CLI not found in PATH")
        error_msg = "Claude CLI 未安装"
        if callback:
            await callback(error_msg)
        return error_msg

    except Exception as e:
        logger.error("Claude CLI failed: %s", e)
        error_msg = f"分析失败: {e}"
        if callback:
            await callback(error_msg)
        return error_msg


def run_claude_sync(prompt: str, timeout: int = 300) -> str:
    """Synchronous version using subprocess.run with exec (no shell)."""
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=PROJECT_DIR,
            env=settings.proxy.get_subprocess_env(),
        )
        if result.returncode != 0:
            logger.error("Claude CLI error: %s", result.stderr)
            return f"分析出错: {result.stderr}" if result.stderr else "分析出错"
        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        return f"分析超时 ({timeout}秒)"
    except FileNotFoundError:
        return "Claude CLI 未安装"
    except Exception as e:
        return f"分析失败: {e}"
