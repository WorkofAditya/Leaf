def commit_map(log):
    return {c["id"]: c for c in log}


def commit_parents(commit):
    parents = commit.get("parents")
    if isinstance(parents, list):
        return [p for p in parents if p]
    parent = commit.get("parent")
    return [parent] if parent else []


def commit_chain(commit_id, cmap):
    chain = []
    seen = set()
    stack = [commit_id] if commit_id else []
    while stack:
        current = stack.pop(0)
        if not current or current not in cmap or current in seen:
            continue
        chain.append(current)
        seen.add(current)
        stack.extend(commit_parents(cmap[current]))
    return chain


def first_parent_chain(commit_id, cmap):
    chain = []
    seen = set()
    current = commit_id
    while current and current in cmap and current not in seen:
        chain.append(current)
        seen.add(current)
        parents = commit_parents(cmap[current])
        current = parents[0] if parents else None
    return chain


def is_ancestor(ancestor_id, commit_id, cmap):
    if not ancestor_id:
        return True
    return ancestor_id in set(commit_chain(commit_id, cmap))


def find_merge_base(left_id, right_id, cmap):
    if not left_id or not right_id:
        return None
    left_ancestors = set(commit_chain(left_id, cmap))
    for candidate in commit_chain(right_id, cmap):
        if candidate in left_ancestors:
            return candidate
    return None
