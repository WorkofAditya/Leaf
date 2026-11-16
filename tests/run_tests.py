from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


COLORS = {
    "green": "\033[32m",
    "red": "\033[31m",
    "yellow": "\033[33m",
    "cyan": "\033[36m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}


def colors_enabled(disabled: bool = False) -> bool:
    if disabled or os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("FORCE_COLOR") not in (None, "", "0") or os.environ.get("CI"):
        return True
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


def paint(value: str, shade: str, enabled: bool) -> str:
    if not enabled:
        return value
    return f"{COLORS[shade]}{value}{COLORS['reset']}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Leaf's isolated test suites and report actionable failures."
    )
    parser.add_argument(
        "suites",
        nargs="*",
        help="Optional suite names, for example test_workflow or test_git_interop",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show every assertion, command, and subprocess output",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120,
        help="Maximum runtime per suite in seconds (default: 120)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List discovered test suites without running them",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    return args


def failure_record(message: str, command: str, cwd: str, stderr: str = "") -> dict:
    return {
        "message": message,
        "command": {
            "command": command,
            "cwd": cwd,
            "stderr": stderr,
        },
    }


def main() -> int:
    args = parse_args()
    enabled = colors_enabled(args.no_color)
    tests_dir = Path(__file__).resolve().parent
    repo_root = tests_dir.parent
    scripts = sorted(tests_dir.glob("test_*.py"))

    if args.suites:
        requested = {name.removesuffix(".py") for name in args.suites}
        available = {script.stem for script in scripts}
        unknown = sorted(requested - available)
        if unknown:
            print(paint("[ERROR]", "red", enabled) + f" Unknown suite(s): {', '.join(unknown)}")
            print("Available: " + ", ".join(sorted(available)))
            return 2
        scripts = [script for script in scripts if script.stem in requested]

    if args.list:
        for script in scripts:
            print(script.stem)
        return 0

    if not scripts:
        print(paint("[ERROR]", "red", enabled) + " No test suites were found.")
        return 2

    print(paint("Leaf test suite", "cyan", enabled))
    print(f"Discovered {len(scripts)} suite(s)")
    print("")

    results = []
    total_started = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="leaf-tests-") as temporary:
        workspace = Path(temporary)
        for index, script in enumerate(scripts, 1):
            suite_name = script.stem
            report_path = workspace / f"{suite_name}.json"
            suite_root = workspace / "workspaces" / suite_name
            env = os.environ.copy()
            env["PATH"] = str(repo_root) + os.pathsep + env.get("PATH", "")
            env["PYTHONPATH"] = str(repo_root) + os.pathsep + env.get("PYTHONPATH", "")
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONUTF8"] = "1"
            env["GIT_TERMINAL_PROMPT"] = "0"
            env["LEAF_TEST_ROOT"] = str(suite_root)
            env["LEAF_TEST_RESULT_FILE"] = str(report_path)
            env["LEAF_TEST_VERBOSE"] = "1" if args.verbose else "0"
            if args.no_color:
                env["NO_COLOR"] = "1"

            print(
                paint("[RUN ]", "cyan", enabled)
                + f" {suite_name} ({index}/{len(scripts)})",
                flush=True,
            )
            started = time.perf_counter()
            process_error = None
            try:
                process = subprocess.run(
                    [sys.executable, str(script)],
                    cwd=str(tests_dir),
                    env=env,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    capture_output=True,
                    timeout=args.timeout,
                    check=False,
                )
                stdout = process.stdout or ""
                stderr = process.stderr or ""
                returncode = process.returncode
            except subprocess.TimeoutExpired as exc:
                stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
                stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
                returncode = 124
                process_error = f"Suite timed out after {args.timeout:g} seconds"
            except OSError as exc:
                stdout = ""
                stderr = f"{type(exc).__name__}: {exc}"
                returncode = 127
                process_error = "Could not start the test process"

            elapsed = time.perf_counter() - started
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                report = {
                    "name": suite_name,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "failures": [],
                }

            failures = list(report.get("failures", []))
            suite_passed = returncode == 0 and report.get("failed", 0) == 0 and process_error is None
            if not report_path.exists() and not failures:
                failures.append(
                    failure_record(
                        process_error or f"Suite exited with code {returncode} without writing a result report",
                        f"{sys.executable} {script}",
                        str(tests_dir),
                        stderr,
                    )
                )
            elif process_error:
                failures.append(
                    failure_record(
                        process_error,
                        f"{sys.executable} {script}",
                        str(tests_dir),
                        stderr,
                    )
                )
            elif returncode != 0 and not failures:
                failures.append(
                    failure_record(
                        f"Suite process exited with code {returncode}",
                        f"{sys.executable} {script}",
                        str(tests_dir),
                        stderr,
                    )
                )

            if args.verbose or not suite_passed:
                if stdout:
                    print(stdout, end="" if stdout.endswith("\n") else "\n")
                if stderr:
                    print(stderr, end="" if stderr.endswith("\n") else "\n", file=sys.stderr)

            result = {
                "name": suite_name,
                "passed": int(report.get("passed", 0)),
                "failed": int(report.get("failed", 0)),
                "skipped": int(report.get("skipped", 0)),
                "failures": failures,
                "suite_passed": suite_passed,
                "elapsed": elapsed,
            }
            results.append(result)

            if suite_passed and result["passed"] == 0 and result["skipped"] > 0:
                label, shade = "[SKIP]", "yellow"
            elif suite_passed:
                label, shade = "[PASS]", "green"
            else:
                label, shade = "[FAIL]", "red"

            print(
                paint(label, shade, enabled)
                + f" {suite_name}  "
                + paint(
                    f"{result['passed']} passed, {result['failed']} failed, "
                    f"{result['skipped']} skipped",
                    "dim",
                    enabled,
                )
                + f"  ({elapsed:.2f}s)",
                flush=True,
            )

    suite_count = len(results)
    suites_passed = sum(result["suite_passed"] for result in results)
    suites_failed = suite_count - suites_passed
    checks_passed = sum(result["passed"] for result in results)
    checks_failed = sum(result["failed"] for result in results)
    checks_skipped = sum(result["skipped"] for result in results)
    elapsed_total = time.perf_counter() - total_started

    print("")
    print(paint("Test summary", "cyan", enabled))
    print(
        f"Suites: {suites_passed}/{suite_count} passed, "
        f"{suites_failed} failed"
    )
    print(
        f"Checks: {checks_passed} passed, {checks_failed} failed, "
        f"{checks_skipped} skipped"
    )
    print(f"Duration: {elapsed_total:.2f}s")

    failures = [
        (result["name"], failure)
        for result in results
        for failure in result["failures"]
    ]
    if failures:
        print("")
        print(paint("Failed checks", "red", enabled))
        for index, (suite_name, failure) in enumerate(failures, 1):
            print(paint(f"{index}. [{suite_name}] {failure['message']}", "red", enabled))
            command = failure.get("command")
            if command:
                print(f"   Command: {command['command']}")
                print(f"   Working directory: {command['cwd']}")
                if command.get("expected_returncode") is not None:
                    print(
                        "   Exit code: "
                        f"expected {command['expected_returncode']}, "
                        f"got {command.get('returncode', 'not available')}"
                    )
                if command.get("stdout"):
                    print(f"   stdout: {command['stdout'][-2000:].rstrip()}")
                if command.get("stderr"):
                    print(f"   stderr: {command['stderr'][-2000:].rstrip()}")

    if suites_failed == 0:
        print(paint("\nAll test suites passed.", "green", enabled))
        return 0

    print(paint(f"\n{ suites_failed } test suite(s) failed.", "red", enabled))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
