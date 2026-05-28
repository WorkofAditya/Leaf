# Repository Rebuild System
**File:** Modules/rebuild.py
This module reconstructs repository state from commit history. It is one of the most important systems inside Leaf.
## How Rebuilding Works
Leaf stores one full snapshot, followed by line-based diffs. To restore a repository state, Leaf:
 1. Starts from the initial snapshot.
 2. Applies every diff in chronological order.
 3. Rebuilds the final file state.
## Important Functions
### leaf_rebuild(commit_id, log)
Recreates the repository exactly as it existed at a commit. It:
 * Loads commit history.
 * Walks through parent chains.
 * Applies diffs.
 * Removes deleted files.
 * Rebuilds file contents.
This function powers restore, diff, and history traversal capabilities.
### write_working_tree(files)
Writes rebuilt files back into the project directory. It also removes files that should no longer exist. This keeps the working tree synchronized with rebuilt history.
