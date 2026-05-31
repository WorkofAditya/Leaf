import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from leaf_web import repo_state, run_leaf, safe_child


def test_leaf_web_runs_real_leaf_commands(tmp_path):
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
