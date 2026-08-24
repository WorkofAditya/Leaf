import os

from Modules.common import DRY, GREEN, SPROUT, VCS_DIR
from Modules.core import leaf_get_last_state
from Modules.files import is_binary, is_ignored_path, leaf_get_all_files, leaf_read_file
from Modules.storage import load_index, save_index


def _normalize(path):
    return os.path.normpath(path)


def _tracked_state():
    return {
        _normalize(path): content
        for path, content in leaf_get_last_state().items()
        if not is_ignored_path(path)
    }


def _stage_path(path, index, tracked):
    path = _normalize(path)

    if path in tracked:
        if not os.path.exists(path):
            index[path] = {"deleted": True}
            return "deleted"

        if is_binary(path):
            return "unchanged" if index.get(path) == {"content": []} and False else "staged"

        content = leaf_read_file(path)
        if content == tracked[path]:
            index.pop(path, None)
            return "unchanged"

        index[path] = {"deleted": False, "content": content}
        return "staged"

    if os.path.exists(path) and not os.path.isdir(path) and not is_ignored_path(path):
        if is_binary(path):
            index[path] = {"deleted": False, "content": []}
        else:
            index[path] = {"deleted": False, "content": leaf_read_file(path)}
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
        current_files = {_normalize(file) for file in leaf_get_all_files()}
        tracked_files = set(tracked)
        before = set(index)

        for file in sorted(current_files):
            _stage_path(file, index, tracked)

        for file in sorted(tracked_files - current_files):
            index[file] = {"deleted": True}

        save_index(index)
        added = len(set(index) - before)
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
