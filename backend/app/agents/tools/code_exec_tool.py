"""Deno sandbox code execution tool for CrewAI agents.

Executes generated JavaScript code in a sandboxed Deno runtime
to verify correctness before delivering to students. Code that
fails execution is flagged for revision.
"""

import asyncio
import logging
import os
import tempfile
import uuid

from crewai.tools import tool

from app.config import settings

logger = logging.getLogger(__name__)

# Timeout for code execution (seconds)
EXECUTION_TIMEOUT = 10


@tool("execute_javascript")
def execute_javascript(code: str) -> str:
    """Execute JavaScript code in a Deno sandbox and return the output.

    Use this to verify that generated JavaScript code compiles and runs
    correctly. Always test code before delivering to students.

    Args:
        code: JavaScript code string to execute. Must be complete and
              self-contained (no external imports unless from deno.land).
    Returns:
        JSON string with keys: success (bool), stdout (str), stderr (str),
        exit_code (int), error (str or null).
    """
    import json

    if not code or not code.strip():
        return json.dumps({
            "success": False,
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "error": "Empty code string provided.",
        }, ensure_ascii=False)

    # Write code to temp file for Deno execution
    tmp_path = os.path.join(
        tempfile.gettempdir(),
        f"rj_sandbox_{uuid.uuid4().hex[:8]}.js",
    )

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(code)

        deno_path = settings.DENO_PATH

        try:
            result = asyncio.run(
                _run_deno(deno_path, tmp_path)
            )
        except RuntimeError:
            # Fallback for nested event loop: use subprocess directly
            import subprocess
            try:
                proc = subprocess.run(
                    [deno_path, "run", "--no-prompt", tmp_path],
                    capture_output=True, text=True, timeout=EXECUTION_TIMEOUT,
                )
                result = {
                    "success": proc.returncode == 0,
                    "stdout": proc.stdout[:2000],
                    "stderr": proc.stderr[:2000],
                    "exit_code": proc.returncode,
                    "error": None if proc.returncode == 0 else f"Exit code {proc.returncode}",
                }
            except subprocess.TimeoutExpired:
                result = {
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                    "error": f"执行超时（{EXECUTION_TIMEOUT}秒）",
                }
            except FileNotFoundError:
                result = {
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                    "error": f"Deno 未安装或路径错误: {deno_path}",
                }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.exception("Code execution failed")
        return json.dumps({
            "success": False,
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "error": str(e),
        }, ensure_ascii=False)

    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


async def _run_deno(deno_path: str, script_path: str) -> dict:
    """Run a Deno script asynchronously with timeout."""
    proc = await asyncio.create_subprocess_exec(
        deno_path, "run", "--no-prompt", script_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=EXECUTION_TIMEOUT
        )
        return {
            "success": proc.returncode == 0,
            "stdout": stdout.decode("utf-8", errors="replace")[:2000],
            "stderr": stderr.decode("utf-8", errors="replace")[:2000],
            "exit_code": proc.returncode,
            "error": None if proc.returncode == 0 else f"Exit code {proc.returncode}",
        }
    except asyncio.TimeoutError:
        proc.kill()
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "error": f"执行超时（{EXECUTION_TIMEOUT}秒）",
        }
