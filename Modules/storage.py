import json
import os
import shutil
import tempfile

from Modules.common import (
    BRANCHES_FILE,
    INDEX_FILE,
    LOG_BACKUP,
    LOG_FILE,
    MERGE_STATE_FILE,
    REMOTES_FILE,
    SESSIONS_FILE,
    TAGS_FILE,
)


def _atomic_json_save(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path), suffix=".tmp", dir=os.path.dirname(path) or ".")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def _load_json(path, default):
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data if isinstance(data, type(default)) else default
    except (OSError, json.JSONDecodeError):
        return default


def safe_load_log():
    try:
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return _load_json(LOG_BACKUP, [])


def safe_save_log(log):
    if os.path.exists(LOG_FILE):
        shutil.copy2(LOG_FILE, LOG_BACKUP)
    _atomic_json_save(LOG_FILE, log)


def load_branches():
    return _load_json(BRANCHES_FILE, {"main": None})


def save_branches(branches):
    _atomic_json_save(BRANCHES_FILE, branches)


def load_sessions():
    return _load_json(SESSIONS_FILE, {})


def save_sessions(sessions):
    _atomic_json_save(SESSIONS_FILE, sessions)


def load_index():
    return _load_json(INDEX_FILE, {})


def save_index(index):
    _atomic_json_save(INDEX_FILE, index)


def clear_index():
    save_index({})


def load_tags():
    return _load_json(TAGS_FILE, {})


def save_tags(tags):
    _atomic_json_save(TAGS_FILE, tags)


def load_merge_state():
    return _load_json(MERGE_STATE_FILE, {})


def save_merge_state(state):
    _atomic_json_save(MERGE_STATE_FILE, state)


def clear_merge_state():
    try:
        os.remove(MERGE_STATE_FILE)
    except FileNotFoundError:
        pass


def load_remotes():
    return _load_json(REMOTES_FILE, {})


def save_remotes(remotes):
    _atomic_json_save(REMOTES_FILE, remotes)
