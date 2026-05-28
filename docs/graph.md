# Commit Graph System
**File:** Modules/graph.py
This module handles commit relationships. It allows Leaf to understand parent chains and branch ancestry.
## Important Functions
### commit_map(log)
Converts commit history into a dictionary. This makes commit lookups faster.
### commit_chain(commit_id, cmap)
Builds the full parent chain for a commit. The function walks backward through history until no parent exists.
### is_ancestor(ancestor_id, commit_id, cmap)
Checks whether one commit exists inside another commit's history chain. This becomes important during merges and branch validation.
