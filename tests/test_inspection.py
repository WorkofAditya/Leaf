"""Regression checks for the read-only commit inspection API used by the GUI."""

import os
import tempfile
from pathlib import Path

from Modules.commands import leaf_init, leaf_save
from Modules.inspection import commit_file_changes, file_diff, file_history
from Modules.staging import leaf_add
from Modules.storage import safe_load_log


def commit(path, message):
    leaf_add(path)
    leaf_save(message)
    return safe_load_log()[-1]["id"]


def main():
    old = os.getcwd()
    with tempfile.TemporaryDirectory() as directory:
        os.chdir(directory)
        leaf_init()
        Path("file1.txt").write_text("one\n")
        Path("file2.txt").write_text("unstaged\n")
        initial = commit("file1.txt", "initial file")
        assert {item["path"] for item in commit_file_changes(initial, safe_load_log())} == {"file1.txt"}
        assert "file2.txt" not in {item["path"] for item in commit_file_changes(initial, safe_load_log())}
        Path("file1.txt").write_text("two\n")
        modified = commit("file1.txt", "modify file")
        Path("src/test").mkdir(parents=True)
        Path("src/test/example.py").write_text("print('nested')\n")
        nested = commit("src/test/example.py", "add nested file")
        Path("file1.txt").unlink()
        deleted = commit("file1.txt", "delete file")
        log = safe_load_log()
        assert commit_file_changes(deleted, log) == [{"path": "file1.txt", "status": "D"}]
        assert file_history("file1.txt", deleted, log) == [deleted, modified, initial]
        assert file_history("src/test/example.py", deleted, log) == [nested]
        assert file_diff(nested, "src/test/example.py", log)["status"] == "A"
        assert file_diff(deleted, "file1.txt", log)["status"] == "D"
    os.chdir(old)
    print("PASS inspection history and diffs")


if __name__ == "__main__":
    main()
