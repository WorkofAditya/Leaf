import os

from Modules.common import COMMITS_DIR
from Modules.files import is_binary, leaf_get_all_files, leaf_read_file, leaf_write_file
from Modules.graph import commit_map, first_parent_chain


def leaf_rebuild(commit_id, log):
    if not commit_id:
        return {}

    files = {}
    commits = commit_map(log)
    chain = reversed(first_parent_chain(commit_id, commits))

    for commit_id in chain:
        commit = commits[commit_id]
        commit_path = os.path.join(COMMITS_DIR, commit_id)

        if commit["type"] == "snapshot":
            for root, _, names in os.walk(commit_path):
                for name in names:
                    path = os.path.join(root, name)
                    if is_binary(path):
                        continue

                    relative_path = os.path.relpath(path, commit_path)
                    files[relative_path] = leaf_read_file(path)
            continue

        for path in commit.get("deleted", []):
            files.pop(path, None)

        for path, diff in commit.get("changes", {}).items():
            lines = []
            for line in diff:
                if line.startswith(("  ", "+ ")):
                    lines.append(line[2:])
            files[path] = lines

    return files


def write_working_tree(files):
    current_files = {
        path for path in leaf_get_all_files()
        if not is_binary(path)
    }
    target_files = set(files)

    for path in current_files - target_files:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    for path, lines in files.items():
        leaf_write_file(path, lines)
