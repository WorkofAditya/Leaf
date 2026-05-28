# Storage System
**File:** Modules/storage.py
This module manages persistent repository data. It handles reading and writing JSON-based storage files.
## What This Module Stores
 * Commit logs
 * Branches
 * Branch sessions
 * Backup logs
## Important Functions
### safe_load_log()
Safely loads commit history. If the main log becomes corrupted, Leaf automatically falls back to a backup file. This improves repository safety.
### safe_save_log(log)
Saves commit history. Before overwriting the log, Leaf creates a backup copy.
### load_branches() / save_branches(branches)
Loads branch pointers from branches.json and writes updated branch information.
### load_sessions() / save_sessions(sessions)
Loads and stores temporary branch sessions. Sessions help preserve unfinished branch states.
## Why This Design Helps
Keeping storage operations isolated makes the rest of the project cleaner. Other modules do not need to worry about JSON parsing or backup handling; they simply call helper functions from this module.
