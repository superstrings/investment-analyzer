"""
Claude CLI runner for background analysis tasks.

Invokes `claude -p` as a subprocess and handles results asynchronously.
Uses asyncio.create_subprocess_exec for safe process execution.
"""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Callable, Optional

from config import settings

logger = logging.getLogger(__name__)

PROJECT_DIR = str(Path(__file__).parent.parent)


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
    try:
        # Using create_subprocess_exec avoids shell injection
        process = await asyncio.create_subprocess_exec(
            "claude",
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
            ["claude", "-p", prompt, "--output-format", "text"],
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
