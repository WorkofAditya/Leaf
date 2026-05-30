import io
import json
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Modules import commands, core, files, graph, rebuild, storage
from Modules.common import BRANCHES_FILE, COMMITS_DIR, LOG_FILE, SESSIONS_FILE, VCS_DIR
from Modules.head_utils import get_head_module


def out(callable_, *args, **kwargs):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = callable_(*args, **kwargs)
    return buffer.getvalue(), result


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    commands.leaf_init()
    return tmp_path


def commit_ids():
    return [c["id"] for c in storage.safe_load_log()]


def test_head_module_lifecycle(tmp_path):
    head = get_head_module()
    vcs = tmp_path / ".leaf"
    head.init_head(str(vcs))
    assert head.read_head(str(vcs)) is None
    assert head.read_current_branch(str(vcs)) == "main"
    head.write_head(str(vcs), "abc123")
    head.write_current_branch(str(vcs), "feature")
    assert head.head_file_path(str(vcs)) == str(vcs / "HEAD")
    assert head.current_branch_path(str(vcs)) == str(vcs / "CURRENT_BRANCH")
    assert head.read_head(str(vcs)) == "abc123"
    assert head.read_current_branch(str(vcs)) == "feature"
    assert head.resolve_head(str(vcs), "fallback") == "abc123"
    head.write_head(str(vcs), "")
    head.write_current_branch(str(vcs), "")
    assert head.read_head(str(vcs)) is None
    assert head.read_current_branch(str(vcs)) is None
    assert head.resolve_head(str(vcs), "fallback") == "fallback"
    assert head.read_head(str(tmp_path / "missing")) is None
    assert head.read_current_branch(str(tmp_path / "missing")) is None


def test_storage_safe_load_save_and_fallback(repo):
    log = [{"id": "one"}]
    storage.safe_save_log(log)
    assert storage.safe_load_log() == log
    Path(LOG_FILE).write_text("not-json")
    assert storage.safe_load_log() == log
    Path(LOG_FILE).unlink()
    Path(VCS_DIR, "log.bak").unlink()
    assert storage.safe_load_log() == []

    Path(BRANCHES_FILE).write_text('{"main": "abc"}')
    assert storage.load_branches() == {"main": "abc"}
    Path(BRANCHES_FILE).write_text("[]")
    assert storage.load_branches() == {"main": None}
    storage.save_branches({"dev": "123"})
    assert storage.load_branches() == {"dev": "123"}

    Path(SESSIONS_FILE).write_text('{"main": {"a.txt": ["x\\n"]}}')
    assert storage.load_sessions() == {"main": {"a.txt": ["x\n"]}}
    Path(SESSIONS_FILE).write_text("[]")
    assert storage.load_sessions() == {}
    storage.save_sessions({"dev": {}})
    assert storage.load_sessions() == {"dev": {}}


def test_file_helpers_ignore_binary_snapshot_and_write(repo):
    Path("tracked.txt").write_text("hello\n")
    Path("skip.pyc").write_bytes(b"compiled")
    Path("nested").mkdir()
    Path("nested", "keep.txt").write_text("keep\n")
    Path("ignored_dir").mkdir()
    Path("ignored_dir", "hidden.txt").write_text("hide\n")
    Path("secret.txt").write_text("secret\n")
    Path(".leafignore").write_text("ignored_dir\nsecret.txt\n")
    Path("binary.bin").write_bytes(b"abc\x00def")

    assert files.is_binary("binary.bin") is True
    assert files.is_binary("tracked.txt") is False
    assert files.is_binary("missing.txt") is True
    assert files.leaf_read_file("tracked.txt") == ["hello\n"]
    assert files.leaf_read_file("missing.txt") == []
    assert files.load_ignore() >= {".leaf", "ignored_dir", "secret.txt", "*.pyc"}
    assert set(files.leaf_get_all_files()) == {"tracked.txt", "nested/keep.txt", ".leafignore", "binary.bin"}

    files.leaf_write_file("new/created.txt", ["created\n"])
    assert Path("new/created.txt").read_text() == "created\n"
    snapshot = Path(COMMITS_DIR, "manual")
    files.leaf_snapshot(str(snapshot))
    assert (snapshot / "tracked.txt").read_text() == "hello\n"
    assert not (snapshot / "secret.txt").exists()


