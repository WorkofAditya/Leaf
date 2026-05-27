#!/bin/bash

set -e

if [ "$EUID" -ne 0 ]; then
    echo "🌿 Root permission required. Asking..."
    exec sudo bash "$0" "$@"
fi

REPO_URL="https://github.com/WorkofAditya/Leaf"
SCRIPT_DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR"
LEAF_FILE="leaf"
HEAD_FILE="HEAD"
LEAF_TARGET="/usr/local/bin/leaf"
HEAD_TARGET="/usr/local/bin/HEAD"

if [ ! -f "$SCRIPT_DIR/$LEAF_FILE" ] || [ ! -f "$SCRIPT_DIR/$HEAD_FILE" ]; then
    echo "🍂 Required files are missing or not together. Cloning from $REPO_URL..."
    TEMP_DIR="$(mktemp -d)"
    trap 'rm -rf "$TEMP_DIR"' EXIT

    git clone --depth 1 "$REPO_URL" "$TEMP_DIR/Leaf"
    SOURCE_DIR="$TEMP_DIR/Leaf"
fi

if [ ! -f "$SOURCE_DIR/$LEAF_FILE" ] || [ ! -f "$SOURCE_DIR/$HEAD_FILE" ]; then
    echo "❌ Could not find both '$LEAF_FILE' and '$HEAD_FILE'."
    exit 1
fi

install -m 755 "$SOURCE_DIR/$LEAF_FILE" "$LEAF_TARGET"
install -m 755 "$SOURCE_DIR/$HEAD_FILE" "$HEAD_TARGET"

echo '🌳 Tree is planted. You can now use "leaf" and "HEAD" commands.'

SCRIPT_PATH="$(realpath "$0")"
rm -f "$SCRIPT_PATH"
