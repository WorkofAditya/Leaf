#!/usr/bin/env python3
import os, sys, json, time, hashlib, difflib

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

def read_file(path):
    try:
        with open(path, "r", errors="ignore") as f:
            return f.readlines()
    except:
        return []

def get_all_files():
    files = []
    for root, dirs, fs in os.walk("."):
        if VCS_DIR in root:
            continue
        for f in fs:
            files.append(os.path.relpath(os.path.join(root, f), "."))
    return files

def save(msg):
    if not os.path.exists(VCS_DIR):
        print("Not a repository")
        return

    with open(LOG_FILE, "r") as f:
        log = json.load(f)

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    commit_id = hash_commit(msg + timestamp)[:10]
    commit_path = os.path.join(COMMITS_DIR, commit_id)
    os.makedirs(commit_path)

    prev_files = {}
    if log:
        last_commit = log[-1]["id"]
        last_path = os.path.join(COMMITS_DIR, last_commit)
        for root, dirs, fs in os.walk(last_path):
            for f in fs:
                rel = os.path.relpath(os.path.join(root, f), last_path)
                prev_files[rel] = read_file(os.path.join(root, f))

    current_files = get_all_files()
    commit_data = {
        "id": commit_id,
        "message": msg,
        "time": timestamp,
        "changes": {}
    }

    for file in current_files:
        new_content = read_file(file)
        old_content = prev_files.get(file, [])

        if new_content != old_content:
            diff = list(difflib.unified_diff(old_content, new_content, lineterm=""))
            commit_data["changes"][file] = diff

            save_path = os.path.join(commit_path, file + ".diff")
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "w") as f:
                f.write("\n".join(diff))

    with open(LOG_FILE, "w") as f:
        log.append(commit_data)
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
        print("Changed files:")
        for f_ in c["changes"]:
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

