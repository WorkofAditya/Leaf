# Core Helpers

**Source file:** `Modules/core.py`

`Modules/core.py` contains small helper functions that connect commit identity, HEAD resolution, and current-state rebuilding.

## Responsibilities

- Generate commit IDs from hashed data.
- Resolve the current commit from branch or detached HEAD state.
- Rebuild the latest saved repository state.

## Functions

### `leaf_hash_commit(data)`

Creates a SHA-1 hash from a string. Commit creation truncates this hash to produce compact commit IDs.

Commit ID input includes message text, formatted time, and runtime time data. This makes IDs stable enough for a small educational VCS while keeping them short and readable.

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
