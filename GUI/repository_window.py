"""Repository workspace window coordinating modular stacked pages."""

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from GUI.repository_service import RepositoryService
from GUI.workspace_pages import BrowserPage, ChangesPage, CommitDetailPage, DiffPage, FileViewerPage, HistoryPage, ReferencesPage


class RepositoryWindow(QMainWindow):
    def __init__(self, repository, on_back):
        super().__init__()
        self.repository, self.on_back = str(Path(repository).resolve()), on_back
        self.service = RepositoryService(self.repository)
        self._fingerprint = self.service.fingerprint()
        self.setWindowTitle(f"Leaf • {Path(repository).name}")
        self.resize(1200, 760)
        self.build_ui()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1000)
        self.refresh_timer.timeout.connect(self.refresh_if_changed)
        self.refresh_timer.start()

    def build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        layout = QHBoxLayout(root); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        sidebar = QFrame(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(230)
        side = QVBoxLayout(sidebar)
        back = QPushButton("← Repositories"); back.clicked.connect(self.go_back); side.addWidget(back)
        name = QLabel(Path(self.repository).name); name.setObjectName("sidebarRepository"); side.addWidget(name)
        self.nav = QListWidget(); self.nav.setObjectName("navigation")
        for label in ("Overview", "Changes", "History", "Branches", "Tags"): self.nav.addItem(label)
        side.addWidget(self.nav, 1); layout.addWidget(sidebar)
        self.pages = QStackedWidget(); layout.addWidget(self.pages, 1)
        self.browser = BrowserPage(self.service); self.changes = ChangesPage(self.service)
        self.history = HistoryPage(self.service); self.viewer = FileViewerPage(self.service)
        self.commit = CommitDetailPage(self.service); self.diff = DiffPage(self.service)
        self.branches = ReferencesPage(self.service, "Branches"); self.tags = ReferencesPage(self.service, "Tags")
        for page in (self.browser, self.changes, self.history, self.branches, self.tags, self.viewer, self.commit, self.diff): self.pages.addWidget(page)
        self.nav.currentRowChanged.connect(self.open_navigation); self.nav.setCurrentRow(0)
        self.browser.file_requested.connect(self.open_file)
        self.viewer.back_requested.connect(lambda: self.show_page(0)); self.viewer.history_requested.connect(self.open_file_history)
        self.history.commit_requested.connect(self.open_commit); self.commit.back_requested.connect(lambda: self.show_page(2))
        self.commit.diff_requested.connect(self.open_diff); self.diff.back_requested.connect(lambda: self.show_page(6))
        self.changes.changed.connect(self.refresh_visible)

    def show_page(self, index): self.pages.setCurrentIndex(index)

    def open_navigation(self, index):
        self.show_page(index)
        if index == 0: self.browser.refresh()
        elif index == 1: self.changes.refresh()
        elif index == 2: self.history.show_history()

        elif index == 3: self.branches.refresh()
        elif index == 4: self.tags.refresh()
    def open_file(self, path): self.viewer.show_file(path); self.show_page(5)
    def open_file_history(self, path): self.history.show_history(path); self.show_page(2)
    def open_commit(self, commit_id): self.commit.show_commit(commit_id); self.show_page(6)
    def open_diff(self, commit_id, path): self.diff.show_diff(commit_id, path); self.show_page(7)

    def refresh_if_changed(self):
        fingerprint = self.service.fingerprint()
        if fingerprint != self._fingerprint:
            self._fingerprint = fingerprint
            self.refresh_visible()

    def refresh_visible(self):
        current = self.pages.currentIndex()
        if current == 0: self.browser.refresh()
        elif current == 1: self.changes.refresh()
        elif current == 2: self.history.refresh()
        elif current == 3: self.branches.refresh()
        elif current == 4: self.tags.refresh()
        elif current == 6 and self.commit.commit_id: self.commit.show_commit(self.commit.commit_id)

    def closeEvent(self, event): self.refresh_timer.stop(); super().closeEvent(event)
    def go_back(self): self.close(); self.on_back()
