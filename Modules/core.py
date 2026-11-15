import hashlib

from Modules.common import VCS_DIR
from Modules.head_utils import get_head_module
from Modules.storage import load_branches, safe_load_log


def leaf_hash_commit(data):
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def leaf_get_head_commit_id(log=None):
    if log is None:
        log = safe_load_log()
    if not log:
        return None

    commit_ids = {commit.get("id") for commit in log}
    head = get_head_module()
    branch = head.read_current_branch(VCS_DIR)

    if branch:
        branch_head = load_branches().get(branch)
        return branch_head if branch_head in commit_ids else log[-1].get("id")

    commit_id = head.read_head(VCS_DIR)
    return commit_id if commit_id in commit_ids else log[-1].get("id")


def leaf_get_last_state():
    log = safe_load_log()
    if not log:
        return {}

    head_id = leaf_get_head_commit_id(log)
    if not head_id:
        return {}

    from Modules.rebuild import leaf_rebuild

    return leaf_rebuild(head_id, log)
