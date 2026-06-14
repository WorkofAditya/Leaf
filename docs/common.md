# Shared Constants

**Source file:** `Modules/common.py`

`Modules/common.py` centralizes constants used throughout Leaf. Keeping paths, symbols, and terminal colors in one module avoids duplication and makes global changes easier.

## Repository Paths

| Constant | Path | Purpose |
| --- | --- | --- |
| `VCS_DIR` | `.leaf` | Root directory for Leaf metadata. |
| `COMMITS_DIR` | `.leaf/commits` | Commit object storage. |
| `LOG_FILE` | `.leaf/log.json` | Ordered commit metadata. |
| `LOG_BACKUP` | `.leaf/log.bak` | Backup copy of the previous log. |
| `BRANCHES_FILE` | `.leaf/branches.json` | Branch pointer map. |
| `SESSIONS_FILE` | `.leaf/sessions.json` | Unsaved branch working states. |
| `INDEX_FILE` | `.leaf/index.json` | Staging area. |
| `TAGS_FILE` | `.leaf/tags.json` | Lightweight tag map. |
| `MERGE_STATE_FILE` | `.leaf/MERGE_STATE.json` | In-progress merge metadata. |
| `REMOTES_FILE` | `.leaf/remotes.json` | Reserved remote configuration storage. |
| `HEAD_MODULE_PATH` | top-level `HEAD` file | Dynamic path to the HEAD helper module. |

## CLI Symbols

Leaf uses small icons to make terminal output easier to scan:

| Constant | Symbol | Typical Meaning |
| --- | --- | --- |
| `LEAF` | 🍃 | Commit or saved-change output. |
| `SPROUT` | 🌱 | Creation or staging output. |
| `HERB` | 🌿 | Informational output. |
| `DRY` | 🍂 | Warnings or no-op messages. |
| `TREE` | 🌳 | Repository, restore, merge, and checkout output. |

## Terminal Colors

The module also defines ANSI color constants:

- `RESET`
- `RED`
- `GREEN`
- `BLUE`
- `GRAY`

These colors are used by status, diff, and integrity commands to distinguish additions, deletions, modifications, and errors.

## Why This Module Matters

Centralized constants keep the rest of Leaf consistent. Storage modules, command handlers, and helper modules all depend on the same path definitions instead of recreating file names independently.
