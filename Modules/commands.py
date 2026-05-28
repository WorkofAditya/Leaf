import difflib
import os
import shutil
import time
import urllib.request

from Modules.common import BLUE, BRANCHES_FILE, COMMITS_DIR, DRY, GREEN, GRAY, HERB, LEAF, LOG_FILE, RED, RESET, SPROUT, TREE, VCS_DIR
from Modules.core import leaf_get_head_commit_id, leaf_get_last_state, leaf_hash_commit
from Modules.files import is_binary, leaf_get_all_files, leaf_read_file, leaf_snapshot
from Modules.graph import commit_chain, commit_map, is_ancestor
from Modules.head_utils import get_head_module
from Modules.rebuild import leaf_rebuild, write_working_tree
from Modules.storage import load_branches, load_sessions, safe_load_log, safe_save_log, save_branches, save_sessions


def leaf_init():
    os.makedirs(COMMITS_DIR, exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("[]")
    if not os.path.exists(BRANCHES_FILE):
        with open(BRANCHES_FILE, "w") as f:
            f.write('{"main": null}')
    save_sessions({})
    get_head_module().init_head(VCS_DIR)
    get_head_module().write_current_branch(VCS_DIR, "main")
    print(f"{SPROUT} Initialized empty leaf repository")


def leaf_save(msg):
    if not os.path.exists(VCS_DIR):
        print(f"{DRY} Not a repository")
        return
    log = safe_load_log()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    commit_id = leaf_hash_commit(msg + timestamp + str(time.time()))[:10]
    commit_path = os.path.join(COMMITS_DIR, commit_id)
    commit_data = {"id": commit_id, "message": msg, "time": timestamp, "branch": get_head_module().read_current_branch(VCS_DIR), "parent": leaf_get_head_commit_id(log), "type": "diff", "changes": {}, "deleted": []}
    current_files = set(leaf_get_all_files())
    if not log:
        os.makedirs(commit_path)
        leaf_snapshot(commit_path)
        commit_data["type"] = "snapshot"
        commit_data["files"] = list(current_files)
    else:
        previous_state = leaf_get_last_state()
        deleted = set(previous_state.keys()) - current_files
        commit_data["deleted"] = list(deleted)
        for file in current_files:
            if is_binary(file):
                continue
            new = leaf_read_file(file)
            old = previous_state.get(file, [])
            if new != old:
                commit_data["changes"][file] = list(difflib.ndiff(old, new))
        if not commit_data["changes"] and not deleted:
            print(f"{DRY} No changes detected, nothing to save")
            return
        os.makedirs(commit_path)
        for file, diff in commit_data["changes"].items():
            save_path = os.path.join(commit_path, file + ".diff")
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "w") as f:
                f.write("\n".join(diff))
    log.append(commit_data)
    safe_save_log(log)
    branches = load_branches()
    branch = get_head_module().read_current_branch(VCS_DIR)
    if branch:
        branches[branch] = commit_id
        save_branches(branches)
        sessions = load_sessions()
        if branch in sessions:
            del sessions[branch]
            save_sessions(sessions)
    get_head_module().write_head(VCS_DIR, commit_id)
    print(f"{LEAF} Saved commit {commit_id}")


def leaf_log():
    if not os.path.exists(LOG_FILE):
        print(f"{DRY} No commits")
        return
    log = safe_load_log()
    head_id = leaf_get_head_commit_id(log)
    cmap = commit_map(log)
    if not head_id or head_id not in cmap:
        print(f"{DRY} No commits")
        return
    for commit_id in commit_chain(head_id, cmap):
        c = cmap[commit_id]
        marker = " (HEAD)" if c["id"] == head_id else ""
        print(f"\n{HERB} commit {c['id']}{marker}")
        print(f"{LEAF} Message: {c['message']}")
        print(f"{SPROUT} Time: {c['time']}")




