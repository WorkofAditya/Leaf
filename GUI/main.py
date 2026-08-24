import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

APP_DIR = Path(os.getenv("APPDATA", Path.home())) / "Leaf"
REPOSITORIES_FILE = APP_DIR / "repositories.json"


class RepositoryManager:
    def __init__(self):
        self.repositories = []
        self.load()

    def load(self):
        try:
            if REPOSITORIES_FILE.exists():
                data = json.loads(REPOSITORIES_FILE.read_text(encoding="utf-8"))
                self.repositories = data.get("repositories", [])
        except (OSError, json.JSONDecodeError):
            self.repositories = []

    def save(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        REPOSITORIES_FILE.write_text(
            json.dumps({"repositories": self.repositories}, indent=2),
            encoding="utf-8",
        )

    def add(self, path):
        path = str(Path(path).resolve())
        if path not in self.repositories:
            self.repositories.append(path)
            self.save()

    def remove(self, path):
        if path in self.repositories:
            self.repositories.remove(path)
            self.save()


class RepositoryCard(QFrame):
    def __init__(self, path, on_open):
        super().__init__()
        self.path = path
        self.setObjectName("repositoryCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        name = QLabel(Path(path).name or path)
        name.setObjectName("repositoryName")

        location = QLabel(path)
        location.setObjectName("repositoryPath")
        location.setTextInteractionFlags(Qt.TextSelectableByMouse)

        open_button = QPushButton("Open Repository")
        open_button.clicked.connect(lambda: on_open(path))

        layout.addWidget(name)
        layout.addWidget(location)
        layout.addWidget(open_button)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = RepositoryManager()
        self.repository_window = None
        self.setWindowTitle("Leaf")
        self.resize(1000, 650)
        self.build_ui()
        self.refresh()

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        title = QLabel("🍃 Leaf")
        title.setObjectName("title")

        subtitle = QLabel("Your repositories")
        subtitle.setObjectName("subtitle")

        self.repository_list = QListWidget()
        self.repository_list.setObjectName("repositoryList")
        self.repository_list.setSpacing(12)

        add_button = QPushButton("＋  Add Repository")
        add_button.setObjectName("addButton")
        add_button.clicked.connect(self.add_repository)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.repository_list, 1)
        layout.addWidget(add_button)

    def refresh(self):
        self.repository_list.clear()

        valid = []
        for path in self.manager.repositories:
            if (Path(path) / ".leaf").is_dir():
                valid.append(path)
                item = QListWidgetItem()
                card = RepositoryCard(path, self.open_repository)
                item.setSizeHint(card.sizeHint())
                self.repository_list.addItem(item)
                self.repository_list.setItemWidget(item, card)

        if valid != self.manager.repositories:
            self.manager.repositories = valid
            self.manager.save()

        if not valid:
            item = QListWidgetItem("No Leaf repositories yet. Add one below.")
            item.setFlags(Qt.NoItemFlags)
            self.repository_list.addItem(item)

    def add_repository(self):
        path = QFileDialog.getExistingDirectory(self, "Select Leaf repository")
        if not path:
            return

        if not (Path(path) / ".leaf").is_dir():
            answer = QMessageBox.question(
                self,
                "Not a Leaf repository",
                "This folder does not contain a .leaf repository. Initialize it?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if answer == QMessageBox.Yes:
                from Modules.commands import leaf_init

                old = os.getcwd()
                try:
                    os.chdir(path)
                    leaf_init()
                finally:
                    os.chdir(old)
            else:
                return

        self.manager.add(path)
        self.refresh()

    def open_repository(self, path):
        from GUI.repository_window import RepositoryWindow

        self.hide()
        self.repository_window = RepositoryWindow(path, self.return_to_repositories)
        self.repository_window.show()

    def return_to_repositories(self):
        self.repository_window = None
        self.refresh()
        self.show()
        self.raise_()
        self.activateWindow()


def run():
    app = QApplication(sys.argv)
    app.setApplicationName("Leaf")
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()


STYLESHEET = """
QMainWindow, QWidget {
    background: #111315;
    color: #edf2ee;
    font-family: Segoe UI;
    font-size: 14px;
}

QLabel#title {
    font-size: 32px;
    font-weight: 700;
}

QLabel#subtitle {
    color: #9da7a0;
    font-size: 16px;
}

QLabel#pageTitle {
    font-size: 28px;
    font-weight: 700;
}

QLabel#muted {
    color: #8f9992;
}

QLabel#repositoryInfo {
    background: #191d1b;
    border: 1px solid #2b332e;
    border-radius: 12px;
    padding: 18px;
    font-size: 16px;
    line-height: 1.5;
}

QLabel#sidebarRepository {
    font-size: 18px;
    font-weight: 600;
    padding: 8px;
}

QListWidget#repositoryList, QListWidget#historyList, QListWidget#navigation {
    background: transparent;
    border: none;
    outline: none;
}

QListWidget#repositoryList::item {
    background: transparent;
    border: none;
}

QListWidget#historyList::item, QListWidget#navigation::item {
    background: #191d1b;
    border: 1px solid #2b332e;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 6px;
}

QListWidget#navigation::item:selected {
    background: #26302a;
    border-color: #3b4a40;
}

QFrame#repositoryCard {
    background: #191d1b;
    border: 1px solid #2b332e;
    border-radius: 12px;
}

QFrame#sidebar {
    background: #151816;
    border-right: 1px solid #2b332e;
}

QLabel#repositoryName {
    font-size: 18px;
    font-weight: 600;
}

QLabel#repositoryPath {
    color: #8f9992;
}

QPushButton {
    background: #26302a;
    border: 1px solid #354038;
    border-radius: 8px;
    padding: 9px 14px;
}

QPushButton:hover {
    background: #303b34;
}

QPushButton#addButton {
    padding: 12px;
    font-size: 15px;
    font-weight: 600;
}
"""
