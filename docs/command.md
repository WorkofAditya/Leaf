# Command System

**Source file:** `Modules/commands.py`

`Modules/commands.py` is the main repository engine. The CLI entry point calls this module after parsing the command name and arguments. It coordinates file scanning, storage, HEAD updates, branch pointers, rebuilds, merges, staging, tags, and integrity checks.

## Responsibilities

- Create and initialize `.leaf/` repositories.
- Capture working-tree state.
- Create snapshot and diff commits.
- Manage branch pointers and branch sessions.
- Compare working files against rebuilt commit state.
- Restore commits into the working tree.
- Stage and unstage paths.
- Perform fast-forward and three-way merges.
- Create tags and revert commits.
- Validate repository integrity.
- Clone local Leaf repositories.
- Import existing Git repositories into Leaf metadata.
- Export Leaf repositories into Git repositories.

## Commit Creation Flow

```text
leaf save
   │
   ├── read merge state and staging index
   ├── choose target state
   │     ├── merge result, if a merge is in progress
   │     ├── indexed files, if paths are staged
   │     └── full working state, if nothing is staged
   ├── calculate parent commit
   ├── create snapshot or diff commit
   ├── write commit directory
   ├── append metadata to log.json
   ├── update branch pointer when attached
   ├── update HEAD
   └── clear index
```

## Important Functions

### `leaf_init()`

Creates the `.leaf/` repository structure. Initialization creates commit storage, the commit log, branch storage, session storage, index storage, tag storage, remote storage, merge state, and HEAD files. The default branch is `main`.

### `leaf_save(msg)`

Creates a commit with the provided message. The saved state depends on repository context:

- If a merge is in progress, Leaf verifies conflict markers are resolved and saves a merge commit with two parents.
- If the staging index contains entries, Leaf applies the index to the rebuilt HEAD state and commits that staged state.
- If the index is empty, Leaf commits the full current working state.

### `_create_commit(...)`

Builds commit metadata, calculates changed and deleted files, writes commit storage, appends to `log.json`, updates the current branch pointer, writes `HEAD`, and clears the staging area.

### `leaf_log()`

Prints history by walking from the current branch head or detached HEAD through the commit graph. Merge commits display their parent IDs, and commits with tags show tag names.

### `leaf_status()`

Reports repository state by comparing the working tree with the rebuilt HEAD state. It displays staged entries, merge conflicts, added files, modified files, deleted files, or a clean-working-tree message.

### `leaf_diff(commit_id=None)`

Rebuilds the selected commit, compares it with the working tree, and prints unified diffs. If no commit ID is provided, Leaf compares against HEAD.

### `leaf_restore(commit_id)`

Rebuilds a commit, writes that state to the working tree, updates `.leaf/HEAD`, clears `.leaf/CURRENT_BRANCH`, clears the index, clears merge state, and enters detached HEAD mode.

### `leaf_branch(name=None, commit_id=None)`

Lists branches when no name is provided. When a name is supplied, it creates a new branch at the provided commit or at the current HEAD.

### `leaf_checkout(branch_name)`

Switches to a branch. If the current branch has unsaved changes, Leaf stores them in `sessions.json`. It then restores the target branch’s saved session or rebuilt commit state, updates HEAD, attaches `CURRENT_BRANCH`, and clears the index.

### `leaf_merge(source_branch)`

Merges another branch into the current branch. The merge system supports:

- Already-up-to-date checks.
- Fast-forward merges.
- Three-way merges.
- Conflict markers.
- Merge commits with two parents.
- `leaf merge --continue`.
- `leaf merge --abort`.

### `leaf_add(path)`

Stages a file, deleted path, or all trackable files when `path` is `.`. Staged content is stored in `.leaf/index.json`.

### `leaf_reset(arg=None, commit_id=None)`

Supports two kinds of reset:

- `leaf reset <path>` unstages a path.
- `leaf reset` clears the entire index.
- `leaf reset --soft <commit>` moves HEAD or the active branch pointer while leaving files unchanged.
- `leaf reset --hard <commit>` moves HEAD or the active branch pointer and rewrites the working tree.

### `leaf_revert(commit_id)`

Creates a new commit that reverses the file changes introduced by an existing commit. It requires a clean working tree.

### `leaf_tag(name=None, commit_id=None)`

Lists tags when no name is supplied. Otherwise, creates a lightweight tag pointing to the supplied commit or current HEAD.

### `leaf_fsck()`

Validates repository integrity by checking that commit directories exist and that parent, branch, and tag pointers reference known commits.

### `leaf_clone(source, dest=None)`

Copies the `.leaf/` directory from a local source repository, rebuilds the default branch into the destination working tree, and initializes HEAD metadata.

### `leaf_import_git()`

Imports an existing `.git` repository into `.leaf` metadata. The importer walks Git commits in topological order, recreates Leaf commit entries, preserves merge parents, stores branches and tags, records remotes, and keeps the original `.git` directory untouched.

### `leaf_export_git()`

Exports an existing `.leaf` repository into a new `.git` repository. The exporter recreates commits, branches, tags, remotes, and the current HEAD checkout, and refuses to overwrite an existing `.git` directory.

## Disabled Remote Commands

The CLI currently disables `remote`, `fetch`, `pull`, and `push`. Commented implementations remain in `Modules/commands.py` for future review, but users cannot execute those commands through the current CLI.