def leaf_diff(commit_id=None):
    log = safe_load_log()
    if not log:
        print(f"{DRY} No commits")
        return
    if commit_id is None:
        commit_id = leaf_get_head_commit_id(log)
    ids = [c["id"] for c in log]
    if commit_id not in ids:
        print(f"{DRY} Invalid commit id")
        return
    target = leaf_rebuild(commit_id, log)
    current = {}
    for f in leaf_get_all_files():
        if not is_binary(f):
            current[f] = leaf_read_file(f)
    any_diff = False
    for f in set(target.keys()) | set(current.keys()):
        old = target.get(f, [])
        new = current.get(f, [])
        if old != new:
            any_diff = True
            print(f"\n{HERB} Diff: {f}")
            for line in difflib.unified_diff(old, new, lineterm=""):
                if line.startswith("+") and not line.startswith("+++"):
                    print(f"{GREEN}{line}{RESET}")
                elif line.startswith("-") and not line.startswith("---"):
                    print(f"{RED}{line}{RESET}")
                else:
                    print(line)
    if not any_diff:
        print(f"{HERB} No differences found")


def leaf_restore(commit_id):
    log = safe_load_log()
    if commit_id not in [c["id"] for c in log]:
        print(f"{DRY} Invalid commit id")
        return
    files = leaf_rebuild(commit_id, log)
    if files is None:
        print(f"{DRY} Restore failed")
        return
    write_working_tree(files)
    get_head_module().write_head(VCS_DIR, commit_id)
    get_head_module().write_current_branch(VCS_DIR, "")
    print(f"{TREE} Restored to commit {commit_id} (detached HEAD)")


def leaf_status():
    if not os.path.exists(LOG_FILE):
        print(f"{DRY} No repository")
        return
    last = leaf_get_last_state()
    current = set(leaf_get_all_files())
    last_files = set(last.keys())
    added, deleted, modified = current - last_files, last_files - current, []
    for f in current & last_files:
        if not is_binary(f) and leaf_read_file(f) != last[f]:
            modified.append(f)
    if not added and not deleted and not modified:
        print(f"{HERB} Clean working tree")
        return
    for f in added:
        print(f"{GRAY}{SPROUT} Added: {f}{RESET}")
    for f in modified:
        print(f"{BLUE}{LEAF} Modified: {f}{RESET}")
    for f in deleted:
        print(f"{RED}{DRY} Deleted: {f}{RESET}")


def leaf_help():
    print("""Leaf Version Control System\n\nUSAGE:\n    leaf <command> [options]\n\nCOMMANDS:\n    init\n        Initialize a new Leaf repository\n\n    save <message>\n        Create a new commit with current changes\n\n    log\n        Show current branch or detached HEAD history\n\n    restore <commit_id>\n        Restore repository to a specific commit in detached HEAD mode\n\n    status\n        Show changed, added, and deleted files\n\n    diff [commit_id]\n        Show differences against HEAD or a commit\n\n    ignore <path>\n        Add file or directory to .leafignore\n\n    branch [name]\n        List branches or create a new branch\n\n    checkout <branch>\n        Switch to another branch\n\n    merge <branch>\n        Merge a branch into current branch\n\n    help\n        Show help information\n\n    version\n        Show current Leaf version\n\nALIASES:\n    leaf help\n    leaf -h\n    leaf --help\n\n    leaf version\n    leaf -v\n\nEXAMPLES:\n    leaf init\n    leaf save "Initial commit"\n    leaf branch feature-login\n    leaf checkout feature-login\n\nLeaf VCS\nFast. Minimal. Local.""")


def leaf_version():
    for url in ["https://raw.githubusercontent.com/WorkofAditya/Leaf/refs/heads/main/version.txt", "https://raw.githubusercontent.com/WorkofAditya/Leaf/main/version.txt"]:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                text = response.read().decode("utf-8").strip()
                if text:
                    print(text)
                    return
        except:
            continue
    print(f"{DRY} Could not fetch version from remote")


def leaf_ignore(target):
    if not target:
        print(f"{DRY} Missing file/folder to ignore")
        return
    existing = set()
    if os.path.exists(".leafignore"):
        with open(".leafignore", "r") as f:
            for line in f:
                value = line.strip()
                if value and not value.startswith("#"):
                    existing.add(value)
    if target in existing:
        print(f"{HERB} Already ignored: {target}")
        return
    with open(".leafignore", "a") as f:
        if os.path.exists(".leafignore") and os.path.getsize(".leafignore") > 0:
            f.write("\n")
        f.write(target)
    print(f"{SPROUT} Added to .leafignore: {target}")


