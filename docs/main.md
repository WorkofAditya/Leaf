# Leaf Documentation

## Purpose

Leaf is a compact version control system designed to make repository history easy to see, explain, and rebuild. It stores project changes inside a `.leaf/` directory using readable JSON files and commit directories.

Leaf’s goal is clarity: users should be able to understand how commits, branches, staging, restore, merge, and repository rebuilding work without needing to learn a large distributed VCS implementation first.

## How Leaf Stores History

Leaf stores history in two phases:

1. **Initial snapshot** — the first commit records the full contents of every tracked text file.
2. **Diff commits** — later commits store line-based differences and deleted-file metadata relative to their parent commit.

When Leaf needs a commit’s full file state, it rebuilds that state from the initial snapshot through the commit’s first-parent ancestry.

## Core Concepts

| Concept | Description |
| --- | --- |
| Working tree | The files currently present in the project directory. |
| Commit | A saved state transition with metadata, parent links, and stored file data. |
| Snapshot commit | The first commit, containing complete files. |
| Diff commit | A later commit, containing line-based changes and deletions. |
| Branch | A named pointer stored in `.leaf/branches.json`. |
| HEAD | The currently checked-out commit ID stored in `.leaf/HEAD`. |
| Current branch | The active branch name stored in `.leaf/CURRENT_BRANCH`. |
| Detached HEAD | A state where `CURRENT_BRANCH` is empty and `HEAD` directly identifies the current commit. |
| Index | The staging area stored in `.leaf/index.json`. |
| Merge state | Temporary metadata for an in-progress merge. |

## Main Data Flow

```text
Working tree
    │
    ├── leaf add ───────────────► .leaf/index.json
    │                                  │
    └── leaf save ─────────────────────┘
             │
             ▼
      commit metadata + stored data
             │
             ├── .leaf/log.json
             ├── .leaf/commits/<id>/
             └── branch + HEAD updates
```

## Typical Lifecycle

```bash
leaf init
leaf add .
leaf save "initial snapshot"
leaf branch feature
leaf checkout feature
leaf save "feature work"
leaf checkout main
leaf merge feature
leaf log
```

This lifecycle demonstrates Leaf’s most important systems: initialization, staging, committing, branch switching, merging, and history traversal.

## Internal Modules

| Module | Responsibility |
| --- | --- |
| `leaf` | Parses command-line arguments and dispatches commands. |
| `Modules/commands.py` | Implements repository commands and most user-facing behavior. |
| `Modules/storage.py` | Reads and writes JSON storage files safely. |
| `Modules/rebuild.py` | Reconstructs file states from commits. |
| `Modules/files.py` | Discovers, reads, writes, ignores, and snapshots files. |
| `Modules/graph.py` | Traverses commit ancestry and finds merge bases. |
| `Modules/core.py` | Provides commit hash and current-state helpers. |
| `HEAD` | Manages `.leaf/HEAD` and `.leaf/CURRENT_BRANCH`. |
| `Modules/head_utils.py` | Dynamically loads the top-level `HEAD` module. |
| `Modules/common.py` | Defines paths, symbols, and terminal colors. |

## Repository Directory

```text
.leaf/
├── commits/
├── log.json
├── log.bak
├── branches.json
├── sessions.json
├── index.json
├── tags.json
├── MERGE_STATE.json
├── remotes.json
├── HEAD
└── CURRENT_BRANCH
```

## Design Principles

- **Readable storage:** JSON files make metadata easy to inspect.
- **Simple history reconstruction:** rebuild logic is centralized and predictable.
- **Branch safety:** restoring a commit detaches HEAD rather than silently moving branch pointers.
- **Small command surface:** commands cover the common version-control lifecycle without hiding too much implementation detail.
- **Educational implementation:** code is intentionally direct so the system can be studied module by module.
