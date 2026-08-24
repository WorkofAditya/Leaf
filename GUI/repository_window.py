import contextlib
import difflib
import io
import os
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


@contextlib.contextmanager
def repository_context(path):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def _normalize(path):
    return os.path.normpath(path)


def _capture_output(func, *args):
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        result = func(*args)
    return result, stream.getvalue().strip()


def working_tree_status(repository):
    with repository_context(repository):
        from Modules.common import LOG_FILE
        from Modules.core import leaf_get_last_state
        from Modules.files import is_binary, is_ignored_path, leaf_get_all_files, leaf_read_file
        from Modules.storage import load_index, load_merge_state

        if not os.path.exists(LOG_FILE):
            return {"staged": {}, "added": [], "modified": [], "deleted": [], "conflicts": []}

        index = load_index()
        staged_set = {_normalize(path) for path in index}
        last = {
            _normalize(path): content
            for path, content in leaf_get_last_state().items()
            if not is_ignored_path(path)
        }
        current = {_normalize(path) for path in leaf_get_all_files()}
        last_files = set(last)
        added = sorted((current - last_files) - staged_set)
        deleted = sorted((last_files - current) - staged_set)
        modified = []
        for path in sorted((current & last_files) - staged_set):
            if not is_binary(path) and leaf_read_file(path) != last[path]:
                modified.append(path)
        merge_state = load_merge_state()
        conflicts = sorted(merge_state.get("conflicts", [])) if merge_state else []
        return {
            "staged": index,
            "added": added,
            "modified": modified,
            "deleted": deleted,
            "conflicts": conflicts,
        }


class ChangeRow(QWidget):
    def __init__(self, path, marker, checked=False):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(checked)
        self.checkbox.stateChanged.connect(self._changed)
        self.marker = QLabel(marker)
        self.marker.setFixedWidth(22)
        self.path = QLabel(path)
        self.path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.checkbox)
        layout.addWidget(self.marker)
        layout.addWidget(self.path, 1)

    def _changed(self):
        self.checkbox.setProperty("leafSelection", True)


class OverviewPage(QWidget):
    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)
        title = QLabel(Path(repository).name or repository)
        title.setObjectName("pageTitle")
        path = QLabel(repository)
        path.setObjectName("muted")
        self.info = QLabel()
        self.info.setObjectName("repositoryInfo")
        layout.addWidget(title)
        layout.addWidget(path)
        layout.addWidget(self.info)
        layout.addStretch()
        self.refresh()

    def refresh(self):
        with repository_context(self.repository):
            from Modules.core import leaf_get_head_commit_id
            from Modules.storage import load_branches, load_tags, safe_load_log
            from Modules.head_utils import get_head_module
            from Modules.common import VCS_DIR
            log = safe_load_log()
            branches = load_branches()
            branch = get_head_module().read_current_branch(VCS_DIR) or "detached"
            head = leaf_get_head_commit_id(log) if log else None
            status = working_tree_status(self.repository)
            changes = sum(len(status[key]) for key in ("added", "modified", "deleted", "staged"))
            self.info.setText(
                f"Current branch:  {branch}\n"
                f"HEAD:  {head or 'No commits yet'}\n"
                f"Branches:  {len(branches)}\n"
                f"Tags:  {len(load_tags())}\n"
                f"Commits:  {len(log)}\n"
                f"Working tree changes:  {changes}\n"
                f"Staged:  {len(status['staged'])}"
            )


class HistoryPage(QWidget):
    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel("History")
        title.setObjectName("pageTitle")
        self.list = QListWidget()
        self.list.setObjectName("historyList")
        self.list.itemDoubleClicked.connect(self.show_commit_diff)
        layout.addWidget(title)
        layout.addWidget(self.list)
        self.refresh()

    def refresh(self):
        self.list.clear()
        with repository_context(self.repository):
            from Modules.storage import safe_load_log, load_tags
            from Modules.core import leaf_get_head_commit_id
            from Modules.graph import commit_chain, commit_map
            log = safe_load_log()
            if not log:
                self.list.addItem("No commits yet.")
                return
            head = leaf_get_head_commit_id(log)
            cmap = commit_map(log)
            tags = {}
            for tag, cid in load_tags().items():
                tags.setdefault(cid, []).append(tag)
            for commit_id in commit_chain(head, cmap):
                commit = cmap[commit_id]
                tag_text = ""
                if tags.get(commit_id):
                    tag_text = "  [" + ", ".join(sorted(tags[commit_id])) + "]"
                item = QListWidgetItem(
                    f"{commit['id']}   {commit.get('message', 'No message')}{tag_text}\n"
                    f"{commit.get('time', '')}   •   {commit.get('branch', 'main')}"
                )
                item.setData(Qt.UserRole, commit_id)
                self.list.addItem(item)

    def show_commit_diff(self, item):
        commit_id = item.data(Qt.UserRole)
        dialog = DiffDialog(self.repository, commit_id, self.window())
        dialog.exec()


