import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEAF = ROOT / "leaf"


def run_leaf(cwd, *args, check=True):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [str(LEAF), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"leaf {' '.join(args)} failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result


def commit_ids(repo):
    return [c["id"] for c in json.loads((repo / ".leaf" / "log.json").read_text())]


def test_fast_forward_merge_and_log(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run_leaf(repo, "init")
    (repo / "a.txt").write_text("one\n")
    run_leaf(repo, "save", "initial")
    run_leaf(repo, "branch", "feature")
    run_leaf(repo, "checkout", "feature")
    (repo / "a.txt").write_text("one\ntwo\n")
    run_leaf(repo, "save", "feature work")
    run_leaf(repo, "checkout", "main")
    out = run_leaf(repo, "merge", "feature").stdout
    assert "Fast-forward merged" in out
    assert (repo / "a.txt").read_text() == "one\ntwo\n"
    assert "feature work" in run_leaf(repo, "log").stdout


def test_three_way_merge_without_conflicts_creates_merge_commit(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run_leaf(repo, "init")
    (repo / "a.txt").write_text("base\n")
    (repo / "b.txt").write_text("base\n")
    run_leaf(repo, "save", "initial")
    run_leaf(repo, "branch", "feature")
    (repo / "a.txt").write_text("main\n")
    run_leaf(repo, "save", "main work")
    run_leaf(repo, "checkout", "feature")
    (repo / "b.txt").write_text("feature\n")
    run_leaf(repo, "save", "feature work")
    run_leaf(repo, "checkout", "main")
    out = run_leaf(repo, "merge", "feature").stdout
    assert "Merged feature" in out
    assert (repo / "a.txt").read_text() == "main\n"
    assert (repo / "b.txt").read_text() == "feature\n"
    log = json.loads((repo / ".leaf" / "log.json").read_text())
    assert len(log[-1]["parents"]) == 2
    assert "Merge parents" in run_leaf(repo, "log").stdout


def test_conflict_merge_continue_and_abort(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run_leaf(repo, "init")
    (repo / "a.txt").write_text("base\n")
    run_leaf(repo, "save", "initial")
    run_leaf(repo, "branch", "feature")
    (repo / "a.txt").write_text("main\n")
    run_leaf(repo, "save", "main work")
    run_leaf(repo, "checkout", "feature")
    (repo / "a.txt").write_text("feature\n")
    run_leaf(repo, "save", "feature work")
    run_leaf(repo, "checkout", "main")
    out = run_leaf(repo, "merge", "feature").stdout
    assert "conflicts" in out
    assert "<<<<<<< current" in (repo / "a.txt").read_text()
    assert "Conflict: a.txt" in run_leaf(repo, "status").stdout
    assert "Resolve conflicts first" in run_leaf(repo, "merge", "--continue").stdout
    (repo / "a.txt").write_text("resolved\n")
    out = run_leaf(repo, "merge", "--continue").stdout
    assert "Merge completed" in out
    assert not (repo / ".leaf" / "MERGE_STATE.json").exists()
    assert (repo / "a.txt").read_text() == "resolved\n"


def test_merge_abort(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run_leaf(repo, "init")
    (repo / "a.txt").write_text("base\n")
    run_leaf(repo, "save", "initial")
    run_leaf(repo, "branch", "feature")
    (repo / "a.txt").write_text("main\n")
    run_leaf(repo, "save", "main work")
    run_leaf(repo, "checkout", "feature")
    (repo / "a.txt").write_text("feature\n")
    run_leaf(repo, "save", "feature work")
    run_leaf(repo, "checkout", "main")
    run_leaf(repo, "merge", "feature")
    out = run_leaf(repo, "merge", "--abort").stdout
    assert "Merge aborted" in out
    assert (repo / "a.txt").read_text() == "main\n"


def test_dirty_tree_blocks_merge(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run_leaf(repo, "init")
    (repo / "a.txt").write_text("base\n")
    run_leaf(repo, "save", "initial")
    run_leaf(repo, "branch", "feature")
    run_leaf(repo, "checkout", "feature")
    (repo / "a.txt").write_text("feature\n")
    run_leaf(repo, "save", "feature")
    run_leaf(repo, "checkout", "main")
    (repo / "a.txt").write_text("dirty\n")
    assert "uncommitted changes" in run_leaf(repo, "merge", "feature").stdout


def test_staging_status_reset_restore_tag_revert_fsck(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run_leaf(repo, "init")
    (repo / "a.txt").write_text("one\n")
    run_leaf(repo, "save", "initial")
    first = commit_ids(repo)[0]
    (repo / "a.txt").write_text("two\n")
    (repo / "b.txt").write_text("new\n")
    run_leaf(repo, "add", "a.txt")
    assert "Staged: a.txt" in run_leaf(repo, "status").stdout
    run_leaf(repo, "reset", "a.txt")
    run_leaf(repo, "add", "a.txt")
    run_leaf(repo, "save", "staged only")
    assert (repo / "b.txt").exists()
    run_leaf(repo, "tag", "v1")
    assert "v1" in run_leaf(repo, "tag").stdout
    second = commit_ids(repo)[-1]
    run_leaf(repo, "restore", first)
    assert (repo / "a.txt").read_text() == "one\n"
    run_leaf(repo, "checkout", "main")
    run_leaf(repo, "revert", second)
    assert (repo / "a.txt").read_text() == "one\n"
    assert "Repository integrity OK" in run_leaf(repo, "fsck").stdout


def test_branch_from_commit_and_hard_soft_reset(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run_leaf(repo, "init")
    (repo / "a.txt").write_text("one\n")
    run_leaf(repo, "save", "one")
    first = commit_ids(repo)[0]
    (repo / "a.txt").write_text("two\n")
    run_leaf(repo, "save", "two")
    run_leaf(repo, "branch", "old", first)
    run_leaf(repo, "checkout", "old")
    assert (repo / "a.txt").read_text() == "one\n"
    run_leaf(repo, "checkout", "main")
    run_leaf(repo, "reset", "--soft", first)
    assert (repo / "a.txt").read_text() == "two\n"
    run_leaf(repo, "reset", "--hard", first)
    assert (repo / "a.txt").read_text() == "one\n"


def test_ignore_diff_and_sessions(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run_leaf(repo, "init")
    run_leaf(repo, "ignore", "ignored.txt")
    (repo / "tracked.txt").write_text("one\n")
    (repo / "ignored.txt").write_text("secret\n")
    run_leaf(repo, "save", "initial")
    assert "tracked.txt" in json.dumps(json.loads((repo / ".leaf" / "log.json").read_text()))
    assert "ignored.txt" not in json.dumps(json.loads((repo / ".leaf" / "log.json").read_text()))
    (repo / "tracked.txt").write_text("two\n")
    assert "Diff: tracked.txt" in run_leaf(repo, "diff").stdout
    run_leaf(repo, "branch", "feature")
    run_leaf(repo, "checkout", "feature")
    (repo / "tracked.txt").write_text("session\n")
    run_leaf(repo, "checkout", "main")
    run_leaf(repo, "checkout", "feature")
    assert (repo / "tracked.txt").read_text() == "session\n"


def test_remote_fetch_push_pull_clone(tmp_path):
    remote = tmp_path / "remote"
    local = tmp_path / "local"
    remote.mkdir()
    local.mkdir()
    run_leaf(remote, "init")
    (remote / "a.txt").write_text("remote\n")
    run_leaf(remote, "save", "remote initial")

    run_leaf(local, "init")
    run_leaf(local, "remote", "add", "origin", str(remote))
    run_leaf(local, "fetch", "origin")
    assert "origin/main" in json.loads((local / ".leaf" / "branches.json").read_text())
    run_leaf(local, "merge", "origin/main")
    assert (local / "a.txt").read_text() == "remote\n"
    (local / "a.txt").write_text("local\n")
    run_leaf(local, "save", "local change")
    run_leaf(local, "push", "origin", "main")
    remote_branches = json.loads((remote / ".leaf" / "branches.json").read_text())
    local_branches = json.loads((local / ".leaf" / "branches.json").read_text())
    assert remote_branches["main"] == local_branches["main"]

    clone_dest = tmp_path / "clone"
    run_leaf(tmp_path, "clone", str(remote), str(clone_dest))
    assert (clone_dest / "a.txt").read_text() == "local\n"
