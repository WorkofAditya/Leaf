"""Read-only repository inspection helpers shared by user interfaces.

These helpers deliberately build on Leaf's existing log, graph, and rebuild
implementation.  They do not write repository data or introduce a second
storage format.
"""

import difflib

from Modules.graph import commit_chain, commit_map, commit_parents
from Modules.rebuild import leaf_rebuild


def commit_snapshot(commit_id, log):
    """Return Leaf's reconstructed text-file snapshot for ``commit_id``."""
    return leaf_rebuild(commit_id, log) if commit_id else {}


def first_parent_id(commit, log):
    """Return the parent used by Leaf's deterministic rebuild semantics."""
    parents = commit_parents(commit)
    return parents[0] if parents else None


def commit_file_changes(commit_id, log):
    """Describe files changed by a commit relative to its first parent.

    Each result contains a repository path and an ``A``, ``M``, or ``D``
    status.  Comparing reconstructed states also supports legacy commits and
    snapshot commits without having to duplicate commit-format parsing.
    """
    commits = commit_map(log)
    commit = commits.get(commit_id)
    if not commit:
        return []
    before = commit_snapshot(first_parent_id(commit, log), log)
    after = commit_snapshot(commit_id, log)
    changes = []
    for path in sorted(set(before) | set(after)):
        if path not in before:
            status = "A"
        elif path not in after:
            status = "D"
        elif before[path] != after[path]:
            status = "M"
        else:
            continue
        changes.append({"path": path, "status": status})
    return changes


def file_history(path, head_id, log):
    """Return only reachable commits that changed ``path``, newest first."""
    return [
        commit_id
        for commit_id in commit_chain(head_id, commit_map(log))
        if any(change["path"] == path for change in commit_file_changes(commit_id, log))
    ]


def file_diff(commit_id, path, log, context=3):
    """Return a unified diff for one changed file in a commit.

    ``/dev/null`` headers make added and deleted files unambiguous, while the
    returned status allows callers to label the UI without parsing diff text.
    """
    commits = commit_map(log)
    commit = commits.get(commit_id)
    if not commit:
        return {"status": None, "before": [], "after": [], "lines": []}
    before = commit_snapshot(first_parent_id(commit, log), log)
    after = commit_snapshot(commit_id, log)
    if path not in before and path not in after:
        return {"status": None, "before": [], "after": [], "lines": []}
    status = "A" if path not in before else "D" if path not in after else "M"
    old = before.get(path, [])
    new = after.get(path, [])
    return {
        "status": status,
        "before": old,
        "after": new,
        "lines": list(
            difflib.unified_diff(
                old,
                new,
                fromfile="/dev/null" if status == "A" else path,
                tofile="/dev/null" if status == "D" else path,
                n=context,
                lineterm="",
            )
        ),
    }
