"""Restricted execution of AI-generated Python scripts.

Defense layers (spec §7, §14):
1. Static AST gate — allowlisted imports only, dangerous builtins and dunder
   attribute access rejected before anything runs.
2. Process isolation — scripts run in a separate python subprocess with a
   stripped environment (no API keys), cwd locked to a per-execution scratch
   directory that contains only a copy of the dataset.
3. Resource limits — CPU time, address space and output file size are capped
   via resource.setrlimit, plus a wall-clock timeout on the subprocess.
"""

import ast
import json
import os
import re
import resource
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ALLOWED_IMPORTS = {
    "pandas",
    "numpy",
    "matplotlib",
    "scipy",
    "json",
    "math",
    "statistics",
    "datetime",
    "re",
    "itertools",
    "collections",
    "functools",
    "random",
    "warnings",
    "typing",
    "textwrap",
}

BLOCKED_NAMES = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
    "input",
    "breakpoint",
    "globals",
    "locals",
    "vars",
    "getattr",
    "setattr",
    "delattr",
    "memoryview",
}

BLOCKED_ATTRIBUTES = {"system", "popen", "fork", "kill", "spawn"}

RESULT_START = "===RESULT_JSON_START==="
RESULT_END = "===RESULT_JSON_END==="

MAX_OUTPUT_CHARS = 20_000


@dataclass
class ExecutionResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    result: dict | None = None
    charts: list[Path] = field(default_factory=list)


def validate_code(code: str) -> list[str]:
    """Return a list of policy violations; empty means the code may run."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"Syntax error: {exc}"]

    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    violations.append(f"Import of '{alias.name}' is not allowed")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if node.level or root not in ALLOWED_IMPORTS:
                violations.append(f"Import from '{node.module}' is not allowed")
        elif isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            violations.append(f"Use of '{node.id}' is not allowed")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") or node.attr in BLOCKED_ATTRIBUTES:
                violations.append(f"Access to attribute '{node.attr}' is not allowed")
    return sorted(set(violations))


def _limit_resources(cpu_seconds: int, memory_mb: int):
    def _apply():
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 5))
        # Address-space cap is best-effort (not enforced on macOS, works on Linux).
        limit = memory_mb * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        except (ValueError, OSError):
            pass
        # Cap any single written file (charts) at 50 MB.
        resource.setrlimit(resource.RLIMIT_FSIZE, (50 * 1024 * 1024,) * 2)

    return _apply


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "\n... [output truncated]"


def _parse_result_json(stdout: str) -> dict | None:
    match = re.search(
        re.escape(RESULT_START) + r"(.*?)" + re.escape(RESULT_END), stdout, re.DOTALL
    )
    if not match:
        return None
    try:
        parsed = json.loads(match.group(1))
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except json.JSONDecodeError:
        return None


def run_code(
    code: str,
    workdir: Path,
    timeout_seconds: int = 60,
    memory_mb: int = 2048,
) -> ExecutionResult:
    """Execute `code` inside `workdir` (already containing the dataset copy)."""
    violations = validate_code(code)
    if violations:
        return ExecutionResult(
            ok=False,
            error="Code rejected by the safety policy:\n- " + "\n- ".join(violations),
        )

    workdir.mkdir(parents=True, exist_ok=True)
    charts_dir = workdir / "charts"
    charts_dir.mkdir(exist_ok=True)
    (workdir / ".mpl").mkdir(exist_ok=True)

    script_path = workdir / "script.py"
    script_path.write_text(code, encoding="utf-8")
    existing_charts = set(charts_dir.glob("*"))

    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(workdir),
        "MPLBACKEND": "Agg",
        "MPLCONFIGDIR": str(workdir / ".mpl"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    try:
        proc = subprocess.run(
            [sys.executable, "-I", script_path.name],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            preexec_fn=_limit_resources(timeout_seconds, memory_mb),
        )
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            ok=False,
            error=f"Execution timed out after {timeout_seconds} seconds",
        )

    stdout = _truncate(proc.stdout)
    stderr = _truncate(proc.stderr)
    charts = sorted(
        p for p in charts_dir.glob("*.png") if p not in existing_charts
    )

    if proc.returncode != 0:
        return ExecutionResult(
            ok=False,
            stdout=stdout,
            stderr=stderr,
            error=f"Script exited with code {proc.returncode}",
            charts=charts,
        )

    return ExecutionResult(
        ok=True,
        stdout=stdout,
        stderr=stderr,
        result=_parse_result_json(proc.stdout),
        charts=charts,
    )
