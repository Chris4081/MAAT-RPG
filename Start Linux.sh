#!/usr/bin/env bash
set -euo pipefail
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="${MAAT_GUI_DATA_ROOT:-${XDG_DATA_HOME:-$HOME/.local/share}/MAAT-RPG}"
PYTHON_BIN="${MAAT_GUI_PYTHON:-$DATA_DIR/linux-env/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
    printf '%s\n' 'Bitte zuerst installieren / Please install first:' "bash \"$BASE_DIR/Install Linux.sh\"" >&2
    exit 1
fi
exec "$PYTHON_BIN" "$BASE_DIR/packaging/linux/launcher.py" "$@"