def test_graph_helpers():
    log = [{"id": "a"}, {"id": "b", "parent": "a"}, {"id": "c", "parent": "b"}]
    cmap = graph.commit_map(log)
    assert cmap["a"]["id"] == "a"
    assert graph.commit_chain("c", cmap) == ["c", "b", "a"]
    assert graph.commit_chain("missing", cmap) == []
    assert graph.is_ancestor(None, "c", cmap) is True
    assert graph.is_ancestor("a", "c", cmap) is True
    assert graph.is_ancestor("c", "a", cmap) is False


def test_init_save_status_log_diff_restore_and_rebuild(repo):
    assert Path(COMMITS_DIR).is_dir()
    assert json.loads(Path(BRANCHES_FILE).read_text()) == {"main": None}
    assert Path(SESSIONS_FILE).read_text() == "{}"
    assert get_head_module().read_current_branch(VCS_DIR) == "main"

    Path("a.txt").write_text("one\n")
    text, _ = out(commands.leaf_status)
    assert "Added: a.txt" in text
    text, _ = out(commands.leaf_save, "initial")
    first = commit_ids()[0]
    assert "Saved commit" in text
    assert core.leaf_hash_commit("data") == core.leaf_hash_commit("data")
    assert core.leaf_get_head_commit_id() == first
    assert core.leaf_get_last_state() == {"a.txt": ["one\n"]}
    assert rebuild.leaf_rebuild(first, storage.safe_load_log()) == {"a.txt": ["one\n"]}
    assert storage.load_branches()["main"] == first

    text, _ = out(commands.leaf_status)
    assert "Clean working tree" in text
    text, _ = out(commands.leaf_save, "no changes")
    assert "No changes detected" in text
    text, _ = out(commands.leaf_diff)
    assert "No differences found" in text
    Path("a.txt").write_text("one\ntwo\n")
    Path("b.txt").write_text("bee\n")
    text, _ = out(commands.leaf_status)
    assert "Modified: a.txt" in text and "Added: b.txt" in text
    text, _ = out(commands.leaf_diff, first)
    assert "Diff: a.txt" in text and "+two" in text
    text, _ = out(commands.leaf_save, "second")
    second = commit_ids()[-1]
    assert second != first
    assert rebuild.leaf_rebuild(second, storage.safe_load_log()) == {"a.txt": ["one\n", "two\n"], "b.txt": ["bee\n"]}
    Path("b.txt").unlink()
    text, _ = out(commands.leaf_save, "delete b")
    third = commit_ids()[-1]
    assert "Saved commit" in text
    assert rebuild.leaf_rebuild(third, storage.safe_load_log()) == {"a.txt": ["one\n", "two\n"]}
    text, _ = out(commands.leaf_log)
    assert f"commit {third} (HEAD)" in text and "Message: initial" in text
    text, _ = out(commands.leaf_restore, first)
    assert "detached HEAD" in text
    assert Path("a.txt").read_text() == "one\n"
    assert not Path("b.txt").exists()
    assert get_head_module().read_current_branch(VCS_DIR) is None
    text, _ = out(commands.leaf_diff, "missing")
    assert "Invalid commit id" in text
    text, _ = out(commands.leaf_restore, "missing")
    assert "Invalid commit id" in text


