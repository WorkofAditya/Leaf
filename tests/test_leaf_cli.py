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


def make_repo(tmp_path, name="repo"):
    repo = tmp_path / name
    repo.mkdir()
    out = run_leaf(repo, "init").stdout
    assert "Initialized empty leaf repository" in out
    assert (repo / ".leaf").is_dir()
    return repo


def commit_ids(repo):
    return [c["id"] for c in json.loads((repo / ".leaf" / "log.json").read_text())]


def branches(repo):
    return json.loads((repo / ".leaf" / "branches.json").read_text())


def test_no_repository_and_argument_validation(tmp_path):
    assert run_leaf(tmp_path, "save", "outside").stdout.strip().endswith("Not a repository")
    assert run_leaf(tmp_path, "status").stdout.strip().endswith("No repository")
    assert run_leaf(tmp_path, "log").stdout.strip().endswith("No commits")
    assert run_leaf(tmp_path, "diff").stdout.strip().endswith("No commits")
    assert run_leaf(tmp_path, "add").stdout.strip().endswith("Missing path")
    assert run_leaf(tmp_path, "ignore").stdout.strip().endswith("Missing file/folder name")
    assert run_leaf(tmp_path, "checkout").stdout.strip().endswith("Missing branch name")
    assert run_leaf(tmp_path, "merge").stdout.strip().endswith("Missing branch name to merge")
    assert run_leaf(tmp_path, "restore").stdout.strip().endswith("Missing commit id")
    assert run_leaf(tmp_path, "revert").stdout.strip().endswith("Missing commit id")
    assert run_leaf(tmp_path, "clone").stdout.strip().endswith("Missing source path")


def test_complete_local_command_lifecycle_in_one_repository(tmp_path):
    repo = make_repo(tmp_path)

    assert "Clean working tree" in run_leaf(repo, "status").stdout
    assert "No commits" in run_leaf(repo, "log").stdout
    assert "No commits" in run_leaf(repo, "diff").stdout

    run_leaf(repo, "ignore", "ignored.txt")
    assert "Already ignored" in run_leaf(repo, "ignore", "ignored.txt").stdout
    (repo / "tracked.txt").write_text("one\n")
    (repo / "ignored.txt").write_text("secret\n")

    status = run_leaf(repo, "status").stdout
    assert "Added: tracked.txt" in status
    assert "ignored.txt" not in status

    assert "Saved commit" in run_leaf(repo, "save", "initial commit").stdout
    saved_log = json.dumps(json.loads((repo / ".leaf" / "log.json").read_text()))
    assert "ignored.txt" not in saved_log
    first = commit_ids(repo)[0]
    assert "initial commit" in run_leaf(repo, "log").stdout
    assert "No differences found" in run_leaf(repo, "diff").stdout
    assert "No changes detected" in run_leaf(repo, "save", "nothing changed").stdout

    (repo / "tracked.txt").write_text("two\n")
    (repo / "added.txt").write_text("added\n")
    diff = run_leaf(repo, "diff").stdout
    assert "Diff: added.txt" in diff
    assert "Diff: tracked.txt" in diff

    assert "Staged" in run_leaf(repo, "add", ".").stdout
    staged_status = run_leaf(repo, "status").stdout
    assert "Staged: added.txt" in staged_status
    assert "Staged: tracked.txt" in staged_status
    assert "Unstaged tracked.txt" in run_leaf(repo, "reset", "tracked.txt").stdout
    assert "Nothing staged for missing.txt" in run_leaf(repo, "reset", "missing.txt").stdout
    assert "Cleared staging area" in run_leaf(repo, "reset").stdout

    run_leaf(repo, "add", "tracked.txt")
    assert "Saved commit" in run_leaf(repo, "save", "staged tracked only").stdout
    second = commit_ids(repo)[-1]
    assert (repo / "added.txt").exists()
    assert "staged tracked only" in run_leaf(repo, "log").stdout

    (repo / "tracked.txt").unlink()
    assert "Deleted: tracked.txt" in run_leaf(repo, "status").stdout
    assert "Staged 1 path(s)" in run_leaf(repo, "add", "tracked.txt").stdout
    assert "Deleted: tracked.txt" in run_leaf(repo, "status").stdout
    assert "Saved commit" in run_leaf(repo, "save", "delete tracked").stdout
    assert not (repo / "tracked.txt").exists()

    assert "Invalid commit id" in run_leaf(repo, "diff", "badcommit").stdout
    assert "Invalid commit id" in run_leaf(repo, "restore", "badcommit").stdout
    assert "Invalid commit id" in run_leaf(repo, "reset", "--hard", "badcommit").stdout
    assert "Invalid commit id" in run_leaf(repo, "revert", "badcommit").stdout
    assert "Invalid commit id" in run_leaf(repo, "tag", "bad", "badcommit").stdout

    assert "Tagged" in run_leaf(repo, "tag", "v1", first).stdout
    assert "v1" in run_leaf(repo, "tag").stdout
    assert "Repository integrity OK" in run_leaf(repo, "fsck").stdout

    assert "Restored to commit" in run_leaf(repo, "restore", first).stdout
    assert (repo / "tracked.txt").read_text() == "one\n"
    assert "Merge requires being on a branch" in run_leaf(repo, "merge", "main").stdout
    assert "Switched to branch main" in run_leaf(repo, "checkout", "main").stdout

    assert "Reverted" in run_leaf(repo, "revert", second).stdout
    assert (repo / "tracked.txt").read_text() == "one\n"


