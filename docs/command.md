# Command System
This is the core engine of Leaf. Most repository behavior happens inside this file.
It contains the logic for:
 * Commits
 * Branches
 * Restore
 * Diff
 * Merge
 * Staging
 * Tags
 * Reset and revert
 * Local remotes
 * Integrity checks
 * Logs
 * Repository state

## Important Functions
### leaf_init()
Creates the repository structure. It builds the `.leaf/` directory and initializes commit storage, branch storage, sessions, the staging index, tags, remotes, merge state, and HEAD.

### leaf_save(msg)
Creates a new commit. It commits the staged index when paths are staged, commits the full working state when no index exists, and finalizes merge commits when a merge is in progress.

### leaf_log()
Prints commit history by walking current branch or detached HEAD ancestry. It displays merge parents and tags when they exist.

### leaf_restore()
Rebuilds a commit state, writes it to the working tree, and clears the current branch so the repository enters detached HEAD mode without moving branch pointers.

### leaf_diff()
Rebuilds a commit state and compares it with the working tree.

### leaf_add() / leaf_reset()
`leaf add` stages file contents in `.leaf/index.json`. `leaf reset <path>` unstages a path, while `leaf reset --soft|--hard <commit>` moves the current branch pointer and optionally rewrites the working tree.

### leaf_merge()
Supports fast-forward merges, true three-way merges, merge commits with two parents, conflict markers, `leaf merge --continue`, and `leaf merge --abort`.

### leaf_tag()
Creates and lists lightweight tags stored in `.leaf/tags.json`.

### leaf_revert()
Creates a new commit that reverses the file changes introduced by an earlier commit.

### leaf_remote() / leaf_fetch() / leaf_pull() / leaf_push() / leaf_clone()
Provides local path-based remote workflows for synchronizing commits and branch pointers between Leaf repositories.

### leaf_fsck()
Checks repository integrity by validating commit directories, parent references, branch pointers, and tag pointers.
