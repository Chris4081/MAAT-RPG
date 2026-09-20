#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ "$(uname -s)" == "Linux" ]]; then
    exec bash "$BASE_DIR/Install Linux.sh" "$@"
fi
TARGET="$BASE_DIR/maatos/setup.sh"

if [ ! -f "$TARGET" ]; then
    echo "❌ MAAT-RPG setup script not found:"
    echo "   $TARGET"
    exit 1
fi

exec bash "$TARGET" "$@"
