def commit_map(log):
    return {c["id"]: c for c in log}


def commit_chain(commit_id, cmap):
    chain = []
    seen = set()
    current = commit_id
    while current and current in cmap and current not in seen:
        chain.append(current)
        seen.add(current)
        current = cmap[current].get("parent")
    return chain


def is_ancestor(ancestor_id, commit_id, cmap):
    if not ancestor_id:
        return True
    return ancestor_id in set(commit_chain(commit_id, cmap))
