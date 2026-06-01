#!/usr/bin/env python3
"""Local Leaf web interface.

Run with:
    python leaf_web.py --repo /path/to/project --port 8765

The server is intentionally local-first: it serves the static GUI in ./gui and
executes the existing Leaf CLI in the selected repository directory.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent
LEAF = ROOT / "leaf"
GUI_DIR = ROOT / "gui"
DEFAULT_PORT = 8765
MAX_BODY = 2 * 1024 * 1024
def read_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, type(default)) else default
    except (OSError, json.JSONDecodeError):
        return default


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return default


def resolve_repo(value: str | None, fallback: Path) -> Path:
    candidate = Path(value).expanduser() if value else fallback
    return candidate.resolve()


def safe_child(repo: Path, relative: str) -> Path:
    clean = unquote(relative or "").lstrip("/")
    target = (repo / clean).resolve()
    if target != repo and repo not in target.parents:
        raise ValueError("Path escapes repository")
    if ".leaf" in target.relative_to(repo).parts:
        raise ValueError("Direct .leaf edits are blocked from the file editor")
    return target


def run_leaf(repo: Path, args: list[str], timeout: int = 30) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, str(LEAF), *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=timeout,
        check=False,
    )
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def list_files(repo: Path) -> list[dict]:
    files: list[dict] = []
    ignore_dirs = {".git", ".leaf", "__pycache__", "node_modules", ".pytest_cache"}
    for root, dirs, names in os.walk(repo):
        dirs[:] = [name for name in dirs if name not in ignore_dirs]
        for name in names:
            path = Path(root) / name
            rel = path.relative_to(repo).as_posix()
            try:
                stat = path.stat()
            except OSError:
                continue
            files.append({"path": rel, "size": stat.st_size})
    return sorted(files, key=lambda item: item["path"])


def repo_state(repo: Path) -> dict:
    leaf_dir = repo / ".leaf"
    is_repo = leaf_dir.is_dir()
    state = {
        "repo": str(repo),
        "exists": repo.exists(),
        "is_repo": is_repo,
        "current_branch": read_text(leaf_dir / "CURRENT_BRANCH") if is_repo else "",
        "head": read_text(leaf_dir / "HEAD") if is_repo else "",
        "log": read_json(leaf_dir / "log.json", []) if is_repo else [],
        "branches": read_json(leaf_dir / "branches.json", {}) if is_repo else {},
        "tags": read_json(leaf_dir / "tags.json", {}) if is_repo else {},
        "remotes": read_json(leaf_dir / "remotes.json", {}) if is_repo else {},
        "index": read_json(leaf_dir / "index.json", {}) if is_repo else {},
        "merge_state": read_json(leaf_dir / "MERGE_STATE.json", {}) if is_repo else {},
        "files": list_files(repo) if repo.exists() and repo.is_dir() else [],
    }
    if is_repo:
        state["status_text"] = run_leaf(repo, ["status"])["stdout"]
        state["diff_text"] = run_leaf(repo, ["diff"])["stdout"]
        state["changes"] = parse_status(state["status_text"], state["index"])
    else:
        state["status_text"] = "Not a Leaf repository. Start tracking this folder to begin."
        state["diff_text"] = ""
        state["changes"] = []
    return state


def strip_ansi(text: str) -> str:
    import re
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def parse_status(status_text: str, index: dict) -> list[dict]:
    staged_paths = set(index.keys())
    changes = {}
    for path, entry in index.items():
        changes[path] = {
            "path": path,
            "staged": True,
            "status": "deleted" if entry.get("deleted") else "staged",
            "label": "Staged deletion" if entry.get("deleted") else "Staged",
        }
    for raw_line in strip_ansi(status_text).splitlines():
        line = raw_line.strip()
        for label, status in (("Conflict:", "conflict"), ("Added:", "added"), ("Modified:", "modified"), ("Deleted:", "deleted"), ("Staged:", "staged")):
            if label in line:
                path = line.split(label, 1)[1].strip()
                if not path:
                    continue
                current = changes.setdefault(path, {"path": path})
                if status == "staged":
                    current["staged"] = True
                else:
                    current.setdefault("staged", path in staged_paths)
                    current["status"] = status
                    current["label"] = status.title()
                break
    return sorted(changes.values(), key=lambda item: (not item.get("staged", False), item["path"]))


def action_to_args(action: str, data: dict) -> list[str]:
    path = str(data.get("path", "")).strip()
    commit_id = str(data.get("commit", "")).strip()
    branch = str(data.get("branch", "")).strip()
    name = str(data.get("name", "")).strip()
    remote = str(data.get("remote", "")).strip()

    actions = {
        "initialize": ["init"],
        "stage_all": ["add", "."],
        "stage_file": ["add", path],
        "unstage_file": ["reset", path],
        "commit": ["save", str(data.get("message", "")).strip()],
        "create_branch": ["branch", name, commit_id],
        "switch_branch": ["checkout", branch],
        "merge_branch": ["merge", branch],
        "merge_continue": ["merge", "--continue"],
        "merge_abort": ["merge", "--abort"],
        "restore_commit": ["restore", commit_id],
        "revert_commit": ["revert", commit_id],
        "soft_reset": ["reset", "--soft", commit_id],
        "hard_reset": ["reset", "--hard", commit_id],
        "create_tag": ["tag", name, commit_id],
        "ignore_path": ["ignore", path],
        "add_remote": ["remote", "add", remote, str(data.get("remote_path", "")).strip()],
        "fetch_remote": ["fetch", remote],
        "pull_remote": ["pull", remote, branch or "main"],
        "push_remote": ["push", remote, branch or "main"],
        "clone_repo": ["clone", str(data.get("source", "")).strip(), str(data.get("dest", "")).strip()],
        "check_integrity": ["fsck"],
    }
    if action not in actions:
        raise ValueError(f"Unsupported action: {action}")
    return [arg for arg in actions[action] if arg != ""]


class LeafWebHandler(BaseHTTPRequestHandler):
    server_version = "LeafWeb/1.0"

    def log_message(self, format: str, *args):  # noqa: A002 - http.server API
        print(f"{self.address_string()} - {format % args}")

    @property
    def default_repo(self) -> Path:
        return self.server.default_repo  # type: ignore[attr-defined]

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path):
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self) -> dict:
        size = int(self.headers.get("Content-Length", "0"))
        if size > MAX_BODY:
            raise ValueError("Request body is too large")
        if size == 0:
            return {}
        return json.loads(self.rfile.read(size).decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        repo = resolve_repo(params.get("repo", [None])[0], self.default_repo)

        try:
            if parsed.path == "/api/state":
                self.send_json(repo_state(repo))
                return
            if parsed.path == "/api/files":
                self.send_json({"repo": str(repo), "files": list_files(repo)})
                return
            if parsed.path == "/api/file":
                target = safe_child(repo, params.get("path", [""])[0])
                self.send_json({"path": target.relative_to(repo).as_posix(), "content": target.read_text(encoding="utf-8")})
                return
        except Exception as exc:  # Keep API errors readable in the GUI.
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        static_path = parsed.path
        if static_path in {"", "/"}:
            static_path = "/index.html"
        target = (GUI_DIR / static_path.lstrip("/")).resolve()
        if GUI_DIR == target or GUI_DIR in target.parents:
            self.send_file(target)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            data = self.read_body()
            repo = resolve_repo(data.get("repo"), self.default_repo)
            repo.mkdir(parents=True, exist_ok=True)

            if parsed.path == "/api/action":
                action = str(data.get("action", "")).strip()
                args = action_to_args(action, data)
                result = run_leaf(repo, args, timeout=60)
                result["action"] = action
                result["state"] = repo_state(repo)
                self.send_json(result)
                return


            if parsed.path == "/api/file":
                target = safe_child(repo, str(data.get("path", "")))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(data.get("content", "")), encoding="utf-8")
                self.send_json({"ok": True, "path": target.relative_to(repo).as_posix(), "state": repo_state(repo)})
                return
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        try:
            repo = resolve_repo(params.get("repo", [None])[0], self.default_repo)
            if parsed.path == "/api/file":
                target = safe_child(repo, params.get("path", [""])[0])
                if target.exists():
                    target.unlink()
                self.send_json({"ok": True, "state": repo_state(repo)})
                return
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self.send_error(HTTPStatus.NOT_FOUND)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local Leaf web GUI")
    parser.add_argument("--repo", default=os.getcwd(), help="Repository/workspace path to open in the GUI")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), LeafWebHandler)
    server.default_repo = Path(args.repo).expanduser().resolve()  # type: ignore[attr-defined]
    print(f"Leaf web GUI running at http://{args.host}:{args.port}")
    print(f"Workspace: {server.default_repo}")  # type: ignore[attr-defined]
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Leaf web GUI")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
