# Commit Graph System

**Source file:** `Modules/graph.py`

`Modules/graph.py` provides ancestry helpers for commit traversal, branch comparison, and merge-base discovery. Leaf stores commits in `log.json`, but graph operations are easier after that list is converted into a dictionary keyed by commit ID.

## Commit Parent Model

Leaf supports both legacy single-parent metadata and modern multi-parent metadata:

- `parent` stores the first parent.
- `parents` stores all parents and is used for merge commits.

The graph helpers normalize these formats so other modules can work with a consistent parent list.

## Functions

### `commit_map(log)`

Converts the commit log list into a dictionary:

```python
{
    "commit-id": commit_metadata
}
```

This makes lookups faster and keeps traversal code simple.

### `commit_parents(commit)`

Returns a clean list of parent IDs for a commit. It prefers the `parents` list when present and falls back to the single `parent` value.

### `commit_chain(commit_id, cmap)`

Builds a full ancestry chain from a commit ID. It follows all parents breadth-first, skips missing IDs, and avoids revisiting commits.

This is used by log output and ancestry checks.

### `first_parent_chain(commit_id, cmap)`

Builds the first-parent chain only. Rebuild uses this function so file state follows the mainline sequence of commits.

### `is_ancestor(ancestor_id, commit_id, cmap)`

Returns whether one commit appears in another commit’s ancestry. This supports merge decisions such as already-up-to-date and fast-forward checks.

### `find_merge_base(left_id, right_id, cmap)`

Finds a common ancestor between two commits. Merge uses this base commit to compare target branch changes with source branch changes during three-way merge.

## Merge Relevance

```text
base commit
   ├── current branch commit
   └── source branch commit
```

Leaf rebuilds all three states, compares each file, and either produces a clean merged file or writes conflict markers.
