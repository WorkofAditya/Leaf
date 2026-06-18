import difflib
import os
import subprocess
import tempfile
import time

from Modules.common import (
    BRANCHES_FILE,
    REMOTES_FILE,
    TAGS_FILE,
    COMMITS_DIR,
    DRY,
    LEAF,
    TREE,
    VCS_DIR,
)
from Modules.files import is_binary, is_ignored_path, leaf_read_file
from Modules.head_utils import get_head_module
from Modules.rebuild import leaf_rebuild
from Modules.storage import safe_load_log, safe_save_log, save_branches, save_index, save_remotes, save_sessions, save_tags


def _progress(message):
    print(f"{TREE} {message}", flush=True)


def _load_json_file(path, default):
    try:
        import json
        with open(path) as fh:
            data = json.load(fh)
        return data if isinstance(data, type(default)) else default
    except Exception:
        return default


def _run_git(args, cwd=".", input_data=None):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        input=input_data,
        text=True,
        capture_output=True,
        check=True,
    )


def _git_available():
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def _leaf_commit_id(git_sha, used):
    base = git_sha[:10]
    if base not in used:
        used.add(base)
        return base
    for length in range(11, 41):
        candidate = git_sha[:length]
        if candidate not in used:
            used.add(candidate)
            return candidate
    suffix = 1
    while f"{base}-{suffix}" in used:
        suffix += 1
    candidate = f"{base}-{suffix}"
    used.add(candidate)
    return candidate


def _git_commit_timestamp(sha):
    raw = _run_git(["show", "-s", "--format=%ct", sha]).stdout.strip()
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(raw)))


def _git_commit_message(sha):
    return _run_git(["show", "-s", "--format=%B", sha]).stdout.rstrip("\n") or "save"


def _git_commit_parents(sha):
    line = _run_git(["show", "-s", "--format=%P", sha]).stdout.strip()
    return line.split() if line else []


def _git_text_state(sha):
    state = {}
    files = _run_git(["ls-tree", "-r", "--name-only", sha]).stdout.splitlines()
    for path in files:
        if is_ignored_path(path):
            continue
        try:
            data = _run_git(["show", f"{sha}:{path}"]).stdout
        except (UnicodeDecodeError, subprocess.CalledProcessError):
            continue
        # Keep Leaf's existing text-only storage semantics.
        if "\0" in data:
            continue
        state[path] = data.splitlines(True)
    return state


def _diff_states(base_state, target_state):
    changes = {}
    deleted = sorted(set(base_state) - set(target_state))
    for path in sorted(set(target_state)):
        old = base_state.get(path, [])
        new = target_state[path]
        if old != new:
            changes[path] = list(difflib.ndiff(old, new))
    return changes, deleted


def _write_leaf_commit_files(commit_path, commit_data, state):
    os.makedirs(commit_path, exist_ok=True)
    if commit_data["type"] == "snapshot":
        for path, lines in state.items():
            full_path = os.path.join(commit_path, path)
            os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)
            with open(full_path, "w") as fh:
                fh.writelines(lines)
    else:
        for path, diff in commit_data.get("changes", {}).items():
            diff_path = os.path.join(commit_path, path + ".diff")
            os.makedirs(os.path.dirname(diff_path) or ".", exist_ok=True)
            with open(diff_path, "w") as fh:
                fh.write("\n".join(diff))
        for path, lines in state.items():
            state_path = os.path.join(commit_path, "state", path)
            os.makedirs(os.path.dirname(state_path) or ".", exist_ok=True)
            with open(state_path, "w") as fh:
                fh.writelines(lines)


