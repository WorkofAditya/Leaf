# Core Helpers
This module contains small but important helper functions used across the repository system.
## Important Functions
### leaf_hash_commit(data)
Creates a SHA1 hash. Leaf uses this hash to generate unique commit IDs. The hash is based on:
 * Commit message
 * Timestamps
 * Runtime values
### leaf_get_head_commit_id()
Returns the current commit ID. The function checks:
 1. Current branch pointer, when attached to a branch
 2. HEAD file, when no branch is active and the repository is detached
This keeps attached branch history independent from detached HEAD movement.
### leaf_get_last_state()
Rebuilds the latest repository state. It internally calls:
```python
leaf_rebuild()

```
This allows Leaf to compare current files with the previous saved version.
