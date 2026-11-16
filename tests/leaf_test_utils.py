from __future__ import annotations

import difflib
import json
import os
import shlex
import shutil
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Sequence


_ANSI = {
    "green": "\033[32m",
    "red": "\033[31m",
    "yellow": "\033[33m",
    "cyan": "\033[36m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}


def _colors_enabled() -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("FORCE_COLOR") not in (None, "", "0"):
        return True
    if os.environ.get("CI"):
        return True
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


def color(value: str, name: str) -> str:
    if not _colors_enabled():
        return value
    return f"{_ANSI[name]}{value}{_ANSI['reset']}"


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


class TestContext:
    """Isolated integration-test workspace with useful failure diagnostics."""

    def __init__(self, script_file: str):
        self.script_path = Path(script_file).resolve()
        self.name = self.script_path.stem
        configured_root = os.environ.get("LEAF_TEST_ROOT")
        self.root = (
            Path(configured_root).resolve()
            if configured_root
            else self.script_path.parent / self.name
        )
        self.repo = self.root / "repo"
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.failures: list[dict] = []
        self.last_command: dict | None = None
        self.verbose = os.environ.get("LEAF_TEST_VERBOSE") == "1"

    def reset(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True)

    def info(self, message: str) -> None:
        if self.verbose:
            print(color("[INFO]", "cyan") + f" {message}", flush=True)

    def pass_(self, message: str) -> None:
        self.passed += 1
        if self.verbose:
            print(color("[PASS]", "green") + f" {message}", flush=True)

    def skip(self, message: str) -> None:
        self.skipped += 1
        print(color("[SKIP]", "yellow") + f" {message}", flush=True)

    def fail(
        self,
        message: str,
        *,
        command: dict | None = None,
        traceback_text: str | None = None,
    ) -> None:
        self.failed += 1
        record = {
            "message": message,
            "command": command or self.last_command,
            "traceback": traceback_text,
        }
        self.failures.append(record)
        print(color("[FAIL]", "red") + f" {message}", flush=True)

    def check(self, condition: bool, message: str, *, command: dict | None = None) -> bool:
        if condition:
            self.pass_(message)
            return True
        self.fail(message, command=command)
        return False

    def command(
        self,
        args: Sequence[str | os.PathLike],
        cwd: Path | str | None = None,
        *,
        expected_returncode: int = 0,
        contains: str | None = None,
        timeout: float = 30,
        input_text: str | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess:
        if not args:
            self.fail("Cannot run an empty command")
            return subprocess.CompletedProcess([], 127, "", "empty command")

        argv = [str(part) for part in args]
        printable = shlex.join(argv)
        working_directory = Path(cwd or self.repo).resolve()
        env = os.environ.copy()
        repo_root = self.script_path.parents[1]
        env["PATH"] = str(repo_root) + os.pathsep + env.get("PATH", "")
        env["PYTHONPATH"] = str(repo_root) + os.pathsep + env.get("PYTHONPATH", "")
        env.setdefault("PYTHONUNBUFFERED", "1")
        env.setdefault("PYTHONUTF8", "1")
        env.setdefault("GIT_TERMINAL_PROMPT", "0")
        if extra_env:
            env.update(extra_env)

        if self.verbose:
            print(color("[CMD]", "cyan") + f" ({working_directory}) $ {printable}", flush=True)

        try:
            result = subprocess.run(
                argv,
                cwd=str(working_directory),
                input=input_text,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                env=env,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            result = subprocess.CompletedProcess(
                argv,
                124,
                _as_text(exc.stdout),
                _as_text(exc.stderr) + f"\nTimed out after {timeout:g} seconds",
            )
        except OSError as exc:
            result = subprocess.CompletedProcess(argv, 127, "", f"{type(exc).__name__}: {exc}")

        record = {
            "command": printable,
            "cwd": str(working_directory),
            "returncode": result.returncode,
            "expected_returncode": expected_returncode,
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
        }
        self.last_command = record

        if result.returncode != expected_returncode:
            self.fail(
                f"Command exited with {result.returncode}; expected {expected_returncode}",
                command=record,
            )
        else:
            self.pass_(f"Command exited with {expected_returncode}: {printable}")

        if contains is not None:
            output = (result.stdout or "") + (result.stderr or "")
            self.check(
                contains in output,
                f"Expected command output to contain {contains!r}",
                command=record,
            )

        if self.verbose and (result.stdout or result.stderr):
            if result.stdout:
                print("[STDOUT]")
                print(result.stdout.rstrip())
            if result.stderr:
                print("[STDERR]")
                print(result.stderr.rstrip())

        return result

    def write(self, rel: str, text: str, cwd: Path | None = None) -> Path:
        base = cwd or self.repo
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.check(path.read_text(encoding="utf-8") == text, f"Write and read back {rel}")
        return path

    def read(self, rel: str, cwd: Path | None = None) -> str:
        return ((cwd or self.repo) / rel).read_text(encoding="utf-8")

    def assert_file(self, rel: str, expected: str, cwd: Path | None = None) -> None:
        path = (cwd or self.repo) / rel
        if not path.is_file():
            self.fail(f"Expected file does not exist: {rel}")
            return

        actual = path.read_text(encoding="utf-8")
        if actual == expected:
            self.pass_(f"{rel} matches expected content")
            return

        diff = "".join(
            difflib.unified_diff(
                expected.splitlines(keepends=True),
                actual.splitlines(keepends=True),
                fromfile=f"expected/{rel}",
                tofile=f"actual/{rel}",
            )
        )
        self.fail(f"Content mismatch in {rel}\n{diff[:4000]}")

    def load_json(self, rel: str, cwd: Path | None = None):
        with ((cwd or self.repo) / rel).open(encoding="utf-8") as stream:
            return json.load(stream)

    def commits(self):
        return self.load_json(".leaf/log.json")

    def commit_ids(self):
        return [commit["id"] for commit in self.commits()]

    def report(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "failures": self.failures,
        }

    def summary(self) -> int:
        status = "PASS" if self.failed == 0 else "FAIL"
        status_color = "green" if self.failed == 0 else "red"
        print(
            f"\n{color('[' + status + ']', status_color)} {self.name}: "
            f"{self.passed} passed, {self.failed} failed, {self.skipped} skipped",
            flush=True,
        )
        if self.failures:
            print(color("Failure details:", "red"), flush=True)
            for index, failure in enumerate(self.failures, 1):
                print(f"  {index}. {failure['message']}", flush=True)
                command = failure.get("command")
                if command:
                    print(f"     Command: {command['command']}", flush=True)
                    print(f"     Working directory: {command['cwd']}", flush=True)
                    if "returncode" in command:
                        print(
                            "     Exit code: "
                            f"expected {command['expected_returncode']}, "
                            f"got {command['returncode']}",
                            flush=True,
                        )
                    if command.get("stdout"):
                        print(f"     stdout: {command['stdout'][-2000:].rstrip()}", flush=True)
                    if command.get("stderr"):
                        print(f"     stderr: {command['stderr'][-2000:].rstrip()}", flush=True)
                if failure.get("traceback"):
                    print(failure["traceback"], flush=True)
        return 1 if self.failed else 0


def main_wrapper(script_file: str, func) -> None:
    context = TestContext(script_file)
    try:
        context.reset()
        func(context)
    except Exception as exc:
        context.fail(
            f"Unhandled {type(exc).__name__}: {exc}",
            traceback_text=traceback.format_exc(),
        )

    report = context.report()
    result_file = os.environ.get("LEAF_TEST_RESULT_FILE")
    if result_file:
        destination = Path(result_file)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    raise SystemExit(context.summary())