class BranchesPage(QWidget):
    def __init__(self, repository, refresh_all):
        super().__init__()
        self.repository = repository
        self.refresh_all = refresh_all
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        title_row = QHBoxLayout()
        title = QLabel("Branches")
        title.setObjectName("pageTitle")
        new_branch = QPushButton("+ New Branch")
        new_branch.clicked.connect(self.create_branch)
        checkout = QPushButton("Checkout")
        checkout.clicked.connect(self.checkout_branch)
        merge = QPushButton("Merge")
        merge.clicked.connect(self.merge_branch)
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(new_branch)
        title_row.addWidget(checkout)
        title_row.addWidget(merge)
        layout.addLayout(title_row)
        self.list = QListWidget()
        self.list.setObjectName("historyList")
        layout.addWidget(self.list)
        self.refresh()

    def refresh(self):
        self.list.clear()
        with repository_context(self.repository):
            from Modules.storage import load_branches
            from Modules.head_utils import get_head_module
            from Modules.common import VCS_DIR
            current = get_head_module().read_current_branch(VCS_DIR)
            for name, commit in sorted(load_branches().items()):
                marker = "  (current)" if name == current else ""
                item = QListWidgetItem(f"🌿  {name}{marker}\n    {commit or 'No commits'}")
                item.setData(Qt.UserRole, name)
                self.list.addItem(item)

    def selected_branch(self):
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def create_branch(self):
        name, ok = text_dialog(self, "New Branch", "Branch name")
        if not ok or not name.strip():
            return
        with repository_context(self.repository):
            from Modules.commands import leaf_branch
            _, output = _capture_output(leaf_branch, name.strip())
        if output and "already exists" in output.lower():
            QMessageBox.warning(self, "Leaf", output)
            return
        self.refresh_all()

    def checkout_branch(self):
        branch = self.selected_branch()
        if not branch:
            return
        with repository_context(self.repository):
            from Modules.commands import leaf_checkout
            _, output = _capture_output(leaf_checkout, branch)
        if output:
            QMessageBox.information(self, "Leaf", output)
        self.refresh_all()

    def merge_branch(self):
        branch = self.selected_branch()
        if not branch:
            return
        with repository_context(self.repository):
            from Modules.commands import leaf_merge
            _, output = _capture_output(leaf_merge, branch)
        if output:
            QMessageBox.information(self, "Leaf", output)
        self.refresh_all()


class TagsPage(QWidget):
    def __init__(self, repository, refresh_all):
        super().__init__()
        self.repository = repository
        self.refresh_all = refresh_all
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        title_row = QHBoxLayout()
        title = QLabel("Tags")
        title.setObjectName("pageTitle")
        create = QPushButton("+ New Tag")
        create.clicked.connect(self.create_tag)
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(create)
        layout.addLayout(title_row)
        self.list = QListWidget()
        self.list.setObjectName("historyList")
        layout.addWidget(self.list)
        self.refresh()

    def refresh(self):
        self.list.clear()
        with repository_context(self.repository):
            from Modules.storage import load_tags
            for tag, commit in sorted(load_tags().items()):
                self.list.addItem(f"🏷  {tag}\n    {commit}")

    def create_tag(self):
        name, ok = text_dialog(self, "New Tag", "Tag name")
        if not ok or not name.strip():
            return
        with repository_context(self.repository):
            from Modules.commands import leaf_tag
            _, output = _capture_output(leaf_tag, name.strip())
        if output:
            QMessageBox.information(self, "Leaf", output)
        self.refresh_all()


