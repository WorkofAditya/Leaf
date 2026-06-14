from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


class TestContext:
    def __init__(self, script_file: str):
        self.script_path = Path(script_file).resolve()
        self.name = self.script_path.stem
        self.root = self.script_path.parent / self.name
        self.passed = 0
        self.failed = 0
        self.repo = self.root / "repo"

    def reset(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True)

    def info(self, message: str) -> None:
        print(f"[INFO] {message}", flush=True)

    def pass_(self, message: str) -> None:
        self.passed += 1
        print(f"[PASS] {message}", flush=True)

    def fail(self, message: str) -> None:
        self.failed += 1
        print(f"[FAIL] {message}", flush=True)
        raise AssertionError(message)

    def check(self, condition: bool, message: str) -> None:
        if condition:
            self.pass_(message)
        else:
            self.fail(message)

    def command(self, args, cwd: Path | None = None, ok: bool = True, contains: str | None = None):
        cwd = cwd or self.repo
        printable = " ".join(args)
        print(f"[COMMAND] $ {printable}", flush=True)
        env = os.environ.copy()
        repo_root = self.script_path.parents[1]
        env["PATH"] = str(repo_root) + os.pathsep + env.get("PATH", "")
        env["PYTHONPATH"] = str(repo_root) + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(args, cwd=str(cwd), text=True, capture_output=True, env=env)
        print(f"[STDOUT] {result.stdout.rstrip()}", flush=True)
        print(f"[STDERR] {result.stderr.rstrip()}", flush=True)
        print(f"[INFO] return code: {result.returncode}", flush=True)
        if ok and result.returncode != 0:
            self.fail(f"Command failed unexpectedly: {printable}")
        if contains is not None:
            combined = result.stdout + result.stderr
            self.check(contains in combined, f"Command output contains {contains!r}")
        if ok:
            self.pass_(f"Command succeeded: {printable}")
        return result

    def write(self, rel: str, text: str, cwd: Path | None = None) -> Path:
        base = cwd or self.repo
        path = base / rel
        self.info(f"Writing {path.relative_to(self.root)}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.check(path.read_text(encoding="utf-8") == text, f"Wrote {rel}")
        return path

    def read(self, rel: str, cwd: Path | None = None) -> str:
        return ((cwd or self.repo) / rel).read_text(encoding="utf-8")

    def assert_file(self, rel: str, expected: str, cwd: Path | None = None) -> None:
        actual = self.read(rel, cwd)
        self.check(actual == expected, f"{rel} contents match expected")

    def load_json(self, rel: str, cwd: Path | None = None):
        with ((cwd or self.repo) / rel).open(encoding="utf-8") as fh:
            return json.load(fh)

    def commits(self):
        return self.load_json(".leaf/log.json")

    def commit_ids(self):
        return [c["id"] for c in self.commits()]

    def summary(self) -> None:
        print(f"[INFO] Summary: {self.passed} passed, {self.failed} failed", flush=True)
        if self.failed:
            raise SystemExit(1)


def main_wrapper(script_file: str, func) -> None:
    ctx = TestContext(script_file)
    try:
        ctx.reset()
        func(ctx)
    except Exception as exc:
        ctx.failed += 1
        print(f"[FAIL] {type(exc).__name__}: {exc}", flush=True)
        ctx.summary()
    ctx.summary()
