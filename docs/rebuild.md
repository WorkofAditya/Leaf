# Repository Rebuild System

**Source file:** `Modules/rebuild.py`

The rebuild system reconstructs complete file states from commit history. It powers restore, diff, status comparisons, checkout, merge, revert, and clone.

## Core Idea

Leaf does not store every commit as a complete copy of the project. Instead:

1. The first commit stores a complete snapshot.
2. Later commits store line-based diffs and deleted-file lists.
3. Rebuild walks the first-parent chain from the first relevant commit to the requested commit.
4. Each snapshot or diff is applied to an in-memory file map.

## Rebuild Flow

```text
requested commit
      │
      ▼
first-parent chain
      │
      ▼
oldest commit → newest commit
      │
      ├── snapshot: copy full file contents into memory
      └── diff: apply additions/context lines and deletions
      │
      ▼
complete file state
```

## Functions

### `leaf_rebuild(commit_id, log)`

Returns a dictionary representing the repository files at a commit:

```python
{
    "path/to/file.txt": ["line 1\n", "line 2\n"]
}
```

Behavior:

- Returns `{}` when no commit ID is supplied.
- Builds a commit lookup map from `log`.
- Calculates the reversed first-parent chain.
- Loads snapshot files for snapshot commits.
- Removes files listed in each diff commit’s `deleted` field.
- Applies stored diff lines to reconstruct changed files.

### `write_working_tree(files)`

Writes a rebuilt file map into the project directory.

Behavior:

- Finds currently trackable files.
- Removes files that are no longer present in the target state.
- Creates missing directories.
- Writes each target file’s content.

## Important Limitations

- Rebuild follows the **first-parent chain**. Merge commits store multiple parents, but file reconstruction uses the mainline path for deterministic rebuild behavior.
- Leaf stores text content as lines. Binary files are skipped by the commit-state capture process.

## Commands That Depend on Rebuild

| Command | How rebuild is used |
| --- | --- |
| `leaf restore` | Recreates the selected commit and writes it to disk. |
| `leaf diff` | Compares rebuilt commit state with the working tree. |
| `leaf status` | Compares rebuilt HEAD state with current files. |
| `leaf checkout` | Writes branch state or saved session to disk. |
| `leaf merge` | Rebuilds base, target, and source commits. |
| `leaf revert` | Rebuilds before/after states for the reverted commit. |
| `leaf clone` | Rebuilds the cloned branch into the destination directory. |