def test_branch_checkout_reset_sessions_and_merge_guards(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "a.txt").write_text("one\n")
    run_leaf(repo, "save", "one")
    first = commit_ids(repo)[0]
    (repo / "a.txt").write_text("two\n")
    run_leaf(repo, "save", "two")
    second = commit_ids(repo)[-1]

    assert "* main" in run_leaf(repo, "branch").stdout
    assert "Created branch old" in run_leaf(repo, "branch", "old", first).stdout
    assert "Branch already exists" in run_leaf(repo, "branch", "old").stdout
    assert "Invalid commit id" in run_leaf(repo, "branch", "bad", "badcommit").stdout
    assert "Unknown branch" in run_leaf(repo, "checkout", "missing").stdout

    assert "Switched to branch old" in run_leaf(repo, "checkout", "old").stdout
    assert (repo / "a.txt").read_text() == "one\n"
    (repo / "session.txt").write_text("draft\n")
    assert "Switched to branch main" in run_leaf(repo, "checkout", "main").stdout
    assert not (repo / "session.txt").exists()
    assert "Switched to branch old" in run_leaf(repo, "checkout", "old").stdout
    assert (repo / "session.txt").read_text() == "draft\n"
    (repo / "session.txt").unlink()
    assert "Switched to branch main" in run_leaf(repo, "checkout", "main").stdout

    assert "Created branch feature" in run_leaf(repo, "branch", "feature").stdout
    assert "Already on main" in run_leaf(repo, "merge", "main").stdout
    run_leaf(repo, "checkout", "feature")
    assert "Already on feature" in run_leaf(repo, "merge", "feature").stdout
    run_leaf(repo, "checkout", "main")
    assert "Unknown branch" in run_leaf(repo, "merge", "missing").stdout
    run_leaf(repo, "add", "a.txt")
    assert "Commit or reset staged changes" in run_leaf(repo, "merge", "feature").stdout
    run_leaf(repo, "reset")

    assert "Reset --soft" in run_leaf(repo, "reset", "--soft", first).stdout
    assert (repo / "a.txt").read_text() == "two\n"
    assert branches(repo)["main"] == first
    assert "Reset --hard" in run_leaf(repo, "reset", "--hard", second).stdout
    assert (repo / "a.txt").read_text() == "two\n"


def test_fast_forward_merge_and_log(tmp_path):
    repo = make_repo(tmp_path)
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
    repo = make_repo(tmp_path)
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


def test_conflict_merge_continue_save_and_abort_paths(tmp_path):
    repo = make_repo(tmp_path)
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
    assert "Merge already in progress" in run_leaf(repo, "merge", "feature").stdout
    assert "Cannot checkout during merge" in run_leaf(repo, "checkout", "feature").stdout
    assert "Conflict: a.txt" in run_leaf(repo, "status").stdout
    assert "Resolve conflicts first" in run_leaf(repo, "merge", "--continue").stdout
    assert "Resolve conflicts before saving merge" in run_leaf(repo, "save", "bad merge save").stdout
    (repo / "a.txt").write_text("resolved\n")
    out = run_leaf(repo, "save", "manual merge save").stdout
    assert "Saved commit" in out
    assert not (repo / ".leaf" / "MERGE_STATE.json").exists()
    assert (repo / "a.txt").read_text() == "resolved\n"

    repo_abort = make_repo(tmp_path, "repo_abort")
    (repo_abort / "a.txt").write_text("base\n")
    run_leaf(repo_abort, "save", "initial")
    run_leaf(repo_abort, "branch", "feature")
    (repo_abort / "a.txt").write_text("main\n")
    run_leaf(repo_abort, "save", "main work")
    run_leaf(repo_abort, "checkout", "feature")
    (repo_abort / "a.txt").write_text("feature\n")
    run_leaf(repo_abort, "save", "feature work")
    run_leaf(repo_abort, "checkout", "main")
    run_leaf(repo_abort, "merge", "feature")
    assert "Merge aborted" in run_leaf(repo_abort, "merge", "--abort").stdout
    assert (repo_abort / "a.txt").read_text() == "main\n"
    assert "No merge in progress" in run_leaf(repo_abort, "merge", "--abort").stdout
    assert "No merge in progress" in run_leaf(repo_abort, "merge", "--continue").stdout


