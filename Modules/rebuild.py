import os

from Modules.common import COMMITS_DIR
from Modules.files import leaf_get_all_files, leaf_read_file
from Modules.graph import first_parent_chain, commit_map


def leaf_rebuild(commit_id, log):
    if not commit_id:
        return {}
    files = {}
    cmap = commit_map(log)
    chain = list(reversed(first_parent_chain(commit_id, cmap)))
    for cid in chain:
        c = cmap[cid]
        cpath = os.path.join(COMMITS_DIR, cid)

        if c["type"] == "snapshot":
            for root, _, fs in os.walk(cpath):
                for f in fs:
                    rel = os.path.relpath(os.path.join(root, f), cpath)
                    files[rel] = leaf_read_file(os.path.join(root, f))
        else:
            for file in c.get("deleted", []):
                files.pop(file, None)

            for file, diff in c.get("changes", {}).items():
                patched = []
                for line in diff:
                    if line.startswith("  ") or line.startswith("+ "):
                        patched.append(line[2:])
                files[file] = patched
    return files


def write_working_tree(files):
    current_files = set(leaf_get_all_files())
    target_files = set(files.keys())
    for f in current_files - target_files:
        try:
            os.remove(f)
        except OSError:
            pass

    for path, content in files.items():
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            f.writelines(content)
