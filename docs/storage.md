# Storage System

**Source file:** `Modules/storage.py`

The storage module provides the persistence layer for Leaf. It reads and writes JSON files inside `.leaf/` and hides error handling from the command engine.

## Storage Files

| File | Contents |
| --- | --- |
| `.leaf/log.json` | Ordered commit metadata. |
| `.leaf/log.bak` | Backup of the previous log file. |
| `.leaf/branches.json` | Branch name to commit ID map. |
| `.leaf/sessions.json` | Saved unsaved working states for branches. |
| `.leaf/index.json` | Staging area. |
| `.leaf/tags.json` | Tag name to commit ID map. |
| `.leaf/MERGE_STATE.json` | Metadata for an in-progress merge. |
| `.leaf/remotes.json` | Reserved remote configuration map. |

## Atomic JSON Writes

### `_atomic_json_save(path, data)`

Writes JSON by first creating a temporary file in the target directory and then replacing the destination file. This reduces the chance of partially written JSON files if a write is interrupted.

## Safe JSON Reads

### `_load_json(path, default)`

Attempts to load JSON from a file. If the file is missing, unreadable, invalid, or does not match the expected default type, the default value is returned.

## Commit Log Functions

### `safe_load_log()`

Loads `.leaf/log.json`. If the main log is unavailable and a backup exists, it falls back to `.leaf/log.bak`.

### `safe_save_log(log)`

Copies the current log to `.leaf/log.bak` before writing the new log with `_atomic_json_save()`.

## Branch and Session Functions

### `load_branches()` / `save_branches(branches)`

Load and save branch pointers. The default branch map is `{ "main": None }`.

### `load_sessions()` / `save_sessions(sessions)`

Load and save branch sessions. Sessions preserve unsaved working changes when switching branches.

## Index Functions

### `load_index()` / `save_index(index)`

Load and save staged file data.

### `clear_index()`

Resets the staging area to an empty object.

## Tag Functions

### `load_tags()` / `save_tags(tags)`

Load and save lightweight tag pointers.

## Merge State Functions

### `load_merge_state()` / `save_merge_state(state)`

Load and save metadata for an in-progress merge.

### `clear_merge_state()`

Removes `.leaf/MERGE_STATE.json` if it exists.

## Remote Storage Functions

### `load_remotes()` / `save_remotes(remotes)`

Load and save remote configuration data. The current CLI disables remote operations, but the storage helpers remain available.

## Why This Module Matters

Centralizing persistence keeps repository commands focused on behavior instead of JSON parsing, backup management, and safe file writes.
