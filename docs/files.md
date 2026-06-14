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
- `.github`
- `.gitlab`
- `__pycache__`
- `*.pyc`
- `HEAD`
- `leaf`
- `Modules`

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

Copies every trackable file into the first commit directory. This is used only for snapshot commits, which provide the base state for later diff commits.

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
