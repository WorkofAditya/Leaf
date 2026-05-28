# HEAD System
**File:** HEAD
This file controls Leaf's current position inside repository history. It behaves similarly to Git's HEAD system but in a much simpler and easier-to-follow way.
## What HEAD Stores
Leaf stores two important values:
 1. Current commit ID
 2. Current branch name
These are saved in:
```text
.leaf/HEAD
.leaf/CURRENT_BRANCH
```
## Important Functions
### init_head()
Creates HEAD-related files during repository initialization. If the files do not exist, they are created automatically.
### read_head()
Reads the current commit ID. If no commit exists yet, it returns None.
### write_head()
Updates the current commit pointer. Whenever a new commit is saved, HEAD moves forward.
### read_current_branch()
Returns the active branch name. (Example: main)
### write_current_branch()
Updates the active branch. Used during branch switching.
## Why HEAD Matters
Without HEAD, Leaf would not know:
 * Which commit is active.
 * Where history continues from.
 * Which branch the user is currently using.
HEAD is basically Leaf's current memory position.
