import difflib
import os
import shutil
import time
import urllib.request

from Modules.common import (
    BLUE,
    BRANCHES_FILE,
    COMMITS_DIR,
    DRY,
    GREEN,
    GRAY,
    HERB,
    INDEX_FILE,
    LEAF,
    LOG_FILE,
    MERGE_STATE_FILE,
    RED,
    REMOTES_FILE,
    RESET,
    SPROUT,
    TAGS_FILE,
    TREE,
    VCS_DIR,
)
from Modules.core import leaf_get_head_commit_id, leaf_get_last_state, leaf_hash_commit
from Modules.files import is_binary, leaf_get_all_files, leaf_read_file, leaf_snapshot
from Modules.graph import commit_chain, commit_map, find_merge_base, is_ancestor
from Modules.git_interop import leaf_export_git, leaf_import_git
from Modules.head_utils import get_head_module
from Modules.rebuild import leaf_rebuild, write_working_tree
from Modules.storage import (
    clear_index,
    clear_merge_state,
    load_branches,
    load_index,
    load_merge_state,
    load_remotes,
    load_sessions,
    load_tags,
    safe_load_log,
    safe_save_log,
    save_branches,
    save_index,
    save_merge_state,
    save_remotes,
    save_sessions,
    save_tags,
)


def leaf_init():
    os.makedirs(COMMITS_DIR, exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("[]")
    if not os.path.exists(BRANCHES_FILE):
        with open(BRANCHES_FILE, "w") as f:
            f.write('{"main": null}')
    save_sessions({})
    save_index({})
    save_tags({})
    save_remotes({})
    clear_merge_state()
    get_head_module().init_head(VCS_DIR)
    get_head_module().write_current_branch(VCS_DIR, "main")
    print(f"{SPROUT} Initialized empty leaf repository")


def _current_working_state():
    state = {}
    for file in leaf_get_all_files():
        if not is_binary(file):
            state[file] = leaf_read_file(file)
    return state


def _diff_states(base_state, target_state):
    changes = {}
    deleted = sorted(set(base_state) - set(target_state))
    for file in sorted(set(target_state)):
        old = base_state.get(file, [])
        new = target_state[file]
        if old != new:
            changes[file] = list(difflib.ndiff(old, new))
    return changes, deleted


def _write_commit_files(commit_path, commit_data, target_state):
    os.makedirs(commit_path, exist_ok=True)
    if commit_data["type"] == "snapshot":
        leaf_snapshot(commit_path)
        return
    for file, diff in commit_data.get("changes", {}).items():
        save_path = os.path.join(commit_path, file + ".diff")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w") as f:
            f.write("\n".join(diff))
    for file in target_state:
        full_path = os.path.join(commit_path, "state", file)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.writelines(target_state[file])


def _create_commit(msg, target_state=None, parents=None, branch=None, merge=False):
    log = safe_load_log()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    commit_id = leaf_hash_commit(msg + timestamp + str(time.time()))[:10]
    commit_path = os.path.join(COMMITS_DIR, commit_id)
    parent = parents[0] if parents else leaf_get_head_commit_id(log)
    base_state = leaf_rebuild(parent, log) if parent else {}
    if target_state is None:
        target_state = _current_working_state()

    commit_data = {
        "id": commit_id,
        "message": msg,
        "time": timestamp,
        "branch": branch if branch is not None else get_head_module().read_current_branch(VCS_DIR),
        "parent": parent,
        "parents": parents or ([parent] if parent else []),
        "type": "diff",
        "changes": {},
        "deleted": [],
    }
    if not log:
        commit_data["type"] = "snapshot"
        commit_data["files"] = sorted(target_state)
    else:
        changes, deleted = _diff_states(base_state, target_state)
        commit_data["changes"] = changes
        commit_data["deleted"] = deleted
        if not changes and not deleted and not merge:
            print(f"{DRY} No changes detected, nothing to save")
            return None

    _write_commit_files(commit_path, commit_data, target_state)
    log.append(commit_data)
    safe_save_log(log)

    branches = load_branches()
    active_branch = get_head_module().read_current_branch(VCS_DIR)
    if active_branch:
        branches[active_branch] = commit_id
        save_branches(branches)
        sessions = load_sessions()
        sessions.pop(active_branch, None)
        save_sessions(sessions)
    get_head_module().write_head(VCS_DIR, commit_id)
    clear_index()
    return commit_id


def _apply_index_to_state(base_state, index):
    state = {path: list(lines) for path, lines in base_state.items()}
    for path, entry in index.items():
        if entry.get("deleted"):
            state.pop(path, None)
        else:
            state[path] = entry.get("content", [])
    return state


def leaf_save(msg):
    if not os.path.exists(VCS_DIR):
        print(f"{DRY} Not a repository")
        return
    msg = msg or "save"
    merge_state = load_merge_state()
    index = load_index()
    parents = None
    merge = False
    target_state = None
    if merge_state:
        conflicts = merge_state.get("conflicts", [])
        unresolved = [path for path in conflicts if _file_has_conflict_markers(path)]
        if unresolved:
            print(f"{DRY} Resolve conflicts before saving merge: {', '.join(unresolved)}")
            return
        parents = [merge_state.get("target"), merge_state.get("source")]
        merge = True
        target_state = _current_working_state()
    elif index:
        head_id = leaf_get_head_commit_id()
        base_state = leaf_rebuild(head_id, safe_load_log()) if head_id else {}
        target_state = _apply_index_to_state(base_state, index)

    commit_id = _create_commit(msg, target_state=target_state, parents=parents, merge=merge)
    if commit_id:
        if merge:
            clear_merge_state()
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
    tags_by_commit = {}
    for tag, cid in load_tags().items():
        tags_by_commit.setdefault(cid, []).append(tag)
    for commit_id in commit_chain(head_id, cmap):
        c = cmap[commit_id]
        marker = " (HEAD)" if c["id"] == head_id else ""
        tags = f" tags: {', '.join(sorted(tags_by_commit.get(commit_id, [])))}" if tags_by_commit.get(commit_id) else ""
        parents = c.get("parents") or ([c.get("parent")] if c.get("parent") else [])
        print(f"\n{HERB} commit {c['id']}{marker}{tags}")
        if len(parents) > 1:
            print(f"{TREE} Merge parents: {' '.join(parents)}")
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
    current = _current_working_state()
    any_diff = False
    for f in sorted(set(target.keys()) | set(current.keys())):
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
    write_working_tree(files)
    get_head_module().write_head(VCS_DIR, commit_id)
    get_head_module().write_current_branch(VCS_DIR, "")
    clear_index()
    clear_merge_state()
    print(f"{TREE} Restored to commit {commit_id} (detached HEAD)")


def leaf_status():
    if not os.path.exists(LOG_FILE):
        print(f"{DRY} No repository")
        return
    merge_state = load_merge_state()
    if merge_state:
        print(f"{TREE} Merge in progress from {merge_state.get('source_branch')} into {merge_state.get('current_branch')}")
        for f in merge_state.get("conflicts", []):
            print(f"{RED}{DRY} Conflict: {f}{RESET}")
    index = load_index()
    for path, entry in sorted(index.items()):
        status = "Deleted" if entry.get("deleted") else "Staged"
        print(f"{GREEN}{SPROUT} {status}: {path}{RESET}")
    last = leaf_get_last_state()
    current = set(leaf_get_all_files())
    last_files = set(last.keys())
    added, deleted, modified = current - last_files, last_files - current, []
    for f in current & last_files:
        if not is_binary(f) and leaf_read_file(f) != last[f]:
            modified.append(f)
    if not added and not deleted and not modified and not index and not merge_state:
        print(f"{HERB} Clean working tree")
        return
    for f in sorted(added):
        print(f"{GRAY}{SPROUT} Added: {f}{RESET}")
    for f in sorted(modified):
        print(f"{BLUE}{LEAF} Modified: {f}{RESET}")
    for f in sorted(deleted):
        print(f"{RED}{DRY} Deleted: {f}{RESET}")


def leaf_version():
    for url in ["https://raw.githubusercontent.com/WorkofAditya/Leaf/refs/heads/main/version.txt", "https://raw.githubusercontent.com/WorkofAditya/Leaf/main/version.txt"]:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                text = response.read().decode("utf-8").strip()
                if text:
                    print(text)
                    return
        except Exception:
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


def leaf_branch(name=None, commit_id=None):
    branches = load_branches()
    current = get_head_module().read_current_branch(VCS_DIR)
    if name is None:
        for b in sorted(branches.keys()):
            print(f"{'*' if b == current else ' '} {b}")
        return
    if name in branches:
        print(f"{DRY} Branch already exists: {name}")
        return
    if commit_id and commit_id not in [c["id"] for c in safe_load_log()]:
        print(f"{DRY} Invalid commit id")
        return
    branches[name] = commit_id or leaf_get_head_commit_id()
    save_branches(branches)
    print(f"{SPROUT} Created branch {name}")


def _capture_working_state():
    return _current_working_state()


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
    else:
        sessions.pop(branch, None)
    save_sessions(sessions)


def _restore_branch_session(branch, fallback_state):
    sessions = load_sessions()
    write_working_tree(sessions.get(branch, fallback_state) or {})


def leaf_checkout(branch_name):
    branches = load_branches()
    if branch_name not in branches:
        print(f"{DRY} Unknown branch: {branch_name}")
        return
    if load_merge_state():
        print(f"{DRY} Cannot checkout during merge; use 'leaf merge --abort' first")
        return
    current_branch = get_head_module().read_current_branch(VCS_DIR)
    if current_branch:
        _save_branch_session(current_branch)
    target = branches[branch_name]
    files = leaf_rebuild(target, safe_load_log()) if target else {}
    _restore_branch_session(branch_name, files)
    get_head_module().write_head(VCS_DIR, target or "")
    get_head_module().write_current_branch(VCS_DIR, branch_name)
    clear_index()
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
    print(f"{DRY} Branch '{branch}' has unresolved session changes; checkout and save/discard them first")
    return False


def _working_tree_clean_for(commit_id, log):
    expected = leaf_rebuild(commit_id, log) if commit_id else {}
    return not _has_uncommitted_changes(_current_working_state(), expected)


def _file_has_conflict_markers(path):
    if not os.path.exists(path):
        return False
    text = "".join(leaf_read_file(path))
    return "<<<<<<<" in text or "=======" in text or ">>>>>>>" in text


def _merge_file(path, base, current, source):
    if current == source:
        return current, False
    if current == base:
        return source, False
    if source == base:
        return current, False
    result = [
        "<<<<<<< current\n",
        *current,
        "=======\n",
        *source,
        ">>>>>>> source\n",
    ]
    return result, True


def _three_way_merge(base_state, current_state, source_state):
    merged = {}
    conflicts = []
    for path in sorted(set(base_state) | set(current_state) | set(source_state)):
        base = base_state.get(path)
        current = current_state.get(path)
        source = source_state.get(path)
        if current is None and source is None:
            continue
        if current is None:
            if source == base:
                continue
            if base is None:
                merged[path] = source
            else:
                content, conflict = _merge_file(path, base or [], [], source or [])
                merged[path] = content
                if conflict:
                    conflicts.append(path)
            continue
        if source is None:
            if current == base:
                continue
            content, conflict = _merge_file(path, base or [], current or [], [])
            merged[path] = content
            if conflict:
                conflicts.append(path)
            continue
        content, conflict = _merge_file(path, base or [], current or [], source or [])
        merged[path] = content
        if conflict:
            conflicts.append(path)
    return merged, conflicts


def leaf_merge(source_branch):
    if source_branch == "--continue":
        leaf_merge_continue()
        return
    if source_branch == "--abort":
        leaf_merge_abort()
        return
    branches = load_branches()
    current_branch = get_head_module().read_current_branch(VCS_DIR)
    if source_branch not in branches:
        print(f"{DRY} Unknown branch: {source_branch}")
        return
    if not current_branch:
        print(f"{DRY} Merge requires being on a branch")
        return
    if source_branch == current_branch:
        print(f"{HERB} Already on {source_branch}")
        return
    if load_merge_state():
        print(f"{DRY} Merge already in progress")
        return
    if load_index():
        print(f"{DRY} Commit or reset staged changes before merging")
        return
    if not _resolve_session_before_sensitive(source_branch):
        return
    log = safe_load_log()
    cmap = commit_map(log)
    target, source = branches.get(current_branch), branches.get(source_branch)
    if not source or target == source or is_ancestor(source, target, cmap):
        print(f"{HERB} Already up to date")
        return
    if not _working_tree_clean_for(target, log):
        print(f"{DRY} Working tree has uncommitted changes; save, reset, or checkout before merging")
        return
    if is_ancestor(target, source, cmap):
        write_working_tree(leaf_rebuild(source, log) or {})
        branches[current_branch] = source
        save_branches(branches)
        get_head_module().write_head(VCS_DIR, source)
        print(f"{TREE} Fast-forward merged {source_branch} into {current_branch}")
        return
    base = find_merge_base(target, source, cmap)
    if not base:
        print(f"{DRY} No merge base found")
        return
    merged, conflicts = _three_way_merge(leaf_rebuild(base, log), leaf_rebuild(target, log), leaf_rebuild(source, log))
    write_working_tree(merged)
    state = {
        "current_branch": current_branch,
        "source_branch": source_branch,
        "base": base,
        "target": target,
        "source": source,
        "conflicts": conflicts,
    }
    save_merge_state(state)
    if conflicts:
        print(f"{DRY} Merge has conflicts: {', '.join(conflicts)}")
        print(f"{HERB} Resolve conflicts, then run 'leaf merge --continue' or 'leaf save <message>'")
        return
    commit_id = _create_commit(f"Merge branch '{source_branch}' into {current_branch}", target_state=merged, parents=[target, source], merge=True)
    clear_merge_state()
    print(f"{TREE} Merged {source_branch} into {current_branch} with commit {commit_id}")


def leaf_merge_continue():
    state = load_merge_state()
    if not state:
        print(f"{DRY} No merge in progress")
        return
    unresolved = [path for path in state.get("conflicts", []) if _file_has_conflict_markers(path)]
    if unresolved:
        print(f"{DRY} Resolve conflicts first: {', '.join(unresolved)}")
        return
    commit_id = _create_commit(
        f"Merge branch '{state.get('source_branch')}' into {state.get('current_branch')}",
        target_state=_current_working_state(),
        parents=[state.get("target"), state.get("source")],
        merge=True,
    )
    clear_merge_state()
    print(f"{TREE} Merge completed with commit {commit_id}")


def leaf_merge_abort():
    state = load_merge_state()
    if not state:
        print(f"{DRY} No merge in progress")
        return
    write_working_tree(leaf_rebuild(state.get("target"), safe_load_log()) or {})
    clear_merge_state()
    print(f"{TREE} Merge aborted")


def leaf_add(path):
    if not path:
        print(f"{DRY} Missing path")
        return
    index = load_index()
    paths = leaf_get_all_files() if path == "." else [path]
    added = 0
    for item in paths:
        if os.path.exists(item) and not is_binary(item):
            index[item] = {"deleted": False, "content": leaf_read_file(item)}
            added += 1
        elif not os.path.exists(item):
            index[item] = {"deleted": True, "content": []}
            added += 1
    save_index(index)
    print(f"{SPROUT} Staged {added} path(s)")


def leaf_reset(arg=None, commit_id=None):
    if arg in {"--hard", "--soft"}:
        target = commit_id or leaf_get_head_commit_id()
        if target not in [c["id"] for c in safe_load_log()]:
            print(f"{DRY} Invalid commit id")
            return
        branches = load_branches()
        branch = get_head_module().read_current_branch(VCS_DIR)
        if branch:
            branches[branch] = target
            save_branches(branches)
        get_head_module().write_head(VCS_DIR, target)
        clear_index()
        clear_merge_state()
        if arg == "--hard":
            write_working_tree(leaf_rebuild(target, safe_load_log()))
        print(f"{TREE} Reset {arg} to {target}")
        return
    if arg:
        index = load_index()
        if arg in index:
            index.pop(arg)
            save_index(index)
            print(f"{DRY} Unstaged {arg}")
        else:
            print(f"{HERB} Nothing staged for {arg}")
        return
    clear_index()
    print(f"{DRY} Cleared staging area")


def leaf_revert(commit_id):
    log = safe_load_log()
    cmap = commit_map(log)
    if commit_id not in cmap:
        print(f"{DRY} Invalid commit id")
        return
    head_id = leaf_get_head_commit_id(log)
    if not _working_tree_clean_for(head_id, log):
        print(f"{DRY} Working tree has uncommitted changes")
        return
    commit = cmap[commit_id]
    parent = commit.get("parent")
    before = leaf_rebuild(parent, log) if parent else {}
    after = leaf_rebuild(commit_id, log)
    current = leaf_rebuild(head_id, log) if head_id else {}
    for path in set(before) | set(after):
        if before.get(path) == after.get(path):
            continue
        if path in before:
            current[path] = before[path]
        else:
            current.pop(path, None)
    write_working_tree(current)
    new_id = _create_commit(f"Revert {commit_id}", target_state=current)
    print(f"{TREE} Reverted {commit_id} with commit {new_id}")


def leaf_tag(name=None, commit_id=None):
    tags = load_tags()
    if name is None:
        for tag, cid in sorted(tags.items()):
            print(f"{tag} {cid}")
        return
    target = commit_id or leaf_get_head_commit_id()
    if target not in [c["id"] for c in safe_load_log()]:
        print(f"{DRY} Invalid commit id")
        return
    tags[name] = target
    save_tags(tags)
    print(f"{SPROUT} Tagged {target} as {name}")


def leaf_fsck():
    ok = True
    log = safe_load_log()
    ids = {c["id"] for c in log}
    for c in log:
        if not os.path.isdir(os.path.join(COMMITS_DIR, c["id"])):
            print(f"{RED}Missing commit directory: {c['id']}{RESET}")
            ok = False
        for parent in c.get("parents") or ([c.get("parent")] if c.get("parent") else []):
            if parent and parent not in ids:
                print(f"{RED}Missing parent {parent} for {c['id']}{RESET}")
                ok = False
    for branch, cid in load_branches().items():
        if cid and cid not in ids:
            print(f"{RED}Branch {branch} points to missing commit {cid}{RESET}")
            ok = False
    for tag, cid in load_tags().items():
        if cid and cid not in ids:
            print(f"{RED}Tag {tag} points to missing commit {cid}{RESET}")
            ok = False
    print(f"{TREE} Repository integrity OK" if ok else f"{DRY} Repository integrity issues found")


def _repo_leaf_dir(path):
    return os.path.join(path, ".leaf") if not path.endswith(".leaf") else path


# Remote repository command implementations are intentionally disabled.
# The original code remains below as comments for future review/restoration, but
# these commands are not executed by the CLI.
# def leaf_remote(args):
#     remotes = load_remotes()
#     if not args:
#         for name, path in sorted(remotes.items()):
#             print(f"{name} {path}")
#         return
#     if args[0] == "add" and len(args) >= 3:
#         remotes[args[1]] = os.path.abspath(args[2])
#         save_remotes(remotes)
#         print(f"{SPROUT} Added remote {args[1]}")
#         return
#     print(f"{DRY} Usage: leaf remote [add <name> <path>]")
#
#
# def _copy_commit_objects(src_leaf, dst_leaf):
#     src_commits = os.path.join(src_leaf, "commits")
#     dst_commits = os.path.join(dst_leaf, "commits")
#     os.makedirs(dst_commits, exist_ok=True)
#     if not os.path.isdir(src_commits):
#         return
#     for cid in os.listdir(src_commits):
#         src = os.path.join(src_commits, cid)
#         dst = os.path.join(dst_commits, cid)
#         if os.path.isdir(src) and not os.path.exists(dst):
#             shutil.copytree(src, dst)
#
#
# def leaf_fetch(remote_name):
#     remotes = load_remotes()
#     if remote_name not in remotes:
#         print(f"{DRY} Unknown remote: {remote_name}")
#         return
#     remote_leaf = _repo_leaf_dir(remotes[remote_name])
#     if not os.path.isdir(remote_leaf):
#         print(f"{DRY} Remote is not a Leaf repository")
#         return
#     from Modules.storage import _load_json
#     remote_log = _load_json(os.path.join(remote_leaf, "log.json"), [])
#     local_log = safe_load_log()
#     local_ids = {c["id"] for c in local_log}
#     local_log.extend([c for c in remote_log if c["id"] not in local_ids])
#     safe_save_log(local_log)
#     _copy_commit_objects(remote_leaf, VCS_DIR)
#     remote_branches = _load_json(os.path.join(remote_leaf, "branches.json"), {})
#     branches = load_branches()
#     for branch, cid in remote_branches.items():
#         branches[f"{remote_name}/{branch}"] = cid
#     save_branches(branches)
#     print(f"{TREE} Fetched {remote_name}")
#
#
# def leaf_push(remote_name, branch_name):
#     remotes = load_remotes()
#     if remote_name not in remotes:
#         print(f"{DRY} Unknown remote: {remote_name}")
#         return
#     remote_path = remotes[remote_name]
#     remote_leaf = _repo_leaf_dir(remote_path)
#     os.makedirs(remote_leaf, exist_ok=True)
#     _copy_commit_objects(VCS_DIR, remote_leaf)
#     from Modules.storage import _atomic_json_save, _load_json
#     remote_log = _load_json(os.path.join(remote_leaf, "log.json"), [])
#     remote_ids = {c["id"] for c in remote_log}
#     remote_log.extend([c for c in safe_load_log() if c["id"] not in remote_ids])
#     _atomic_json_save(os.path.join(remote_leaf, "log.json"), remote_log)
#     remote_branches = _load_json(os.path.join(remote_leaf, "branches.json"), {"main": None})
#     branches = load_branches()
#     if branch_name not in branches:
#         print(f"{DRY} Unknown branch: {branch_name}")
#         return
#     remote_branches[branch_name] = branches[branch_name]
#     _atomic_json_save(os.path.join(remote_leaf, "branches.json"), remote_branches)
#     print(f"{TREE} Pushed {branch_name} to {remote_name}")
#
#
# def leaf_pull(remote_name, branch_name):
#     leaf_fetch(remote_name)
#     leaf_merge(f"{remote_name}/{branch_name}")
#

def leaf_clone(source, dest=None):
    dest = dest or os.path.basename(os.path.abspath(source.rstrip(os.sep))) + "-clone"
    remote_leaf = _repo_leaf_dir(source)
    if not os.path.isdir(remote_leaf):
        print(f"{DRY} Source is not a Leaf repository")
        return
    os.makedirs(dest, exist_ok=True)
    shutil.copytree(remote_leaf, os.path.join(dest, ".leaf"), dirs_exist_ok=True)
    old = os.getcwd()
    os.chdir(dest)
    try:
        from Modules.storage import _load_json
        branches = _load_json(os.path.join(".leaf", "branches.json"), {"main": None})
        target = branches.get("main") or next((cid for cid in branches.values() if cid), None)
        write_working_tree(leaf_rebuild(target, safe_load_log()) if target else {})
        get_head_module().init_head(VCS_DIR)
        get_head_module().write_head(VCS_DIR, target or "")
        get_head_module().write_current_branch(VCS_DIR, "main" if "main" in branches else "")
    finally:
        os.chdir(old)
    print(f"{TREE} Cloned {source} into {dest}")
