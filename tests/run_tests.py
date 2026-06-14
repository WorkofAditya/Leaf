from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    tests_dir = Path(__file__).resolve().parent
    scripts = sorted(tests_dir.glob("test_*.py"))
    results = []
    print(f"[INFO] Discovered {len(scripts)} test script(s)", flush=True)
    for script in scripts:
        print(f"[INFO] Running {script.name}", flush=True)
        env = os.environ.copy()
        repo_root = tests_dir.parent
        env["PATH"] = str(repo_root) + os.pathsep + env.get("PATH", "")
        env["PYTHONPATH"] = str(repo_root) + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run([sys.executable, str(script)], cwd=str(tests_dir), text=True, env=env)
        passed = result.returncode == 0
        results.append((script.stem, passed))
        print(("PASS" if passed else "FAIL") + f" {script.stem}", flush=True)
    passed_count = sum(1 for _, passed in results if passed)
    print("", flush=True)
    for name, passed in results:
        print(("PASS" if passed else "FAIL") + f" {name}", flush=True)
    print(f"{passed_count}/{len(results)} tests passed", flush=True)
    return 0 if passed_count == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
