"""GUI-facing, read-only adapter for the existing Leaf repository engine."""

import contextlib
import os
from pathlib import Path


@contextlib.contextmanager
def repository_context(path):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


class RepositoryService:
    def __init__(self, repository):
        self.repository = Path(repository).resolve()

    def _read(self, callback):
        with repository_context(self.repository):
            return callback()

    def log(self):
        from Modules.storage import safe_load_log
        return self._read(safe_load_log)

    def head_id(self, log=None):
        from Modules.core import leaf_get_head_commit_id
        return self._read(lambda: leaf_get_head_commit_id(log))

    def branches(self):
        from Modules.storage import load_branches
        return self._read(load_branches)

    def tags(self):
        from Modules.storage import load_tags
        return self._read(load_tags)

    def current_branch(self):
        from Modules.common import VCS_DIR
        from Modules.head_utils import get_head_module
        return self._read(lambda: get_head_module().read_current_branch(VCS_DIR) or "detached")

    def fingerprint(self):
        """Cheap metadata fingerprint used to avoid unnecessary UI rerenders."""
        paths = [".leaf/log.json", ".leaf/branches.json", ".leaf/tags.json", ".leaf/index.json"]
        result = []
        for relative in paths:
            path = self.repository / relative
            try:
                stat = path.stat()
                result.append((relative, stat.st_mtime_ns, stat.st_size))
            except OSError:
                result.append((relative, None, None))
        return tuple(result)

    def list_directory(self, relative=""):
        directory = (self.repository / relative).resolve()
        if self.repository not in (directory, *directory.parents) or not directory.is_dir():
            return []
        entries = []
        for entry in directory.iterdir():
            if entry.name == ".leaf":
                continue
            try:
                stat = entry.stat()
            except OSError:
                continue
            entries.append({
                "name": entry.name,
                "path": entry.relative_to(self.repository).as_posix(),
                "is_dir": entry.is_dir(),
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })
        return sorted(entries, key=lambda item: (not item["is_dir"], item["name"].casefold()))

    def read_working_file(self, relative):
        path = (self.repository / relative).resolve()
        if self.repository not in (path, *path.parents) or not path.is_file():
            raise OSError("File is outside the repository")
        raw = path.read_bytes()
        binary = b"\0" in raw[:8192]
        if binary:
            return {"binary": True, "text": "", "size": len(raw)}
        return {"binary": False, "text": raw.decode("utf-8", errors="replace"), "size": len(raw)}

    def working_tree_status(self):
        def read_status():
            from Modules.common import LOG_FILE
            from Modules.core import leaf_get_last_state
            from Modules.files import is_binary, is_ignored_path, leaf_get_all_files, leaf_read_file
            from Modules.storage import load_index, load_merge_state
            if not os.path.exists(LOG_FILE):
                return {"staged": {}, "added": [], "modified": [], "deleted": [], "conflicts": []}
            index = load_index()
            staged = {os.path.normpath(path) for path in index}
            last = {os.path.normpath(path): content for path, content in leaf_get_last_state().items() if not is_ignored_path(path)}
            current = {os.path.normpath(path) for path in leaf_get_all_files()}
            return {
                "staged": index,
                "added": sorted((current - set(last)) - staged),
                "deleted": sorted((set(last) - current) - staged),
                "modified": sorted(path for path in (current & set(last)) - staged if not is_binary(path) and leaf_read_file(path) != last[path]),
                "conflicts": sorted(load_merge_state().get("conflicts", [])) if load_merge_state() else [],
            }
        return self._read(read_status)

    def commit_changes(self, commit_id, log=None):
        from Modules.inspection import commit_file_changes
        log = self.log() if log is None else log
        return self._read(lambda: commit_file_changes(commit_id, log))

    def file_history(self, path, log=None, head_id=None):
        from Modules.inspection import file_history
        log = self.log() if log is None else log
        head_id = self.head_id(log) if head_id is None else head_id
        return self._read(lambda: file_history(path, head_id, log))

    def file_diff(self, commit_id, path, log=None):
        from Modules.inspection import file_diff
        log = self.log() if log is None else log
        return self._read(lambda: file_diff(commit_id, path, log))
