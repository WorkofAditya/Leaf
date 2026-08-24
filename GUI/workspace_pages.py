"""Stacked workspace pages used by :mod:`GUI.repository_window`."""

import contextlib
import io
import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
    QLineEdit, QPlainTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from GUI.repository_service import repository_context


def _format_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}"
        size /= 1024


def _format_time(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return value or "Unknown time"


class BrowserPage(QWidget):
    file_requested = Signal(str)

    def __init__(self, service):
        super().__init__()
        self.service, self.current_folder = service, ""
        layout = QVBoxLayout(self); layout.setContentsMargins(28, 28, 28, 28)
        header = QHBoxLayout()
        self.title = QLabel("Repository files"); self.title.setObjectName("pageTitle")
        self.up = QPushButton("↑ Parent"); self.up.clicked.connect(self.go_up)
        root = QPushButton("⌂ Root"); root.clicked.connect(lambda: self.open_folder(""))
        header.addWidget(self.title); header.addStretch(); header.addWidget(self.up); header.addWidget(root)
        layout.addLayout(header)
        self.breadcrumbs = QLabel(); self.breadcrumbs.setObjectName("muted"); layout.addWidget(self.breadcrumbs)
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Name", "Size", "Modified"])
        self.tree.itemActivated.connect(self.activate); layout.addWidget(self.tree, 1)
        self.refresh()

    def open_folder(self, relative):
        self.current_folder = relative.strip("/")
        self.refresh()

    def go_up(self):
        self.open_folder(str(Path(self.current_folder).parent) if self.current_folder else "")

    def refresh(self):
        selected = self.tree.currentItem().data(0, Qt.UserRole) if self.tree.currentItem() else None
        self.tree.clear(); self.up.setEnabled(bool(self.current_folder))
        self.breadcrumbs.setText("Repository root" if not self.current_folder else f"Repository root / {self.current_folder}")
        for entry in self.service.list_directory(self.current_folder):
            icon = "📁" if entry["is_dir"] else "📄"
            item = QTreeWidgetItem([f"{icon}  {entry['name']}", "—" if entry["is_dir"] else _format_size(entry["size"]), datetime.fromtimestamp(entry["modified"]).strftime("%Y-%m-%d %H:%M")])
            item.setData(0, Qt.UserRole, entry["path"]); item.setData(0, Qt.UserRole + 1, entry["is_dir"])
            self.tree.addTopLevelItem(item)
            if entry["path"] == selected: self.tree.setCurrentItem(item)
        self.tree.resizeColumnToContents(0)

    def activate(self, item, _column):
        path = item.data(0, Qt.UserRole)
        if item.data(0, Qt.UserRole + 1): self.open_folder(path)
        else: self.file_requested.emit(path)


class FileViewerPage(QWidget):
    back_requested = Signal()
    history_requested = Signal(str)

    def __init__(self, service):
        super().__init__(); self.service = service; self.path = None
        layout = QVBoxLayout(self); layout.setContentsMargins(28, 28, 28, 28)
        row = QHBoxLayout(); self.title = QLabel(); self.title.setObjectName("pageTitle")
        back = QPushButton("← Files"); back.clicked.connect(self.back_requested); self.history = QPushButton("History"); self.history.clicked.connect(lambda: self.history_requested.emit(self.path))
        row.addWidget(back); row.addWidget(self.title); row.addStretch(); row.addWidget(self.history); layout.addLayout(row)
        self.metadata = QLabel(); self.metadata.setObjectName("muted"); layout.addWidget(self.metadata)
        self.editor = QPlainTextEdit(); self.editor.setReadOnly(True); layout.addWidget(self.editor, 1)

    def show_file(self, path):
        self.path = path; self.title.setText(Path(path).name); data = self.service.read_working_file(path)
        self.metadata.setText(f"{path}  •  {_format_size(data['size'])}")
        self.editor.setPlainText("Binary file\n\nCannot display contents as text." if data["binary"] else data["text"])


class HistoryPage(QWidget):
    commit_requested = Signal(str)

    def __init__(self, service):
        super().__init__(); self.service = service; self.file_path = None
        layout = QVBoxLayout(self); layout.setContentsMargins(28, 28, 28, 28)
        self.title = QLabel("History"); self.title.setObjectName("pageTitle"); layout.addWidget(self.title)
        self.list = QListWidget(); self.list.setObjectName("historyList"); self.list.itemActivated.connect(lambda item: self.commit_requested.emit(item.data(Qt.UserRole)))
        layout.addWidget(self.list, 1)

    def show_history(self, path=None): self.file_path = path; self.refresh()

    def refresh(self):
        self.list.clear(); log = self.service.log(); head = self.service.head_id(log)
        ids = self.service.file_history(self.file_path, log, head) if self.file_path else []
        if not self.file_path:
            from Modules.graph import commit_chain, commit_map
            ids = commit_chain(head, commit_map(log))
        self.title.setText(f"{self.file_path} History" if self.file_path else "History")
        if not ids: self.list.addItem("No commits yet." if not self.file_path else "No commits changed this file."); return
        tags = self.service.tags(); branches = self.service.branches()
        for cid in ids:
            commit = next(item for item in log if item["id"] == cid)
            labels = [name for name, target in branches.items() if target == cid] + [name for name, target in tags.items() if target == cid]
            decoration = f"  [{', '.join(labels)}]" if labels else ""
            item = QListWidgetItem(f"● {cid[:7]}  {commit.get('message', 'No message')}{decoration}\n   {commit.get('branch') or 'detached'} · {_format_time(commit.get('time'))}")
            item.setData(Qt.UserRole, cid); self.list.addItem(item)


class CommitDetailPage(QWidget):
    back_requested = Signal()
    diff_requested = Signal(str, str)

    def __init__(self, service):
        super().__init__(); self.service = service; self.commit_id = None
        layout = QVBoxLayout(self); layout.setContentsMargins(28, 28, 28, 28)
        row = QHBoxLayout(); back = QPushButton("← Back"); back.clicked.connect(self.back_requested); self.title = QLabel(); self.title.setObjectName("pageTitle"); row.addWidget(back); row.addWidget(self.title); row.addStretch(); layout.addLayout(row)
        self.info = QLabel(); self.info.setObjectName("repositoryInfo"); layout.addWidget(self.info)
        self.list = QListWidget(); self.list.setObjectName("historyList"); self.list.itemActivated.connect(self.open_diff); layout.addWidget(self.list, 1)

    def show_commit(self, commit_id):
        self.commit_id = commit_id; log = self.service.log(); commit = next(c for c in log if c["id"] == commit_id)
        parents = commit.get("parents") or ([commit.get("parent")] if commit.get("parent") else [])
        changes = self.service.commit_changes(commit_id, log); self.title.setText(f"Commit {commit_id[:7]}")
        self.info.setText(f"{commit.get('message', 'No message')}\n\nParent: {', '.join(parents) or 'None'}\nBranch: {commit.get('branch') or 'detached'}\nTimestamp: {_format_time(commit.get('time'))}\nChanged files: {len(changes)}")
        self.list.clear()
        for change in changes:
            item = QListWidgetItem(f"{change['status']}  {change['path']}"); item.setData(Qt.UserRole, change["path"]); self.list.addItem(item)

    def open_diff(self, item): self.diff_requested.emit(self.commit_id, item.data(Qt.UserRole))


class DiffPage(QWidget):
    back_requested = Signal()

    def __init__(self, service):
        super().__init__(); self.service = service
        layout = QVBoxLayout(self); layout.setContentsMargins(28, 28, 28, 28)
        row = QHBoxLayout(); back = QPushButton("← Commit"); back.clicked.connect(self.back_requested); self.title = QLabel(); self.title.setObjectName("pageTitle"); row.addWidget(back); row.addWidget(self.title); row.addStretch(); layout.addLayout(row)
        self.info = QLabel(); self.info.setObjectName("muted"); layout.addWidget(self.info)
        self.editor = QPlainTextEdit(); self.editor.setReadOnly(True); layout.addWidget(self.editor, 1)

    def show_diff(self, commit_id, path):
        diff = self.service.file_diff(commit_id, path); self.title.setText(path)
        self.info.setText(f"Commit {commit_id[:7]}  •  {diff['status']}  •  {'/dev/null → ' + path if diff['status'] == 'A' else path + ' → /dev/null' if diff['status'] == 'D' else 'parent → selected commit'}")
        self.editor.setPlainText("\n".join(diff["lines"]) or "No textual difference available.")
        document = self.editor.document()
        for block in iter_blocks(document):
            text = block.text()
            color = "#6a9f6d" if text.startswith("+") and not text.startswith("+++") else "#b86b6b" if text.startswith("-") and not text.startswith("---") else None
            if color:
                cursor = QTextCursor(block); cursor.select(QTextCursor.LineUnderCursor); fmt = QTextCharFormat(); fmt.setBackground(QColor(color)); cursor.setCharFormat(fmt)


def iter_blocks(document):
    block = document.firstBlock()
    while block.isValid(): yield block; block = block.next()


class ChangesPage(QWidget):
    """Small staging frontend that continues to delegate mutations to Leaf."""
    changed = Signal()
    def __init__(self, service):
        super().__init__(); self.service = service; self.rows = []
        layout = QVBoxLayout(self); layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel("Changes"); title.setObjectName("pageTitle"); layout.addWidget(title)
        actions = QHBoxLayout(); stage = QPushButton("Stage selected"); stage.clicked.connect(lambda: self.stage(True)); unstage = QPushButton("Unstage selected"); unstage.clicked.connect(lambda: self.stage(False)); self.message = QLineEdit(); self.message.setPlaceholderText("Commit message"); save = QPushButton("Save staged changes"); save.clicked.connect(self.save); actions.addWidget(stage); actions.addWidget(unstage); actions.addWidget(self.message, 1); actions.addWidget(save); layout.addLayout(actions)
        self.list = QListWidget(); layout.addWidget(self.list, 1); self.refresh()
    def refresh(self):
        status = self.service.working_tree_status(); self.list.clear(); self.rows = []
        for group, marker, staged in (("Staged", "✓", True), ("Added", "+", False), ("Modified", "M", False), ("Deleted", "D", False)):
            files = list(status["staged"]) if staged else status[group.lower()]
            for path in files:
                row = QWidget(); line = QHBoxLayout(row); check = QCheckBox(); line.addWidget(check); line.addWidget(QLabel(f"{marker}  {path}")); line.addStretch(); item = QListWidgetItem(); item.setSizeHint(row.sizeHint()); self.list.addItem(item); self.list.setItemWidget(item, row); self.rows.append((path, staged, check))
    def stage(self, add):
        selected = [path for path, staged, check in self.rows if check.isChecked() and staged != add]
        if not selected: return
        with repository_context(self.service.repository):
            if add:
                from Modules.staging import leaf_add
                for path in selected:
                    with contextlib.redirect_stdout(io.StringIO()): leaf_add(path)
            else:
                from Modules.commands import leaf_reset
                for path in selected:
                    with contextlib.redirect_stdout(io.StringIO()): leaf_reset(path)
        self.refresh(); self.changed.emit()
    def save(self):
        message = self.message.text().strip()
        if not message: return
        with repository_context(self.service.repository):
            from Modules.commands import leaf_save
            with contextlib.redirect_stdout(io.StringIO()): leaf_save(message)
        self.message.clear(); self.refresh(); self.changed.emit()


class ReferencesPage(QWidget):
    """Read-only branch/tag overview; mutations remain available via the CLI."""
    def __init__(self, service, kind):
        super().__init__(); self.service, self.kind = service, kind
        layout = QVBoxLayout(self); layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel(kind); title.setObjectName("pageTitle"); layout.addWidget(title)
        self.list = QListWidget(); self.list.setObjectName("historyList"); layout.addWidget(self.list, 1)
        self.refresh()
    def refresh(self):
        self.list.clear()
        values = self.service.branches() if self.kind == "Branches" else self.service.tags()
        current = self.service.current_branch() if self.kind == "Branches" else None
        if not values: self.list.addItem(f"No {self.kind.lower()} yet.")
        for name, commit in sorted(values.items()):
            marker = "  (current)" if name == current else ""
            self.list.addItem(f"{name}{marker}\n{commit or 'No commits'}")
