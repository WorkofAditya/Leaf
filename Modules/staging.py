import os
from pathlib import Path

from Modules.common import DRY, GREEN, SPROUT, VCS_DIR
from Modules.core import leaf_get_last_state
from Modules.files import is_binary, is_ignored_path, leaf_get_all_files, leaf_read_file
from Modules.storage import load_index, save_index


def _normalize(path):
    return os.path.normpath(str(path)).replace("\\", "/")


def _path_matches(left, right):
    return _normalize(left).casefold() == _normalize(right).casefold()


def _tracked_state():
    return {
        _normalize(path): content
        for path, content in leaf_get_last_state().items()
        if not is_ignored_path(path)
    }


def _working_tree_path(path):
    requested = _normalize(path)
    for actual in leaf_get_all_files():
        if _path_matches(actual, requested):
            return actual
    candidate = Path(path)
    if candidate.is_file():
        return str(candidate)
    return None


def _stage_path(path, index, tracked):
    requested = _normalize(path)

    tracked_path = next((item for item in tracked if _path_matches(item, requested)), None)
    if tracked_path is not None:
        actual = _working_tree_path(tracked_path)
        if actual is None:
            index[tracked_path] = {"deleted": True}
            return "deleted"

        if is_binary(actual):
            current_content = []
        else:
            current_content = leaf_read_file(actual)

        if current_content == tracked[tracked_path]:
            index.pop(tracked_path, None)
            return "unchanged"

        index[tracked_path] = {"deleted": False, "content": current_content}
        return "staged"

    actual = _working_tree_path(path)
    if actual is not None and not os.path.isdir(actual) and not is_ignored_path(actual):
        key = _normalize(actual)
        if is_binary(actual):
            index[key] = {"deleted": False, "content": []}
        else:
            index[key] = {"deleted": False, "content": leaf_read_file(actual)}
        return "staged"

    return None


def leaf_add(path="."):
    if not os.path.isdir(VCS_DIR):
        print(f"{DRY} Not a repository")
        return

    index = load_index()
    tracked = _tracked_state()

    if path in (None, ""):
        path = "."

    if path == ".":
        current_files = [_normalize(file) for file in leaf_get_all_files()]
        tracked_files = set(tracked)

        for file in current_files:
            _stage_path(file, index, tracked)

        current_set = set(current_files)
        for file in sorted(tracked_files - current_set):
            index[file] = {"deleted": True}

        save_index(index)
        print(f"{SPROUT} Staged {len(index)} change(s)")
        return

    result = _stage_path(path, index, tracked)
    if result == "deleted":
        print(f"{GREEN}{SPROUT} Staged deletion: {path}")
    elif result == "staged":
        print(f"{GREEN}{SPROUT} Staged: {path}")
    elif result == "unchanged":
        print(f"{DRY} No changes to stage: {path}")
    else:
        print(f"{DRY} Nothing to stage: {path}")
    save_index(index)
