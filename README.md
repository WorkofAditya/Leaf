<div align="center">
  <a href="https://github.com/WorkofAditya/Leaf">
  
<img width="1408" height="768" alt="1000153396" src="https://github.com/user-attachments/assets/69791615-dd89-4994-a8af-bbd77db08559" />
</a>

  # _Preserve it,_ with [Leaf](https://github.com/WorkofAditya/Leaf)

  <p>
    Every change leaves a <strong><i>mark</i></strong>.<br>
    Leaf remembers what you don’t.<br>
    <b>Developed by <a href="https://github.com/WorkofAditya/">Adityasinh</a></b>
  </p>

  <p>
    <a href="https://github.com/WorkofAditya/Leaf/issues">Report a bug</a>
    ·
    <a href="https://github.com/WorkofAditya/Leaf/issues">Request a feature</a>
  </p>
</div>

---

## Overview

Leaf is a lightweight version control system built to preserve file history in a simple and readable way. Instead of trying to compete with Git in complexity, Leaf focuses on clarity. Every save creates a visible trail of changes, making it easier to understand what happened inside a project over time.

Leaf tracks a project by combining:

- **Snapshots** for the first complete repository state.
- **Line-based diffs** for later commits.
- **Branch pointers** for named lines of development.
- **HEAD state** for the currently checked-out commit or branch.
- **Rebuild logic** that reconstructs files from saved history.

> **Every change leaves a mark.**

## Mental Model

Leaf treats a repository like a growing tree:

| Concept | Meaning in Leaf |
| --- | --- |
| Repository | The tree that contains tracked project history. |
| Commit | A saved mark in time. |
| Branch | A named pointer to a commit. |
| HEAD | The current position in history. |
| Rebuild | The process of recreating files from stored commits. |

The first commit stores a full snapshot. Later commits store differences against their parent commit. When Leaf restores, diffs, merges, or checks status, it rebuilds commit state from history and compares that state with the working tree.

## Quick Start

```bash
# Create a Leaf repository in the current directory
leaf init

# Save the current project state
leaf save "initial setup"

# Inspect history on the current branch or detached HEAD
leaf log

# View changes between the working tree and HEAD
leaf diff
```

## Common Workflow

### 1. Initialize a repository

```bash
leaf init
```

This creates the `.leaf/` directory, initializes storage files, creates the default `main` branch, and attaches `HEAD` to `main`.

### 2. Stage selected files, or commit everything

```bash
leaf add src/app.py
leaf save "update app entry point"
```

If files are staged, `leaf save` commits the staged index. If nothing is staged, it commits the current working state.

### 3. Check project status

```bash
leaf status
```

Status compares the working tree with the rebuilt HEAD state and reports staged, added, modified, deleted, and merge-conflict files.

### 4. Create and switch branches

```bash
leaf branch feature-ui
leaf checkout feature-ui
```

Branch checkout saves unresolved working changes for the branch as a session, restores the target branch state, updates `HEAD`, and clears the staging index.

### 5. Restore a specific commit

```bash
leaf restore <commit-id>
```

Restore writes the selected commit to the working tree and enters **detached HEAD** mode. Existing branch pointers are not moved.

## Command Reference

| Command | Purpose |
| --- | --- |
| `leaf init` | Create a repository. |
| `leaf clone <path> [dest]` | Clone a local Leaf repository. |
| `leaf import-git` | Import an existing `.git` repository into Leaf metadata while preserving commits, branches, tags, and remotes. |
| `leaf export-git` | Export an existing Leaf repository into a `.git` repository while preserving commits, branches, tags, and remotes. |
| `leaf add <path>` | Stage a file, deleted path, or `.` for all files. |
| `leaf save <message>` | Create a commit. |
| `leaf status` | Show staged and working-tree changes. |
| `leaf diff [commit]` | Compare the working tree with a commit. Defaults to HEAD. |
| `leaf log` | Show ancestry for the current branch or detached HEAD. |
| `leaf restore <commit>` | Restore a commit and detach HEAD. |
| `leaf reset <path>` | Unstage a path. |
| `leaf reset --soft <commit>` | Move HEAD or the current branch pointer without rewriting files. |
| `leaf reset --hard <commit>` | Move HEAD or the current branch pointer and rewrite files. |
| `leaf branch [name] [commit]` | List branches or create a branch at HEAD or a commit. |
| `leaf checkout <branch>` | Switch to a branch. |
| `leaf merge <branch>` | Merge another branch into the current branch. |
| `leaf merge --continue` | Complete a conflicted merge after markers are resolved. |
| `leaf merge --abort` | Cancel a merge and restore the target branch state. |
| `leaf revert <commit>` | Create a new commit that reverses another commit. |
| `leaf tag [name] [commit]` | List tags or create a lightweight tag. |
| `leaf ignore <path>` | Add an ignore pattern to `.leafignore`. |
| `leaf fsck` | Validate repository integrity. |
| `leaf version` | Fetch and print the remote version file. |
| `leaf help` | Print CLI help. |

Remote-style commands (`remote`, `fetch`, `pull`, and `push`) are currently disabled in the CLI.

## Repository Layout

```text
.leaf/
├── commits/             # Commit object directories.
│   └── <commit-id>/     # Snapshot files or diff/state data for one commit.
├── log.json             # Ordered commit metadata.
├── log.bak              # Backup of the previous log file.
├── branches.json        # Branch name -> commit ID map.
├── sessions.json        # Unsaved branch working states preserved across checkout.
├── index.json           # Staging area.
├── tags.json            # Lightweight tag name -> commit ID map.
├── MERGE_STATE.json     # In-progress merge metadata.
├── remotes.json         # Reserved local remote configuration storage.
├── HEAD                 # Current commit ID.
└── CURRENT_BRANCH       # Active branch name, or empty in detached HEAD mode.
```

## Documentation Map

Detailed internal documentation lives in [`docs/`](docs/main.md):

- [`docs/main.md`](docs/main.md) — project overview and system flow.
- [`docs/command.md`](docs/command.md) — command engine and workflows.
- [`docs/storage.md`](docs/storage.md) — JSON persistence layer.
- [`docs/rebuild.md`](docs/rebuild.md) — history reconstruction.
- [`docs/HEAD.md`](docs/HEAD.md) — HEAD and branch attachment behavior.
- [`docs/files.md`](docs/files.md) — file discovery, ignore rules, snapshots.
- [`docs/graph.md`](docs/graph.md) — commit ancestry and merge-base helpers.
- [`docs/core.md`](docs/core.md) — shared commit and state helpers.
- [`docs/common.md`](docs/common.md) — constants, paths, symbols, colors.
- [`docs/head_utils.md`](docs/head_utils.md) — dynamic loader for the top-level `HEAD` module.
- [`docs/leaf.md`](docs/leaf.md) — CLI entry point.

## Development Notes

- Leaf is implemented in Python.
- The executable CLI is the top-level `leaf` file.
- Most behavior lives in `Modules/commands.py`.
- Repository data is stored as readable JSON plus commit directories.
- Binary files are skipped for diff generation.
- The project intentionally favors transparency over advanced VCS features.