def leaf_import_git():
    if not _git_available():
        print(f"{DRY} Git is not installed")
        return
    if not os.path.isdir(".git"):
        print(f"{DRY} No .git repository found")
        return
    _progress("Starting Git import")
    os.makedirs(COMMITS_DIR, exist_ok=True)

    _progress("Reading Git commit graph")
    shas = _run_git(["rev-list", "--topo-order", "--reverse", "--all"]).stdout.splitlines()
    used = set()
    sha_to_leaf = {sha: _leaf_commit_id(sha, used) for sha in shas}
    log = []
    states = {}
    for index, sha in enumerate(shas, 1):
        leaf_id = sha_to_leaf[sha]
        _progress(f"Importing commit {index}/{len(shas)} {sha[:12]} -> {leaf_id}")
        parents = [sha_to_leaf[p] for p in _git_commit_parents(sha) if p in sha_to_leaf]
        parent = parents[0] if parents else None
        state = _git_text_state(sha)
        base = states.get(parent, {}) if parent else {}
        commit_data = {
            "id": leaf_id,
            "git_sha": sha,
            "message": _git_commit_message(sha),
            "time": _git_commit_timestamp(sha),
            "branch": None,
            "parent": parent,
            "parents": parents,
            "type": "snapshot" if not parents else "diff",
            "changes": {},
            "deleted": [],
        }
        if commit_data["type"] == "snapshot":
            commit_data["files"] = sorted(state)
        else:
            commit_data["changes"], commit_data["deleted"] = _diff_states(base, state)
        _write_leaf_commit_files(os.path.join(COMMITS_DIR, leaf_id), commit_data, state)
        states[leaf_id] = state
        log.append(commit_data)

    _progress("Importing branches")
    branches = {}
    branch_lines = _run_git(["for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads"]).stdout.splitlines()
    for line in branch_lines:
        name, sha = line.split(" ", 1)
        if sha in sha_to_leaf:
            branches[name] = sha_to_leaf[sha]
    if not branches:
        branches["main"] = None

    _progress("Importing tags")
    tags = {}
    tag_lines = _run_git(["for-each-ref", "--format=%(refname:short) %(objectname) %(objecttype)", "refs/tags"]).stdout.splitlines()
    for line in tag_lines:
        name, obj, obj_type = line.split(" ", 2)
        target_sha = obj
        if obj_type == "tag":
            target_sha = _run_git(["rev-list", "-n", "1", obj]).stdout.strip()
        if target_sha in sha_to_leaf:
            tags[name] = sha_to_leaf[target_sha]

    _progress("Importing remotes")
    remotes = {}
    remote_lines = _run_git(["remote", "-v"]).stdout.splitlines()
    for line in remote_lines:
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "(fetch)":
            remotes[parts[0]] = parts[1]

    _progress("Preserving HEAD")
    current_branch = _run_git(["branch", "--show-current"]).stdout.strip()
    head_sha = _run_git(["rev-parse", "--verify", "HEAD"]).stdout.strip() if shas else ""
    head_id = sha_to_leaf.get(head_sha, "")
    if current_branch and current_branch in branches:
        for c in log:
            if c["id"] == branches[current_branch]:
                c["branch"] = current_branch
    safe_save_log(log)
    save_branches(branches)
    save_sessions({})
    save_index({})
    save_tags(tags)
    save_remotes(remotes)
    get_head_module().init_head(VCS_DIR)
    get_head_module().write_head(VCS_DIR, head_id)
    get_head_module().write_current_branch(VCS_DIR, current_branch if current_branch in branches else "")
    print(f"{LEAF} Imported Git repository into .leaf ({len(log)} commits, {len(branches)} branches, {len(tags)} tags, {len(remotes)} remotes)")


def _commit_state(commit):
    if not commit:
        return {}
    state_dir = os.path.join(COMMITS_DIR, commit["id"], "state")
    if os.path.isdir(state_dir):
        state = {}
        for root, _, files in os.walk(state_dir):
            for name in files:
                path = os.path.join(root, name)
                rel = os.path.relpath(path, state_dir)
                if not is_binary(path):
                    state[rel] = leaf_read_file(path)
        return state
    return leaf_rebuild(commit["id"], safe_load_log())


def _git_ref_name(branch):
    cleaned = branch.strip().replace(" ", "-")
    return cleaned or "main"