def test_no_repository_and_no_commit_messages(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    text, _ = out(commands.leaf_save, "msg")
    assert "Not a repository" in text
    text, _ = out(commands.leaf_status)
    assert "No repository" in text
    text, _ = out(commands.leaf_diff)
    assert "No commits" in text
    text, _ = out(commands.leaf_log)
    assert "No commits" in text
    text, _ = out(commands.leaf_branch)
    assert "Not a repository" in text
    text, _ = out(commands.leaf_branch, "feature")
    assert "Not a repository" in text


def test_ignore_command_idempotent_and_missing(repo):
    text, _ = out(commands.leaf_ignore, "")
    assert "Missing file/folder" in text
    text, _ = out(commands.leaf_ignore, "build")
    assert "Added to .leafignore: build" in text
    assert Path(".leafignore").read_text() == "build"
    text, _ = out(commands.leaf_ignore, "build")
    assert "Already ignored: build" in text


def test_branch_checkout_sessions_and_fast_forward_merge(repo):
    Path("file.txt").write_text("base\n")
    commands.leaf_save("base")
    base = commit_ids()[-1]
    text, _ = out(commands.leaf_branch)
    assert "* main" in text
    text, _ = out(commands.leaf_branch, "feature")
    assert "Created branch feature" in text
    text, _ = out(commands.leaf_branch, "feature")
    assert "Branch already exists" in text
    assert storage.load_branches()["feature"] == base

    Path("file.txt").write_text("main draft\n")
    text, _ = out(commands.leaf_checkout, "feature")
    assert "Switched to branch feature" in text
    assert Path("file.txt").read_text() == "base\n"
    assert storage.load_sessions()["main"] == {"file.txt": ["main draft\n"]}
    Path("file.txt").write_text("feature done\n")
    commands.leaf_save("feature done")
    feature_tip = commit_ids()[-1]
    text, _ = out(commands.leaf_checkout, "main")
    assert Path("file.txt").read_text() == "main draft\n"
    # Discard session so main can fast-forward to feature.
    storage.save_sessions({})
    text, _ = out(commands.leaf_merge, "feature")
    assert "Fast-forward merged feature into main" in text
    assert storage.load_branches()["main"] == feature_tip
    assert Path("file.txt").read_text() == "feature done\n"
    text, _ = out(commands.leaf_merge, "feature")
    assert "Already up to date" in text
    text, _ = out(commands.leaf_merge, "main")
    assert "Already on main" in text
    text, _ = out(commands.leaf_checkout, "missing")
    assert "Unknown branch" in text
    text, _ = out(commands.leaf_merge, "missing")
    assert "Unknown branch" in text


def test_merge_rejects_detached_non_fast_forward_and_session_choices(repo, monkeypatch):
    Path("file.txt").write_text("base\n")
    commands.leaf_save("base")
    commands.leaf_branch("left")
    commands.leaf_branch("right")
    commands.leaf_checkout("left")
    Path("file.txt").write_text("left\n")
    commands.leaf_save("left")
    commands.leaf_checkout("right")
    Path("file.txt").write_text("right\n")
    commands.leaf_save("right")
    text, _ = out(commands.leaf_merge, "left")
    assert "Non fast-forward merge not supported yet" in text

    commands.leaf_restore(storage.load_branches()["left"])
    text, _ = out(commands.leaf_merge, "right")
    assert "Merge requires being on a branch" in text

    commands.leaf_checkout("right")
    storage.save_sessions({"left": {"file.txt": ["left session\n"]}})
    monkeypatch.setattr("builtins.input", lambda prompt="": "x")
    text, _ = out(commands.leaf_merge, "left")
    assert "Merge cancelled" in text
    monkeypatch.setattr("builtins.input", lambda prompt="": "d")
    text, _ = out(commands.leaf_merge, "left")
    assert "Discarded saved session" in text and "Non fast-forward" in text

    storage.save_sessions({"left": {"file.txt": ["left session\n"]}})
    monkeypatch.setattr("builtins.input", lambda prompt="": "c")
    text, _ = out(commands.leaf_merge, "left")
    assert "Session restored" in text
    assert Path("file.txt").read_text() == "left session\n"


def test_help_version_and_cli(repo, monkeypatch):
    text, _ = out(commands.leaf_help)
    assert "Leaf Version Control System" in text

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *exc):
            return False
        def read(self):
            return b"9.9.9\n"

    monkeypatch.setattr(commands.urllib.request, "urlopen", lambda *a, **k: FakeResponse())
    text, _ = out(commands.leaf_version)
    assert text.strip() == "9.9.9"
    monkeypatch.setattr(commands.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError("down")))
    text, _ = out(commands.leaf_version)
    assert "Could not fetch version" in text

    result = subprocess.run([sys.executable, str(REPO_ROOT / "leaf"), "help"], cwd=Path.cwd(), text=True, capture_output=True, check=True)
    assert "Leaf Version Control System" in result.stdout
    result = subprocess.run([sys.executable, str(REPO_ROOT / "leaf"), "status"], cwd=Path.cwd(), text=True, capture_output=True, check=True)
    assert result.stdout