def leaf_branch(name=None):
    branches = load_branches(); current = get_head_module().read_current_branch(VCS_DIR)
    if name is None:
        for b in sorted(branches.keys()): print(f"{'*' if b == current else ' '} {b}")
        return
    if name in branches: print(f"{DRY} Branch already exists: {name}"); return
    branches[name] = leaf_get_head_commit_id(); save_branches(branches); print(f"{SPROUT} Created branch {name}")


def _capture_working_state():
    state = {}
    for file in leaf_get_all_files():
        if not is_binary(file):
            state[file] = leaf_read_file(file)
    return state


def _has_uncommitted_changes(state, head_state):
    for f in set(state.keys()) | set(head_state.keys()):
        if state.get(f, []) != head_state.get(f, []):
            return True
    return False


def _save_branch_session(branch):
    head_state = leaf_get_last_state()
    working_state = _capture_working_state()
    sessions = load_sessions()
    if _has_uncommitted_changes(working_state, head_state):
        sessions[branch] = working_state
    elif branch in sessions:
        del sessions[branch]
    save_sessions(sessions)


def _restore_branch_session(branch, fallback_state):
    sessions = load_sessions()
    write_working_tree(sessions.get(branch, fallback_state) or {})


def leaf_checkout(branch_name):
    branches = load_branches()
    if branch_name not in branches:
        print(f"{DRY} Unknown branch: {branch_name}"); return
    current_branch = get_head_module().read_current_branch(VCS_DIR)
    if current_branch:
        _save_branch_session(current_branch)
    target = branches[branch_name]
    files = leaf_rebuild(target, safe_load_log()) if target else {}
    _restore_branch_session(branch_name, files)
    get_head_module().write_head(VCS_DIR, target or "")
    get_head_module().write_current_branch(VCS_DIR, branch_name)
    print(f"{TREE} Switched to branch {branch_name}")


def _has_session_changes(branch):
    sessions = load_sessions()
    if branch not in sessions:
        return False
    head_id = load_branches().get(branch)
    head_state = leaf_rebuild(head_id, safe_load_log()) if head_id else {}
    return _has_uncommitted_changes(sessions[branch], head_state)


def _resolve_session_before_sensitive(branch):
    if not _has_session_changes(branch):
        return True
    print(f"{HERB} Branch '{branch}' has unresolved session changes.")
    print("Choose: [c]ommit session / [d]iscard session / [x]cancel")
    choice = input("> ").strip().lower()
    sessions = load_sessions()
    if choice.startswith("c"):
        saved = sessions.get(branch, {})
        write_working_tree(saved)
        print(f"{SPROUT} Session restored. Run 'leaf save <message>' to commit these changes, then retry merge.")
        return False
    if choice.startswith("d"):
        if branch in sessions:
            del sessions[branch]
            save_sessions(sessions)
        print(f"{DRY} Discarded saved session for branch '{branch}'")
        return True
    print(f"{DRY} Merge cancelled")
    return False


def leaf_merge(source_branch):
    branches = load_branches(); current_branch = get_head_module().read_current_branch(VCS_DIR)
    if source_branch not in branches: print(f"{DRY} Unknown branch: {source_branch}"); return
    if not current_branch: print(f"{DRY} Merge requires being on a branch"); return
    if source_branch == current_branch: print(f"{HERB} Already on {source_branch}"); return
    if not _resolve_session_before_sensitive(source_branch):
        return
    log = safe_load_log(); cmap = commit_map(log); target, source = branches.get(current_branch), branches.get(source_branch)
    if not source or target == source or is_ancestor(source, target, cmap): print(f"{HERB} Already up to date"); return
    if not is_ancestor(target, source, cmap): print(f"{DRY} Non fast-forward merge not supported yet"); return
    write_working_tree(leaf_rebuild(source, log) or {}); branches[current_branch] = source; save_branches(branches); get_head_module().write_head(VCS_DIR, source)
    print(f"{TREE} Fast-forward merged {source_branch} into {current_branch}")
