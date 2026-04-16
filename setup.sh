#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$BASE_DIR/MAAT RPG.app/Contents/Resources/maatos/setup.sh"

if [ ! -f "$TARGET" ]; then
    echo "❌ MAAT-RPG setup script not found:"
    echo "   $TARGET"
    exit 1
fi

exec bash "$TARGET" "$@"
