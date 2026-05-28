# Dynamic HEAD Loader
**File:** Modules/head_utils.py
This module dynamically loads the external HEAD file. Instead of importing HEAD normally, Leaf loads it manually using Python loaders.
## Why This Exists
The HEAD system is stored outside the normal module structure. This helper allows Leaf to:
 * Access HEAD functions safely.
 * Cache the loaded module.
 * Avoid repeated loading.
## Important Function
### get_head_module()
Loads the HEAD module only once. After loading, the module is cached in memory. Future calls reuse the same object. This improves performance and keeps the project organized.
