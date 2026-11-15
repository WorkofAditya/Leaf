import codecs
import os


def is_binary(path):
    decoder = codecs.getincrementaldecoder("utf-8")()

    try:
        with open(path, "rb") as stream:
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    break
                if b"\0" in chunk:
                    return True
                decoder.decode(chunk)

        decoder.decode(b"", final=True)
    except (OSError, UnicodeDecodeError):
        return True

    return False


def leaf_read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as stream:
            return stream.readlines()
    except (OSError, UnicodeDecodeError):
        return []


def leaf_write_file(path, lines):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(path, "w", encoding="utf-8") as stream:
        stream.writelines(lines)


def load_ignore():
    ignore = {".leaf", ".git", "__pycache__", "*.pyc"}

    if os.path.exists(".leafignore"):
        try:
            with open(".leafignore", "r", encoding="utf-8") as stream:
                for line in stream:
                    pattern = line.strip()
                    if pattern and not pattern.startswith("#"):
                        ignore.add(pattern)
        except OSError:
            pass

    return ignore


def is_ignored_path(path, ignore=None):
    if ignore is None:
        ignore = load_ignore()

    normalized = os.path.normpath(path).replace("/", os.sep)
    parts = normalized.split(os.sep)
    name = os.path.basename(normalized)

    for pattern in ignore:
        if pattern.startswith("*.") and name.endswith(pattern[1:]):
            return True
        if pattern in parts:
            return True

    return False


def leaf_get_all_files():
    ignore = load_ignore()
    files = []

    for root, dirs, names in os.walk("."):
        dirs[:] = sorted(
            name
            for name in dirs
            if not is_ignored_path(os.path.join(root, name), ignore)
        )

        for name in names:
            path = os.path.relpath(os.path.join(root, name), ".")
            if not is_ignored_path(path, ignore):
                files.append(path)

    return sorted(files)


def leaf_snapshot(commit_path, state):
    for path, lines in state.items():
        destination = os.path.join(commit_path, path)
        leaf_write_file(destination, lines)
