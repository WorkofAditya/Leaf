# Dynamic HEAD Loader

**Source file:** `Modules/head_utils.py`

`Modules/head_utils.py` dynamically imports the top-level `HEAD` file as a Python module. The project keeps HEAD-related behavior in a file named `HEAD`, which is not a conventional `.py` module name, so normal imports are not used.

## Why Dynamic Loading Is Needed

The top-level `HEAD` file contains functions for reading and writing `.leaf/HEAD` and `.leaf/CURRENT_BRANCH`. Because the file does not have a `.py` extension, Leaf loads it with `importlib` machinery instead of a standard `import HEAD` statement.

## Function

### `get_head_module()`

Loads and returns the HEAD helper module.

Behavior:

1. If the module has already been loaded, return the cached module.
2. Build a loader from `HEAD_MODULE_PATH`.
3. Create a module specification.
4. Execute the module.
5. Cache it for future calls.

## Why This Design Helps

- Keeps HEAD file operations isolated in one module.
- Avoids repeated loader setup.
- Allows regular Python modules to call HEAD helpers through one stable function.
- Supports the project’s intentionally simple top-level `HEAD` file layout.
