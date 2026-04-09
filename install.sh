#!/bin/bash

set -e

if [ "$EUID" -ne 0 ]; then
    echo "🌿 Root permission required. Asking..."
    exec sudo bash "$0" "$@"
fi

FILE="leaf"
TARGET="/usr/local/bin/leaf"

if [ ! -f "$FILE" ]; then
    echo "🍂 Leaf file not found in current directory"
    exit 1
fi

chmod +x "$FILE"
mv "$FILE" "$TARGET"

echo '🌳 Tree is planted. You can now use "leaf" command.'

SCRIPT_PATH="$(realpath "$0")"
rm -f "$SCRIPT_PATH"
