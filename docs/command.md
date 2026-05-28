# Command System
This is the core engine of Leaf. Most repository behavior happens inside this file.
It contains the logic for:
 * Commits
 * Branches
 * Restore
 * Diff
 * Merge
 * Logs
 * Repository state
## Why This File Is Important
If the leaf file is the command receiver, commands.py is the actual brain. It performs the heavy work behind every command.
## Important Functions
### leaf_init()
Creates the repository structure. It builds the .leaf/ directory and initializes:
 * Commit storage
 * Branch storage
 * Logs
 * Sessions
 * HEAD
### leaf_save(msg)
Creates a new commit. This function:
 1. Scans project files.
 2. Compares them with the previous state.
 3. Creates diffs.
 4. Stores commit metadata.
 5. Updates branch pointers when attached to a branch.
 6. Moves HEAD forward.
  - *Note: The first commit becomes a full snapshot. All later commits store only changes.*
### leaf_log()
Prints commit history by walking parent commits from the current branch tip or detached HEAD. It also marks the current HEAD commit and does not show unrelated branch commits.
### leaf_restore()
Rebuilds a commit state, writes it to the working tree, and clears the current branch so the repository enters detached HEAD mode without moving any branch pointer.
### leaf_diff()
Rebuilds a commit state and compares file changes. Useful for understanding what changed between saves.
## Internal Design
This file connects almost every module together. It imports:
 * Storage helpers
 * Rebuild logic
 * Graph utilities
 * File scanning
 * HEAD management
That makes it the center of repository operations.
