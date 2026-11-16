from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from Modules import storage
from Modules.files import is_binary, is_ignored_path, leaf_read_file, leaf_write_file
from Modules.graph import (
    commit_map,
    commit_parents,
    commit_chain,
    find_merge_base,
    first_parent_chain,
    is_ancestor,
)
from leaf_test_utils import main_wrapper


def test_commit_graph(ctx) -> None:
    log = [
        {"id": "root", "parents": []},
        {"id": "left", "parents": ["root"]},
        {"id": "right", "parents": ["root"]},
        {"id": "merge", "parents": ["left", "right"]},
    ]
    commits = commit_map(log)

    ctx.check(
        commit_chain("merge", commits) == ["merge", "left", "right", "root"],
        "Commit traversal visits both sides of a merge",
    )
    ctx.check(
        first_parent_chain("merge", commits) == ["merge", "left", "root"],
        "First-parent traversal follows only the mainline",
    )
    ctx.check(
        commit_parents({"id": "legacy", "parent": "root"}) == ["root"],
        "Legacy single-parent commits remain readable",
    )
    ctx.check(
        commit_parents({"id": "root", "parents": [], "parent": "legacy"}) == [],
        "An explicit empty parent list identifies a root commit",
    )
    ctx.check(is_ancestor("right", "merge", commits), "Second parent is recognized as an ancestor")
    ctx.check(is_ancestor("root", "merge", commits), "Root commit is recognized as an ancestor")
    ctx.check(not is_ancestor("missing", "merge", commits), "Unknown commits are not ancestors")
    ctx.check(
        find_merge_base("left", "right", commits) == "root",
        "Merge-base lookup finds the common root",
    )
    ctx.check(
        find_merge_base("merge", "right", commits) == "right",
        "Merge-base lookup handles a merge commit",
    )
    ctx.check(find_merge_base("left", "missing", commits) is None, "Missing merge-base inputs are handled")

    cyclic = commit_map([
        {"id": "one", "parents": ["two"]},
        {"id": "two", "parents": ["one"]},
    ])
    ctx.check(
        commit_chain("one", cyclic) == ["one", "two"],
        "Commit traversal terminates safely on malformed cycles",
    )
    ctx.check(
        first_parent_chain("one", cyclic) == ["one", "two"],
        "First-parent traversal terminates safely on malformed cycles",
    )


def test_file_helpers(ctx) -> None:
    files_dir = ctx.root / "file-fixtures"
    files_dir.mkdir()

    text_file = files_dir / "utf8.txt"
    text_file.write_text("café\nsecond line", encoding="utf-8")
    empty_file = files_dir / "empty.txt"
    empty_file.write_bytes(b"")
    binary_file = files_dir / "binary.bin"
    binary_file.write_bytes(b"header\0payload")
    invalid_utf8 = files_dir / "invalid.txt"
    invalid_utf8.write_bytes(b"\xff\xfe\xfa")

    ctx.check(not is_binary(str(text_file)), "UTF-8 text is classified as text")
    ctx.check(not is_binary(str(empty_file)), "Empty files are classified as text")
    ctx.check(is_binary(str(binary_file)), "Files containing a null byte are classified as binary")
    ctx.check(is_binary(str(invalid_utf8)), "Invalid UTF-8 files are classified as binary")
    ctx.check(
        leaf_read_file(str(text_file)) == ["café\n", "second line"],
        "Text reads preserve line endings and UTF-8 content",
    )
    ctx.check(leaf_read_file(str(invalid_utf8)) == [], "Unreadable text returns an empty result")

    written_file = files_dir / "nested" / "written.txt"
    leaf_write_file(str(written_file), ["first\n", "second\n"])
    ctx.check(
        written_file.read_text(encoding="utf-8") == "first\nsecond\n",
        "Writing a file creates missing parent directories",
    )

    ignore = {".leaf", ".git", "__pycache__", "*.pyc", "private"}
    ctx.check(is_ignored_path(".leaf/log.json", ignore), "Leaf metadata directories are ignored")
    ctx.check(is_ignored_path("nested/.git/config", ignore), "Nested Git directories are ignored")
    ctx.check(is_ignored_path("nested/__pycache__/module.pyc", ignore), "Nested Python caches are ignored")
    ctx.check(is_ignored_path("nested/cache.pyc", ignore), "Wildcard ignore rules match file extensions")
    ctx.check(is_ignored_path("deep/private/secret.txt", ignore), "Directory ignore rules apply at any depth")
    ctx.check(not is_ignored_path("nested/cache.py", ignore), "Wildcard ignore rules do not overmatch")
    ctx.check(not is_ignored_path("nested/visible.txt", ignore), "Unmatched paths remain trackable")


def test_storage_recovery(ctx) -> None:
    storage_dir = ctx.root / "storage-fixtures"
    storage_dir.mkdir()
    log_file = storage_dir / "log.json"
    backup_file = storage_dir / "log.bak"
    payload = [{"id": "first", "message": "first commit"}]

    with (
        patch.object(storage, "LOG_FILE", str(log_file)),
        patch.object(storage, "LOG_BACKUP", str(backup_file)),
    ):
        storage.safe_save_log(payload)
        ctx.check(
            json.loads(log_file.read_text(encoding="utf-8")) == payload,
            "Log storage writes valid JSON",
        )
        storage.safe_save_log([{"id": "second", "message": "second commit"}])
        ctx.check(
            json.loads(backup_file.read_text(encoding="utf-8")) == payload,
            "Saving a new log preserves the previous version",
        )

        log_file.write_text("{broken json", encoding="utf-8")
        ctx.check(
            storage.safe_load_log() == payload,
            "A corrupted log is recovered from its backup",
        )

        storage.safe_save_log([{"id": "recovered", "message": "recovered history"}])
        ctx.check(
            storage.safe_load_log() == [{"id": "recovered", "message": "recovered history"}],
            "A recovered log can be saved again",
        )

    atomic_file = storage_dir / "nested" / "metadata.json"
    storage._atomic_json_save(str(atomic_file), {"ready": True, "count": 3})
    ctx.check(
        json.loads(atomic_file.read_text(encoding="utf-8")) == {"ready": True, "count": 3},
        "Atomic JSON writes create parent directories and persist content",
    )
    leftovers = list(atomic_file.parent.glob("*.tmp"))
    ctx.check(not leftovers, "Atomic JSON writes leave no temporary files behind")


def run(ctx) -> None:
    test_commit_graph(ctx)
    test_file_helpers(ctx)
    test_storage_recovery(ctx)


if __name__ == "__main__":
    main_wrapper(__file__, run)
