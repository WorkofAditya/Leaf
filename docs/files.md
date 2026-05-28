# File Management System
This module handles all file-related operations. Leaf depends heavily on this file because version control is ultimately about tracking files.
## Important Functions
### is_binary(path)
Checks whether a file is binary. Binary files are skipped during diff generation. This prevents corrupted text comparisons.
### leaf_read_file(path)
Reads a file safely. Returns file contents as lines.
### leaf_write_file(path, lines)
Writes content back into files. Also creates missing directories automatically.
### load_ignore()
Loads ignored paths. Leaf ignores .leaf, .git, cache folders, and compiled files. It also supports custom ignores via a .leafignore file.
### leaf_get_all_files()
Scans the working directory. Returns every trackable file. This function is heavily used during commits and rebuilds.
### leaf_snapshot()
Creates a full repository snapshot. Used only for the very first commit. Later commits switch to diff-based storage.
