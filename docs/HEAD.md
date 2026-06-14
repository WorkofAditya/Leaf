# HEAD System

**Source file:** `HEAD`

The HEAD system records Leaf’s current position in repository history. It is split into two files inside `.leaf/`:

```text
.leaf/HEAD
.leaf/CURRENT_BRANCH
```

Together, these files tell Leaf whether the user is attached to a branch or directly viewing a commit.

## Stored Values

| File | Meaning |
| --- | --- |
| `.leaf/HEAD` | Current commit ID. |
| `.leaf/CURRENT_BRANCH` | Active branch name, or empty when detached. |

## Attached vs Detached HEAD

### Attached HEAD

When `.leaf/CURRENT_BRANCH` contains a branch name, Leaf treats the branch pointer as authoritative. New commits move the branch pointer and update `.leaf/HEAD` to the new commit ID.

```text
CURRENT_BRANCH = main
branches.json: main -> abc123
HEAD = abc123
```

### Detached HEAD

When `.leaf/CURRENT_BRANCH` is empty, Leaf uses `.leaf/HEAD` directly. Restoring a commit intentionally enters detached HEAD mode so branch pointers are not changed accidentally.

```text
CURRENT_BRANCH = ""
HEAD = def456
```

## Functions

### `head_file_path(vcs_dir)`

Returns the path to the repository’s `HEAD` file.

### `current_branch_path(vcs_dir)`

Returns the path to the repository’s `CURRENT_BRANCH` file.

### `init_head(vcs_dir)`

Creates missing HEAD metadata files. New repositories default `CURRENT_BRANCH` to `main`.

### `read_head(vcs_dir)`

Reads and returns the current commit ID. Empty or missing files return `None`.

### `write_head(vcs_dir, commit_id)`

Writes the current commit ID to `.leaf/HEAD`. Passing an empty value clears the file.

### `read_current_branch(vcs_dir)`

Reads and returns the active branch name. Empty or missing files return `None`.

### `write_current_branch(vcs_dir, branch_name)`

Writes the active branch name. Passing an empty value detaches HEAD.

### `resolve_head(vcs_dir, fallback_commit_id)`

Returns the current HEAD commit if it exists; otherwise returns the supplied fallback commit ID.

## Why HEAD Matters

HEAD tells Leaf:

- Which commit should be considered current.
- Whether commits should advance a branch pointer.
- Which history chain `leaf log` should display.
- What state should be rebuilt for status, diff, restore, checkout, and merge operations.
