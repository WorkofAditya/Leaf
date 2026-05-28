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
 1. HEAD file
 2. Current branch pointer
This makes Leaf more reliable when switching branches.
### leaf_get_last_state()
Rebuilds the latest repository state. It internally calls:
```python
leaf_rebuild()

```
This allows Leaf to compare current files with the previous saved version.
