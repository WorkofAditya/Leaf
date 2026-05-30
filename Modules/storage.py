import json
import os
import shutil
import tempfile

from Modules.common import BRANCHES_FILE, LOG_BACKUP, LOG_FILE, SESSIONS_FILE


def safe_load_log():
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except:
        if os.path.exists(LOG_BACKUP):
            with open(LOG_BACKUP, "r") as f:
                return json.load(f)
        return []


def safe_save_log(log):
    log_dir = os.path.dirname(LOG_FILE) or "."
    os.makedirs(log_dir, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix="log.", suffix=".tmp", dir=log_dir, text=True)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(log, f, indent=2)
            f.write("\n")
        os.replace(temp_path, LOG_FILE)
        shutil.copy2(LOG_FILE, LOG_BACKUP)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def load_branches():
    try:
        with open(BRANCHES_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except:
        pass
    return {"main": None}


def save_branches(branches):
    with open(BRANCHES_FILE, "w") as f:
        json.dump(branches, f, indent=2)


def load_sessions():
    try:
        with open(SESSIONS_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except:
        pass
    return {}


def save_sessions(sessions):
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, indent=2)
