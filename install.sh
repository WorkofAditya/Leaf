#!/bin/bash

set -e

REPO_URL="https://github.com/WorkofAditya/Leaf"
SCRIPT_DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR"
LEAF_FILE="leaf"
HEAD_FILE="HEAD"

if [ -n "$TERMUX_VERSION" ] || [ -d "/data/data/com.termux/files/usr" ]; then
    IS_TERMUX=true
    BIN_DIR="${PREFIX:-/data/data/com.termux/files/usr}/bin"
else
    IS_TERMUX=false
    BIN_DIR="/usr/local/bin"
fi

LEAF_TARGET="$BIN_DIR/leaf"
HEAD_TARGET="$BIN_DIR/HEAD"

if [ "$IS_TERMUX" = false ] && [ "$EUID" -ne 0 ]; then
    echo "🌿 Root permission required. Asking..."
    exec sudo bash "$0" "$@"
fi

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

mkdir -p "$BIN_DIR"
install -m 755 "$SOURCE_DIR/$LEAF_FILE" "$LEAF_TARGET"
install -m 755 "$SOURCE_DIR/$HEAD_FILE" "$HEAD_TARGET"

echo "🌳 Tree is planted. You can now use \"leaf\" and \"HEAD\" commands from $BIN_DIR."
