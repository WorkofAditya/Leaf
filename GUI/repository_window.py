import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


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
        old = os.getcwd()
        try:
            os.chdir(self.repository)
            from Modules.core import leaf_get_head_commit_id
            from Modules.storage import load_branches, safe_load_log
            from Modules.head_utils import get_head_module
            from Modules.common import VCS_DIR
            log = safe_load_log()
            branches = load_branches()
            branch = get_head_module().read_current_branch(VCS_DIR) or "main"
            head = leaf_get_head_commit_id(log) if log else None
            self.info.setText(
                f"Current branch:  {branch}\n"
                f"HEAD:  {head or 'No commits yet'}\n"
                f"Branches:  {len(branches)}\n"
                f"Commits:  {len(log)}"
            )
        finally:
            os.chdir(old)


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
        layout.addWidget(title)
        layout.addWidget(self.list)
        self.refresh()

    def refresh(self):
        self.list.clear()
        old = os.getcwd()
        try:
            os.chdir(self.repository)
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
        finally:
            os.chdir(old)


class BranchesPage(QWidget):
    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel("Branches")
        title.setObjectName("pageTitle")
        self.list = QListWidget()
        layout.addWidget(title)
        layout.addWidget(self.list)
        self.refresh()

    def refresh(self):
        self.list.clear()
        old = os.getcwd()
        try:
            os.chdir(self.repository)
            from Modules.storage import load_branches
            from Modules.head_utils import get_head_module
            from Modules.common import VCS_DIR
            current = get_head_module().read_current_branch(VCS_DIR)
            for name, commit in sorted(load_branches().items()):
                marker = "  (current)" if name == current else ""
                self.list.addItem(f"🌿  {name}{marker}\n    {commit or 'No commits'}")
        finally:
            os.chdir(old)


class ChangesPage(QWidget):
    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel("Changes")
        title.setObjectName("pageTitle")
        self.status = QLabel()
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(title)
        layout.addWidget(self.status)
        layout.addStretch()
        self.refresh()

    def refresh(self):
        old = os.getcwd()
        try:
            os.chdir(self.repository)
            from Modules.storage import load_index
            from Modules.files import leaf_get_all_files
            index = load_index()
            files = leaf_get_all_files()
            self.status.setText(
                f"Working tree files:  {len(files)}\n"
                f"Staged entries:  {len(index)}\n\n"
                "Detailed staging and diff controls will be added next."
            )
        finally:
            os.chdir(old)


class RepositoryWindow(QMainWindow):
    def __init__(self, repository, on_back):
        super().__init__()
        self.repository = str(Path(repository).resolve())
        self.on_back = on_back
        self.setWindowTitle(f"Leaf • {Path(repository).name}")
        self.resize(1150, 720)
        self.build_ui()

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
        self.pages.addWidget(OverviewPage(self.repository))
        self.pages.addWidget(ChangesPage(self.repository))
        self.pages.addWidget(HistoryPage(self.repository))
        self.pages.addWidget(BranchesPage(self.repository))
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)
        layout.addWidget(self.pages, 1)

    def go_back(self):
        self.close()
        self.on_back()
