# File Management System

**Source file:** `Modules/files.py`

`Modules/files.py` contains file-system helpers used by commit creation, status checks, rebuilds, and snapshots. Leaf tracks text files and avoids binary diffing.

## Responsibilities

- Detect binary files.
- Read text files into line arrays.
- Write line arrays back to disk.
- Load built-in and user-defined ignore rules.
- Discover trackable files in the working tree.
- Create the first full snapshot commit.

## Ignore Rules

Leaf always ignores internal or source-control infrastructure paths such as:

- `.leaf`
- `.git`
- `__pycache__`
- `*.pyc`

Project files such as `.github/`, `.gitlab/`, `HEAD`, `leaf`, and `Modules/` are not reserved by Leaf. They can be tracked like any other project content.

Users can add extra entries to `.leafignore`. Blank lines and comments beginning with `#` are skipped.

## Functions

### `is_binary(path)`

Reads the first chunk of a file and checks for null bytes. Files that cannot be read are treated as binary. Binary files are skipped by working-state capture and diff generation.

### `leaf_read_file(path)`

Reads a text file and returns a list of lines. If the file cannot be read, it returns an empty list. Leaf stores file contents as line arrays so `difflib` can calculate line-based diffs.

### `leaf_write_file(path, lines)`

Writes a list of lines to a file. Missing parent directories are created automatically.

### `load_ignore()`

Builds the ignore set from built-in defaults and `.leafignore` entries.

### `leaf_get_all_files()`

Walks the current directory and returns all trackable file paths. Directory names and file patterns from the ignore set are excluded.

### `leaf_snapshot(commit_path)`

Writes the captured text-file state into the first commit directory. It uses the same state captured for the commit, so binary and ignored files cannot slip into a snapshot.

## How File Discovery Fits Into Leaf

```text
Working directory
   │
   ├── load_ignore()
   ├── leaf_get_all_files()
   ├── is_binary(path)
   └── leaf_read_file(path)
           │
           ▼
   in-memory working state
```

That in-memory state is then compared against rebuilt commit state to produce commits, diffs, and status output.