def test_dirty_tree_and_unresolved_session_block_merge(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "a.txt").write_text("base\n")
    run_leaf(repo, "save", "initial")
    run_leaf(repo, "branch", "feature")
    run_leaf(repo, "checkout", "feature")
    (repo / "a.txt").write_text("feature\n")
    run_leaf(repo, "save", "feature")
    run_leaf(repo, "checkout", "main")
    (repo / "a.txt").write_text("dirty\n")
    assert "uncommitted changes" in run_leaf(repo, "merge", "feature").stdout

    clean_repo = make_repo(tmp_path, "session_block")
    (clean_repo / "a.txt").write_text("base\n")
    run_leaf(clean_repo, "save", "initial")
    run_leaf(clean_repo, "branch", "feature")
    run_leaf(clean_repo, "checkout", "feature")
    (clean_repo / "draft.txt").write_text("unsaved\n")
    run_leaf(clean_repo, "checkout", "main")
    assert "unresolved session changes" in run_leaf(clean_repo, "merge", "feature").stdout


def test_remote_commands_are_disabled_and_clone_variants_work(tmp_path):
    remote = make_repo(tmp_path, "remote")
    local = make_repo(tmp_path, "local")
    (remote / "a.txt").write_text("remote\n")
    run_leaf(remote, "save", "remote initial")

    for args in [
        ("remote",),
        ("remote", "add", "origin", str(remote)),
        ("fetch", "origin"),
        ("pull", "origin", "main"),
        ("push", "origin", "main"),
    ]:
        out = run_leaf(local, *args).stdout
        assert "Remote repository commands are currently disabled" in out

    assert "origin/main" not in branches(local)
    assert "Source is not a Leaf repository" in run_leaf(tmp_path, "clone", str(tmp_path / "missing")).stdout

    clone_dest = tmp_path / "clone"
    run_leaf(tmp_path, "clone", str(remote), str(clone_dest))
    assert (clone_dest / "a.txt").read_text() == "remote\n"
    default_parent = tmp_path / "default_clone_parent"
    default_parent.mkdir()
    run_leaf(default_parent, "clone", str(remote))
    assert (default_parent / "remote-clone" / "a.txt").read_text() == "remote\n"


def test_help_and_version_commands(tmp_path):
    for help_arg in ["help", "-h", "--help"]:
        result = run_leaf(tmp_path, help_arg)
        assert "DESCRIPTION:" in result.stdout
        assert "Create a new Leaf repository" in result.stdout
        assert "Usage:" in result.stdout
        assert "DISABLED REMOTE COMMANDS:" in result.stdout
        assert "Remote synchronization commands are currently disabled" in result.stdout

    version = run_leaf(tmp_path, "version")
    assert version.returncode == 0
    assert version.stdout.strip()


def test_fsck_reports_corrupt_references(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "a.txt").write_text("one\n")
    run_leaf(repo, "save", "one")
    first = commit_ids(repo)[0]

    branch_file = repo / ".leaf" / "branches.json"
    branch_data = json.loads(branch_file.read_text())
    branch_data["broken"] = "missingcommit"
    branch_file.write_text(json.dumps(branch_data))

    tag_file = repo / ".leaf" / "tags.json"
    tag_file.write_text(json.dumps({"badtag": "missingcommit"}))

    log_file = repo / ".leaf" / "log.json"
    log_data = json.loads(log_file.read_text())
    log_data[0]["parents"] = ["missingparent"]
    log_file.write_text(json.dumps(log_data))

    shutil.rmtree(repo / ".leaf" / "commits" / first)
    out = run_leaf(repo, "fsck").stdout
    assert "Missing commit directory" in out
    assert "Missing parent" in out
    assert "Branch broken points to missing commit" in out
    assert "Tag badtag points to missing commit" in out
    assert "Repository integrity issues found" in out