def leaf_export_git():
    if not _git_available():
        print(f"{DRY} Git is not installed")
        return
    if not os.path.isdir(VCS_DIR):
        print(f"{DRY} No .leaf repository found")
        return
    if os.path.exists(".git"):
        print(f"{DRY} .git already exists; refusing to overwrite it")
        return
    _progress("Starting Git export")
    log = safe_load_log()
    os.makedirs(".git", exist_ok=False)
    _progress("Initializing .git repository")
    _run_git(["init", "."])
    if not log:
        print(f"{TREE} Created empty Git repository")
        return

    env = os.environ.copy()
    env.setdefault("GIT_AUTHOR_NAME", "Leaf")
    env.setdefault("GIT_AUTHOR_EMAIL", "leaf@example.invalid")
    env.setdefault("GIT_COMMITTER_NAME", env["GIT_AUTHOR_NAME"])
    env.setdefault("GIT_COMMITTER_EMAIL", env["GIT_AUTHOR_EMAIL"])
    marks = {}
    for index, commit in enumerate(log, 1):
        _progress(f"Exporting commit {index}/{len(log)} {commit['id']}")
        state = _commit_state(commit)
        for path in list(state):
            if path.startswith(".git/") or path == ".git":
                state.pop(path, None)
        commit_env = env.copy()
        with tempfile.TemporaryDirectory(prefix="leaf-export-") as work_tree:
            index_path = os.path.join(work_tree, ".git-index")
            commit_env["GIT_INDEX_FILE"] = index_path
            subprocess.run(["git", "read-tree", "--empty"], check=True, env=commit_env)
            for path, lines in state.items():
                full_path = os.path.join(work_tree, path)
                os.makedirs(os.path.dirname(full_path) or work_tree, exist_ok=True)
                with open(full_path, "w") as fh:
                    fh.writelines(lines)
            subprocess.run(["git", f"--work-tree={work_tree}", "add", "-A"], check=True, env=commit_env)
            tree = subprocess.run(["git", "write-tree"], text=True, capture_output=True, check=True, env=commit_env).stdout.strip()
        stamp = commit.get("time") or "1970-01-01 00:00:00"
        commit_env["GIT_AUTHOR_DATE"] = stamp
        commit_env["GIT_COMMITTER_DATE"] = stamp
        parents = [marks[p] for p in commit.get("parents", []) if p in marks]
        args = ["commit-tree", tree]
        for parent in parents:
            args.extend(["-p", parent])
        args.extend(["-m", commit.get("message") or "save"])
        new_sha = subprocess.run(["git", *args], text=True, capture_output=True, check=True, env=commit_env).stdout.strip()
        marks[commit["id"]] = new_sha

    _progress("Exporting branches")
    branches = _load_json_file(BRANCHES_FILE, {"main": log[-1]["id"]})
    for branch, leaf_id in branches.items():
        if leaf_id in marks:
            _run_git(["update-ref", f"refs/heads/{_git_ref_name(branch)}", marks[leaf_id]])

    _progress("Exporting tags")
    tags = _load_json_file(TAGS_FILE, {})
    for tag, leaf_id in tags.items():
        if leaf_id in marks:
            _run_git(["tag", "-f", tag, marks[leaf_id]])

    _progress("Exporting remotes")
    remotes = _load_json_file(REMOTES_FILE, {})
    for name, url in remotes.items():
        _run_git(["remote", "add", name, url])
    _progress("Restoring HEAD")
    head_branch = get_head_module().read_current_branch(VCS_DIR)
    head_id = get_head_module().read_head(VCS_DIR) or log[-1]["id"]
    if head_branch and branches.get(head_branch) in marks:
        _run_git(["symbolic-ref", "HEAD", f"refs/heads/{_git_ref_name(head_branch)}"])
    elif head_id in marks:
        with open(os.path.join(".git", "HEAD"), "w") as fh:
            fh.write(marks[head_id] + "\n")
    _progress("Checking out exported HEAD")
    _run_git(["reset", "--hard", "HEAD"])
    print(f"{LEAF} Exported Leaf repository into .git ({len(log)} commits, {len(branches)} branches, {len(tags)} tags, {len(remotes)} remotes)")
