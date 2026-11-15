# Core Helpers

**Source file:** `Modules/core.py`

`Modules/core.py` contains small helper functions that connect commit identity, HEAD resolution, and current-state rebuilding.

## Responsibilities

- Generate commit IDs from hashed data.
- Resolve the current commit from branch or detached HEAD state.
- Rebuild the latest saved repository state.

## Functions

### `leaf_hash_commit(data)`

Creates a SHA-256 digest from a string. Commit creation hashes a canonical JSON representation of the message, timestamp, parent IDs, and saved file contents, then uses a short prefix as the commit ID. Leaf checks existing IDs and commit directories before accepting the prefix, extending it with a new digest when a collision occurs.

### `leaf_get_head_commit_id(log=None)`

Returns the current commit ID.

Resolution order:

1. Load the commit log if the caller did not provide one.
2. Read the active branch from `.leaf/CURRENT_BRANCH`.
3. If attached to a branch, return that branch’s commit pointer from `.leaf/branches.json`.
4. If detached, return the direct commit ID stored in `.leaf/HEAD`.

This separation is important because attached branch state and detached HEAD state behave differently.

### `leaf_get_last_state()`

Rebuilds the file state at the current HEAD. If the repository has no commits or no resolvable HEAD, it returns an empty dictionary.

This helper is used by commands that need to compare the current working tree with the latest saved state, such as status, checkout sessions, and commit preparation.
