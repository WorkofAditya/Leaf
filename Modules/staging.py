import os

from Modules.common import DRY, GREEN, SPROUT, VCS_DIR
from Modules.core import leaf_get_last_state
from Modules.files import is_binary, is_ignored_path, leaf_get_all_files, leaf_read_file
from Modules.storage import load_index, save_index


def _tracked_state():
    return {
        path: content
        for path, content in leaf_get_last_state().items()
        if not is_ignored_path(path)
    }


def _stage_path(path, index, tracked):
    path = os.path.normpath(path).replace(os.sep, "/")
    if path in tracked:
        if not os.path.exists(path):
            index[path] = {"deleted": True}
            return "deleted"
        if is_binary(path):
            index[path] = {"content": []}
        else:
            index[path] = {"content": leaf_read_file(path)}
        return "staged"
    if os.path.exists(path) and not os.path.isdir(path) and not is_ignored_path(path):
        if is_binary(path):
            index[path] = {"content": []}
        else:
            index[path] = {"content": leaf_read_file(path)}
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
        current_files = set(leaf_get_all_files())
        tracked_files = set(tracked)

        for file in sorted(current_files):
            _stage_path(file, index, tracked)

        for file in sorted(tracked_files - current_files):
            index[file] = {"deleted": True}

        save_index(index)
        print(f"{SPROUT} Staged {len(index)} change(s)")
        return

    result = _stage_path(path, index, tracked)
    if result == "deleted":
        print(f"{GREEN}{SPROUT} Staged deletion: {path}")
    elif result == "staged":
        print(f"{GREEN}{SPROUT} Staged: {path}")
    else:
        print(f"{DRY} Nothing to stage: {path}")
    save_index(index)
