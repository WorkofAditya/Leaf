import os
import shutil


def is_binary(path):
    try:
        with open(path, "rb") as f:
            chunk = f.read(1024)
            if b"\0" in chunk:
                return True
    except:
        return True
    return False


def leaf_read_file(path):
    try:
        with open(path, "r", errors="ignore") as f:
            return f.readlines()
    except:
        return []


def leaf_write_file(path, lines):
    dirpath = os.path.dirname(path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    with open(path, "w") as f:
        f.writelines(lines)


def load_ignore():
    ignore = {".leaf", ".git", ".github", ".gitlab", "__pycache__", "*.pyc"}

    if os.path.exists(".leafignore"):
        try:
            with open(".leafignore", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        ignore.add(line)
        except:
            pass

    return ignore


def leaf_get_all_files():
    ignore = load_ignore()
    files = []

    for root, dirs, fs in os.walk("."):
        dirs[:] = [d for d in dirs if d not in ignore]

        for f in fs:
            path = os.path.relpath(os.path.join(root, f), ".")
            ignored = False

            for ig in ignore:
                if ig.startswith("*.") and f.endswith(ig[1:]):
                    ignored = True
                    break
                if ig in path.split(os.sep):
                    ignored = True
                    break

            if not ignored:
                files.append(path)

    return files


def leaf_snapshot(commit_path):
    for file in leaf_get_all_files():
        dest = os.path.join(commit_path, file)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(file, dest)
