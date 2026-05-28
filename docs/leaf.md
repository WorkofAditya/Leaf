# CLI Entry Point
This file **leaf** is the starting point of the entire project. Whenever a user runs a command like:
```bash
leaf save "message"
```
This file receives the command and decides which internal function should run.
## What This File Does
The CLI file acts like a traffic controller. It:
 * Reads command line arguments.
 * Checks which command was used.
 * Forwards execution to the correct module.
 * Validates missing arguments.
### Main Function
#### def main():
This function reads sys.argv and routes commands such as:
 * init
 * save
 * log
 * restore
 * branch
 * checkout
 * merge
Each command maps to a function inside commands.py.
## Why This Design Matters
Keeping the CLI separated from the actual logic makes the project cleaner. The leaf file only handles user interaction, while the real repository behavior lives inside the modules.
