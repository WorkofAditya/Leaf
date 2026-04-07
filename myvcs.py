#!/usr/bin/env python3
import os, sys, json, time, hashlib, shutil

VCS_DIR = ".myvcs"
COMMITS_DIR = os.path.join(VCS_DIR, "commits")
LOG_FILE = os.path.join(VCS_DIR, "log.json")

def init():
    os.makedirs(COMMITS_DIR, exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump([], f)
    print("Initialized empty repository")

def hash_commit(data):
    return hashlib.sha1(data.encode()).hexdigest()

def snapshot_files(dest):
    for root, dirs, files in os.walk("."):
        if VCS_DIR in root:
            continue
        for file in files:
            path = os.path.join(root, file)
            rel = os.path.relpath(path, ".")
            target = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(path, target)

def save(msg):
    if not os.path.exists(VCS_DIR):
        print("Not a repository")
        return

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    raw = msg + timestamp
    commit_id = hash_commit(raw)[:10]

    commit_path = os.path.join(COMMITS_DIR, commit_id)
    os.makedirs(commit_path)

    snapshot_files(commit_path)

    with open(LOG_FILE, "r") as f:
        log = json.load(f)

    commit_data = {
        "id": commit_id,
        "message": msg,
        "time": timestamp,
        "files": []
    }

    for root, dirs, files in os.walk(commit_path):
        for file in files:
            rel = os.path.relpath(os.path.join(root, file), commit_path)
            commit_data["files"].append(rel)

    log.append(commit_data)

    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

    print(f"Saved commit {commit_id}")

def log():
    if not os.path.exists(LOG_FILE):
        print("No commits")
        return

    with open(LOG_FILE, "r") as f:
        log = json.load(f)

    for c in reversed(log):
        print(f"\nCommit: {c['id']}")
        print(f"Message: {c['message']}")
        print(f"Time: {c['time']}")
        print("Files:")
        for f_ in c["files"]:
            print(f"  {f_}")

def main():
    if len(sys.argv) < 2:
        return

    cmd = sys.argv[1]

    if cmd == "init":
        init()
    elif cmd == "save":
        msg = " ".join(sys.argv[2:])
        save(msg)
    elif cmd == "log":
        log()

if __name__ == "__main__":
    main()
