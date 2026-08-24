import contextlib
import io
import os
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
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
        last = leaf_get_last_state()
        last = {
            _normalize(path): content
            for path, content in last.items()
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
        self.marker = QLabel(marker)
        self.marker.setFixedWidth(22)
        self.path = QLabel(path)
        self.path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.checkbox)
        layout.addWidget(self.marker)
        layout.addWidget(self.path, 1)


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
            from Modules.storage import load_branches, safe_load_log
            from Modules.head_utils import get_head_module
            from Modules.common import VCS_DIR
            log = safe_load_log()
            branches = load_branches()
            branch = get_head_module().read_current_branch(VCS_DIR) or "detached"
            head = leaf_get_head_commit_id(log) if log else None
            status = working_tree_status(self.repository)
            total = sum(len(status[key]) for key in ("added", "modified", "deleted", "staged"))
            self.info.setText(
                f"Current branch:  {branch}\n"
                f"HEAD:  {head or 'No commits yet'}\n"
                f"Branches:  {len(branches)}\n"
                f"Commits:  {len(log)}\n"
                f"Working tree changes:  {total}\n"
                f"Staged:  {len(status['staged'])}"
            )


class HistoryPage(QWidget):
    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)
        title = QLabel("History")
        title.setObjectName("pageTitle")
        self.list = QListWidget()
        self.list.setObjectName("historyList")
        layout.addWidget(title)
        layout.addWidget(self.list)
        self.refresh()

    def refresh(self):
        self.list.clear()
        with repository_context(self.repository):
            from Modules.storage import safe_load_log
            from Modules.core import leaf_get_head_commit_id
            from Modules.graph import commit_chain, commit_map
            log = safe_load_log()
            if not log:
                self.list.addItem("No commits yet.")
                return
            head = leaf_get_head_commit_id(log)
            cmap = commit_map(log)
            for commit_id in commit_chain(head, cmap):
                commit = cmap[commit_id]
                self.list.addItem(
                    f"{commit['id']}   {commit.get('message', 'No message')}\n"
                    f"{commit.get('time', '')}   •   {commit.get('branch', 'main')}"
                )


class BranchesPage(QWidget):
    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)
        title = QLabel("Branches")
        title.setObjectName("pageTitle")
        self.list = QListWidget()
        self.list.setObjectName("historyList")
        layout.addWidget(title)
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
                self.list.addItem(f"🌿  {name}{marker}\n    {commit or 'No commits'}")


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
        self.commit_message = QLineEdit()
        self.commit_message.setPlaceholderText("Commit message")
        self.commit_message.returnPressed.connect(self.save_changes)
        save = QPushButton("Save Staged Changes")
        save.setObjectName("saveButton")
        save.clicked.connect(self.save_changes)
        actions.addWidget(stage_selected)
        actions.addWidget(unstage_selected)
        actions.addWidget(self.commit_message, 1)
        actions.addWidget(save)
        layout.addLayout(actions)

        self.list = QListWidget()
        self.list.setObjectName("changesList")
        layout.addWidget(self.list, 1)
        self.refresh()

    def _capture_checked_paths(self):
        for path, _, row in self.rows:
            if row.checkbox.isChecked():
                self.selected_paths.add(_normalize(path))
            else:
                self.selected_paths.discard(_normalize(path))

    def add_group(self, title, files, marker, staged=False):
        if not files:
            return
        header = QListWidgetItem(title)
        header.setFlags(Qt.NoItemFlags)
        self.list.addItem(header)
        for path in files:
            normalized = _normalize(path)
            row = ChangeRow(path, marker, checked=normalized in self.selected_paths)
            item = QListWidgetItem()
            item.setSizeHint(row.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, row)
            self.rows.append((normalized, staged, row))

    def refresh(self):
        self._capture_checked_paths()
        status = working_tree_status(self.repository)
        visible_paths = {
            _normalize(path)
            for path in list(status["staged"])
            + status["added"]
            + status["modified"]
            + status["deleted"]
            + status["conflicts"]
        }
        self.selected_paths.intersection_update(visible_paths)
        self.list.clear()
        self.rows = []
        staged = status["staged"]
        unstaged_count = len(status["added"]) + len(status["modified"]) + len(status["deleted"])
        total = len(staged) + unstaged_count + len(status["conflicts"])
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
        return [path for path, row_staged, row in self.rows if row_staged == staged and _normalize(path) in self.selected_paths]

    def stage_selected(self):
        paths = self.selected_rows(False)
        if not paths:
            self.summary.setText("Select one or more unstaged files")
            return
        with repository_context(self.repository):
            from Modules.staging import leaf_add
            with contextlib.redirect_stdout(io.StringIO()):
                for path in paths:
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
            with contextlib.redirect_stdout(io.StringIO()):
                for path in paths:
                    leaf_reset(path)
        self.selected_paths.difference_update(_normalize(path) for path in paths)
        self.refresh()

    def save_changes(self):
        message = self.commit_message.text().strip()
        if not message:
            self.summary.setText("Enter a commit message")
            return
        status = working_tree_status(self.repository)
        if not status["staged"]:
            self.summary.setText("Nothing staged to commit")
            return
        with repository_context(self.repository):
            from Modules.commands import leaf_save
            with contextlib.redirect_stdout(io.StringIO()):
                leaf_save(message)
        self.commit_message.clear()
        self.selected_paths.clear()
        self.refresh()


class RepositoryWindow(QMainWindow):
    def __init__(self, repository, on_back):
        super().__init__()
        self.repository = str(Path(repository).resolve())
        self.on_back = on_back
        self.setWindowTitle(f"Leaf • {Path(repository).name}")
        self.resize(1150, 720)
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
        for label in ["Overview", "Changes", "History", "Branches"]:
            self.nav.addItem(label)
        side.addWidget(self.nav, 1)
        layout.addWidget(sidebar)
        self.pages = QStackedWidget()
        self.overview_page = OverviewPage(self.repository)
        self.changes_page = ChangesPage(self.repository)
        self.history_page = HistoryPage(self.repository)
        self.branches_page = BranchesPage(self.repository)
        self.pages.addWidget(self.overview_page)
        self.pages.addWidget(self.changes_page)
        self.pages.addWidget(self.history_page)
        self.pages.addWidget(self.branches_page)
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)
        layout.addWidget(self.pages, 1)

    def refresh_all(self):
        current = self.pages.currentIndex()
        self.overview_page.refresh()
        self.changes_page.refresh()
        self.history_page.refresh()
        self.branches_page.refresh()
        self.pages.setCurrentIndex(current)

    def closeEvent(self, event):
        self.refresh_timer.stop()
        super().closeEvent(event)

    def go_back(self):
        self.close()
        self.on_back()
