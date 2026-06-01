<div align="center">
  <a href="">
   <img width="150" height="150" alt="Untitled_design_2_-removebg-preview" src="https://github.com/user-attachments/assets/b3de9948-ad0c-4a68-9e2c-efb8a77bfb8f" />

  </a>
 
  # _Preserve it,_ with [Leaf](https://github.com/WorkofAditya/Leaf)

  <p>
    Every change leaves a <strong><i>mark</i></strong>
    <br>
    Leaf remembers what you don’t.
    <br> 
    <b>Developed by <a href="https://github.com/WorkofAditya/">Adityasinh</a></b>
    <br>
    <br>
    <a href="https://github.com/WorkofAditya/Leaf/issues">Report a bug</a>
    <br />
    <a href="https://github.com/WorkofAditya/Leaf/issues">Request feature</a>
  </p>
</div>
<br>

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

## Leaf Web GUI
Leaf includes a local web interface that keeps the same minimalist style while connecting to the real Leaf CLI through a small Python backend. Start it from this repository and point it at any workspace:
```bash
python leaf_web.py --repo /path/to/project --port 8765
```
Then open `http://127.0.0.1:8765` to use Leaf Studio: a GitHub-style, page-based repository interface with dedicated Code, Commits, Branches, Merge Requests, Remotes, and Settings pages. The UI focuses on repository contents, visual change staging, commit boxes, history review, branch management, remote sync, ignore rules, and integrity checks instead of exposing CLI commands.

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