class FilesPage(QWidget):
    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel("Files")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Path", "Size"])
        self.tree.itemDoubleClicked.connect(self.open_file)
        layout.addWidget(self.tree)
        self.refresh()

    def refresh(self):
        self.tree.clear()
        with repository_context(self.repository):
            from Modules.files import leaf_get_all_files
            for path in sorted(leaf_get_all_files()):
                item = QTreeWidgetItem([path, str(os.path.getsize(path))])
                item.setData(0, Qt.UserRole, path)
                self.tree.addTopLevelItem(item)

    def open_file(self, item, _column):
        path = item.data(0, Qt.UserRole)
        if not path:
            return
        full = str(Path(self.repository) / path)
        if not Path(full).is_file():
            return
        try:
            text = Path(full).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            QMessageBox.warning(self, "Leaf", str(exc))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(path)
        dialog.resize(900, 650)
        layout = QVBoxLayout(dialog)
        editor = QPlainTextEdit(text)
        editor.setReadOnly(True)
        layout.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()


class DiffDialog(QDialog):
    def __init__(self, repository, commit_id=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Leaf Diff")
        self.resize(1000, 700)
        layout = QVBoxLayout(self)
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        layout.addWidget(editor)
        with repository_context(repository):
            from Modules.common import LOG_FILE
            from Modules.core import leaf_get_head_commit_id, leaf_get_last_state
            from Modules.files import leaf_get_all_files, leaf_read_file, is_binary
            from Modules.graph import commit_map
            from Modules.storage import safe_load_log
            from Modules.rebuild import leaf_rebuild
            log = safe_load_log()
            target_id = commit_id or leaf_get_head_commit_id(log)
            if not target_id:
                editor.setPlainText("No commits yet.")
            else:
                target = leaf_rebuild(target_id, log)
                current = {
                    p: leaf_read_file(p)
                    for p in leaf_get_all_files()
                    if not is_binary(p)
                }
                lines = []
                if commit_id:
                    cmap = commit_map(log)
                    commit = cmap.get(commit_id, {})
                    lines.append(f"Commit: {commit_id}")
                    lines.append(f"Message: {commit.get('message', '')}")
                    lines.append("")
                else:
                    lines.append("Working tree vs HEAD")
                    lines.append("")
                for path in sorted(set(target) | set(current)):
                    diff = list(difflib.unified_diff(target.get(path, []), current.get(path, []), fromfile=path, tofile=path))
                    if diff:
                        lines.extend(diff)
                        lines.append("")
                editor.setPlainText("\n".join(lines) if len(lines) > 2 else "No differences.")
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class ChangesPage(QWidget):
    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        self.rows = []
        self.selected_paths = set()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)
        title_row = QHBoxLayout()
        title = QLabel("Changes")
        title.setObjectName("pageTitle")
        self.summary = QLabel()
        self.summary.setObjectName("muted")
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self.summary)
        layout.addLayout(title_row)
        actions = QHBoxLayout()
        stage_selected = QPushButton("Stage Selected")
        stage_selected.clicked.connect(self.stage_selected)
        unstage_selected = QPushButton("Unstage Selected")
        unstage_selected.clicked.connect(self.unstage_selected)
        show_diff = QPushButton("View Diff")
        show_diff.clicked.connect(self.view_diff)
        self.commit_message = QLineEdit()
        self.commit_message.setPlaceholderText("Commit message")
        save = QPushButton("Save Staged Changes")
        save.clicked.connect(self.save_changes)
        actions.addWidget(stage_selected)
        actions.addWidget(unstage_selected)
        actions.addWidget(show_diff)
        actions.addWidget(self.commit_message, 1)
        actions.addWidget(save)
        layout.addLayout(actions)
        self.list = QListWidget()
        layout.addWidget(self.list, 1)
        self.refresh()

    def _capture_checked_paths(self):
        for path, _, row in self.rows:
            key = _normalize(path)
            if row.checkbox.isChecked():
                self.selected_paths.add(key)
            else:
                self.selected_paths.discard(key)

    def add_group(self, title, files, marker, staged=False):
        if not files:
            return
        header = QListWidgetItem(title)
        header.setFlags(Qt.NoItemFlags)
        self.list.addItem(header)
        for path in files:
            normalized = _normalize(path)
            row = ChangeRow(path, marker, normalized in self.selected_paths)
            item = QListWidgetItem()
            item.setSizeHint(row.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, row)
            self.rows.append((normalized, staged, row))

    def refresh(self):
        self._capture_checked_paths()
        status = working_tree_status(self.repository)
        visible = {_normalize(path) for path in list(status["staged"]) + status["added"] + status["modified"] + status["deleted"] + status["conflicts"]}
        self.selected_paths.intersection_update(visible)
        self.list.clear()
        self.rows = []
        staged = status["staged"]
        total = len(staged) + len(status["added"]) + len(status["modified"]) + len(status["deleted"]) + len(status["conflicts"])
        self.summary.setText("Clean working tree" if total == 0 else f"{total} change(s) • {len(staged)} staged")
        if total == 0:
            item = QListWidgetItem("✓  Working tree is clean")
            item.setFlags(Qt.NoItemFlags)
            self.list.addItem(item)
            return
        self.add_group("STAGED", list(staged.keys()), "✓", True)
        self.add_group("ADDED", status["added"], "+")
        self.add_group("MODIFIED", status["modified"], "M")
        self.add_group("DELETED", status["deleted"], "−")
        self.add_group("CONFLICTS", status["conflicts"], "!")

    def selected_rows(self, staged):
        self._capture_checked_paths()
        return [path for path, row_staged, _ in self.rows if row_staged == staged and _normalize(path) in self.selected_paths]

    def stage_selected(self):
        paths = self.selected_rows(False)
        if not paths:
            self.summary.setText("Select one or more unstaged files")
            return
        with repository_context(self.repository):
            from Modules.staging import leaf_add
            for path in paths:
                with contextlib.redirect_stdout(io.StringIO()):
                    leaf_add(path)
        self.selected_paths.difference_update(_normalize(path) for path in paths)
        self.refresh()

    def unstage_selected(self):
        paths = self.selected_rows(True)
        if not paths:
            self.summary.setText("Select one or more staged files")
            return
        with repository_context(self.repository):
            from Modules.commands import leaf_reset
            for path in paths:
                with contextlib.redirect_stdout(io.StringIO()):
                    leaf_reset(path)
        self.selected_paths.difference_update(_normalize(path) for path in paths)
        self.refresh()

    def save_changes(self):
        message = self.commit_message.text().strip()
        if not message:
            self.summary.setText("Enter a commit message")
            return
        with repository_context(self.repository):
            from Modules.commands import leaf_save
            _, output = _capture_output(leaf_save, message)
        self.commit_message.clear()
        self.selected_paths.clear()
        if output and "No changes" in output:
            self.summary.setText(output)
        self.refresh()

    def view_diff(self):
        DiffDialog(self.repository, parent=self).exec()


