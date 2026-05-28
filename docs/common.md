# Shared Constants
This file stores shared paths, symbols, and constants used across the project. Instead of repeating values everywhere, Leaf keeps them in one place.
## What Is Stored Here
### Repository Paths
These define where Leaf stores repository data.
```python
VCS_DIR
COMMITS_DIR
LOG_FILE

```
### Visual Symbols
Leaf uses emoji symbols for readable terminal output. This gives the CLI more personality and makes messages easier to notice.
```python
LEAF = "🍃"
TREE = "🌳"
DRY = "🍂"

```
### Terminal Colors
ANSI color codes are stored here. These are used to print colored terminal messages.
## Why This File Exists
Centralizing shared values makes maintenance easier. If a storage path changes later, only one file needs updating.
