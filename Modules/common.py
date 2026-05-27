import os

VCS_DIR = ".leaf"
COMMITS_DIR = os.path.join(VCS_DIR, "commits")
LOG_FILE = os.path.join(VCS_DIR, "log.json")
LOG_BACKUP = os.path.join(VCS_DIR, "log.bak")
BRANCHES_FILE = os.path.join(VCS_DIR, "branches.json")
HEAD_MODULE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "HEAD")

LEAF = "🍃"
SPROUT = "🌱"
HERB = "🌿"
DRY = "🍂"
TREE = "🌳"

RESET = "\033[0m"
RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
GRAY = "\033[90m"
