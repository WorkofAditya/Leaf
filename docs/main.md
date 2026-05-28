# Leaf
Leaf is a lightweight version control system built to preserve file history in a simple and readable way.
Instead of trying to compete with Git in complexity, Leaf focuses on clarity. Every save creates a visible trail of changes, making it easier to understand what happened inside a project over time.
Leaf works by storing:
 * Snapshots of files
 * Line-by-line differences
 * Branch references
 * Rebuildable history
The project is designed around one idea:
> **Every change leaves a mark.**
## How Leaf Thinks
Leaf treats a project like a growing tree.
 * **A repository** is the tree.
 * **Commits** are branches and leaves.
 * **History** is the growth record.
 * **HEAD** is the current position on the tree.
Instead of storing full copies every time, Leaf stores only the changed lines after the first snapshot commit. That makes history smaller and easier to rebuild.
## Core Workflow
**Initialize a repository:**
```bash
leaf init
```
**Save changes:**
```bash
leaf save "initial setup"
```
**View current history:**
```bash
leaf log
```
`leaf log` follows the current branch or detached HEAD ancestry instead of printing unrelated commits from every branch.
**Restore a commit:**
```bash
leaf restore <commit-id>
```
Restoring a commit checks out that commit in detached HEAD mode, so existing branch pointers stay unchanged until you explicitly checkout or create a branch.
**Create branches:**
```bash
leaf branch feature-ui
```
**Switch branches:**
```bash
leaf checkout feature-ui
```
## Repository Structure
```text
.leaf/
├── commits/       # Stores commit data.
├── log.json       # Stores commit history and metadata.
├── branches.json  # Tracks branch pointers.
├── sessions.json  # Stores temporary branch states.
├── HEAD           # Stores the detached/current commit id.
└── CURRENT_BRANCH # Stores the active branch name, or empty when detached.
```
## Why Leaf Exists
Leaf was built to make version control easier to understand. Most version control systems hide their internal behavior behind complicated commands and layers of abstraction.
Leaf exposes the process in a more human-readable way. You can follow how commits are stored, rebuilt, restored, and connected without needing deep knowledge of distributed systems.
