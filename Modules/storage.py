import json
import os
import shutil

from Modules.common import BRANCHES_FILE, LOG_BACKUP, LOG_FILE


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
    if os.path.exists(LOG_FILE):
        shutil.copy2(LOG_FILE, LOG_BACKUP)
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


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
