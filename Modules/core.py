import hashlib

from Modules.head_utils import get_head_module
from Modules.storage import load_branches, safe_load_log
from Modules.common import VCS_DIR
def leaf_hash_commit(data):
    return hashlib.sha1(data.encode()).hexdigest()


def leaf_get_head_commit_id(log=None):
    if log is None:
        log = safe_load_log()
    if not log:
        return None
    head_id = get_head_module().read_head(VCS_DIR)
    if head_id:
        return head_id
    branch = get_head_module().read_current_branch(VCS_DIR)
    if branch:
        return load_branches().get(branch)
    return None


def leaf_get_last_state():
    log = safe_load_log()
    if not log:
        return {}
    head_id = leaf_get_head_commit_id(log)
    if not head_id:
        return {}
    from Modules.rebuild import leaf_rebuild
    return leaf_rebuild(head_id, log) or {}
