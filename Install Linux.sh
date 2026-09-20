#!/usr/bin/env bash
set -euo pipefail
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -n "${MAAT_SETUP_PYTHON:-}" ]]; then
    exec "$MAAT_SETUP_PYTHON" "$BASE_DIR/packaging/linux/setup_linux.py" "$@"
fi
for candidate in python3.12 python3.11 python3.10 python3.13 python3; do
    if "$candidate" -c 'import sys; sys.exit(not ((3,10) <= sys.version_info[:2] < (3,14)))' 2>/dev/null; then
        exec "$candidate" "$BASE_DIR/packaging/linux/setup_linux.py" "$@"
    fi
done
printf '%s\n' 'Python 3.10–3.13 wird benötigt / Python 3.10–3.13 is required.' \
    'Ubuntu: sudo apt install python3 python3-venv python3-dev' \
    'Anderen Interpreter wählen / Choose interpreter: MAAT_SETUP_PYTHON=python3.12 bash "Install Linux.sh"' >&2
exit 1