class RepositoryWindow(QMainWindow):
    def __init__(self, repository, on_back):
        super().__init__()
        self.repository = str(Path(repository).resolve())
        self.on_back = on_back
        self.setWindowTitle(f"Leaf • {Path(repository).name}")
        self.resize(1200, 760)
        self.build_ui()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1000)
        self.refresh_timer.timeout.connect(self.refresh_all)
        self.refresh_timer.start()

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 22, 16, 18)
        side.setSpacing(8)
        back = QPushButton("←  Repositories")
        back.clicked.connect(self.go_back)
        side.addWidget(back)
        name = QLabel(Path(self.repository).name or self.repository)
        name.setObjectName("sidebarRepository")
        side.addWidget(name)
        side.addSpacing(16)
        self.nav = QListWidget()
        self.nav.setObjectName("navigation")
        for label in ["Overview", "Changes", "History", "Branches", "Tags", "Files"]:
            self.nav.addItem(label)
        side.addWidget(self.nav, 1)
        layout.addWidget(sidebar)
        self.pages = QStackedWidget()
        self.overview_page = OverviewPage(self.repository)
        self.changes_page = ChangesPage(self.repository)
        self.history_page = HistoryPage(self.repository)
        self.branches_page = BranchesPage(self.repository, self.refresh_all)
        self.tags_page = TagsPage(self.repository, self.refresh_all)
        self.files_page = FilesPage(self.repository)
        for page in [self.overview_page, self.changes_page, self.history_page, self.branches_page, self.tags_page, self.files_page]:
            self.pages.addWidget(page)
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)
        layout.addWidget(self.pages, 1)

    def refresh_all(self):
        current = self.pages.currentIndex()
        self.overview_page.refresh()
        self.changes_page.refresh()
        self.history_page.refresh()
        self.branches_page.refresh()
        self.tags_page.refresh()
        self.files_page.refresh()
        self.pages.setCurrentIndex(current)

    def closeEvent(self, event):
        self.refresh_timer.stop()
        super().closeEvent(event)

    def go_back(self):
        self.close()
        self.on_back()


def text_dialog(parent, title, placeholder):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    layout = QVBoxLayout(dialog)
    field = QLineEdit()
    field.setPlaceholderText(placeholder)
    field.returnPressed.connect(dialog.accept)
    layout.addWidget(field)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    ok = dialog.exec() == QDialog.Accepted
    return field.text(), ok
