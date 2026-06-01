import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from leaf_web import action_to_args, parse_status, repo_state, run_leaf, safe_child


def test_leaf_web_runs_real_leaf_workflow_operations(tmp_path):
    init = run_leaf(tmp_path, ["init"])
    assert init["ok"]
    assert "Initialized" in init["stdout"]

    (tmp_path / "README.md").write_text("hello from web\n")
    add = run_leaf(tmp_path, ["add", "README.md"])
    assert add["ok"]
    save = run_leaf(tmp_path, ["save", "web commit"])
    assert save["ok"]

    state = repo_state(tmp_path)
    assert state["is_repo"] is True
    assert state["current_branch"] == "main"
    assert state["log"][-1]["message"] == "web commit"
    assert state["branches"]["main"] == state["head"]
    assert {file["path"] for file in state["files"]} == {"README.md"}


def test_safe_child_blocks_leaf_metadata_and_path_escape(tmp_path):
    assert safe_child(tmp_path, "docs/readme.md") == tmp_path / "docs" / "readme.md"

    for value in ("../outside.txt", ".leaf/log.json"):
        try:
            safe_child(tmp_path, value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{value} should be blocked")


def test_workflow_actions_map_to_leaf_operations():
    assert action_to_args("stage_file", {"path": "README.md"}) == ["add", "README.md"]
    assert action_to_args("commit", {"message": "polish docs"}) == ["save", "polish docs"]
    assert action_to_args("switch_branch", {"branch": "feature"}) == ["checkout", "feature"]
    assert action_to_args("merge_branch", {"branch": "feature"}) == ["merge", "feature"]


def test_parse_status_returns_structured_changes():
    status = "🌱 Staged: README.md\n🍃 Modified: app.py\n🍂 Deleted: old.txt\n"
    changes = parse_status(status, {"README.md": {"deleted": False, "content": []}})
    assert {change["path"] for change in changes} == {"README.md", "app.py", "old.txt"}
    assert next(change for change in changes if change["path"] == "README.md")["staged"] is True
    assert next(change for change in changes if change["path"] == "app.py")["status"] == "modified"
