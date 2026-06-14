# CLI Entry Point

**Source file:** `leaf`

The top-level `leaf` executable is the command-line entry point. It reads `sys.argv`, identifies the requested command, validates required arguments, and dispatches to functions in `Modules/commands.py`.

## Role in the Architecture

The CLI file is intentionally thin. It does not implement repository logic directly. Instead, it maps user commands to command-engine functions.

```text
Terminal command
   │
   ▼
leaf executable
   │
   ├── parse command name
   ├── validate basic arguments
   └── call Modules.commands function
```

## Command Dispatch

| CLI command | Function called |
| --- | --- |
| `leaf init` | `leaf_init()` |
| `leaf save <message>` | `leaf_save(message)` |
| `leaf add <path>` | `leaf_add(path)` |
| `leaf reset ...` | `leaf_reset(...)` |
| `leaf revert <commit>` | `leaf_revert(commit)` |
| `leaf log` | `leaf_log()` |
| `leaf restore <commit>` | `leaf_restore(commit)` |
| `leaf status` | `leaf_status()` |
| `leaf diff [commit]` | `leaf_diff(commit)` |
| `leaf ignore <path>` | `leaf_ignore(path)` |
| `leaf branch [name] [commit]` | `leaf_branch(name, commit)` |
| `leaf checkout <branch>` | `leaf_checkout(branch)` |
| `leaf merge <branch>` | `leaf_merge(branch)` |
| `leaf tag [name] [commit]` | `leaf_tag(name, commit)` |
| `leaf clone <path> [dest]` | `leaf_clone(source, dest)` |
| `leaf fsck` | `leaf_fsck()` |
| `leaf version` / `leaf v` / `leaf -v` | `leaf_version()` |
| `leaf help` / `leaf --help` / `leaf -h` | `leaf_help()` |

## Argument Handling

The entry point performs lightweight validation for commands that require values. For example, `restore`, `checkout`, `merge`, `clone`, and `revert` print a warning when the required commit, branch, or path argument is missing.

More detailed validation happens inside `Modules/commands.py`, where repository state is available.

## Disabled Commands

The CLI explicitly disables these commands:

- `remote`
- `fetch`
- `pull`
- `push`

When users run one of them, Leaf prints a message explaining that remote repository commands are currently disabled.

## Why This Design Matters

Keeping command parsing separate from repository behavior makes Leaf easier to maintain and test. The CLI stays small, while the command module owns repository state transitions.
