#!/usr/bin/env bash
set -euo pipefail
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"
# The repository and the Linux test archive each have their own GUI launcher.
# macOS continues through the original interpreter selection below.
if [[ "$(uname -s)" == "Linux" ]]; then
    for launch in "$BASE_DIR/../Start Linux.sh" "$BASE_DIR/../../../../Start Linux.sh"; do
        if [[ -f "$launch" ]]; then
            exec bash "$launch" "$@"
        fi
    done
fi
if [ -n "${MAAT_GUI_PYTHON:-}" ]; then
    exec "$MAAT_GUI_PYTHON" -m gui.desktop "$@"
fi
# Source/ZIP installs use the automatic GUI environment. Packaged apps without
# an outer setup keep the existing bundled/legacy interpreter lookup below.
for launch in "$BASE_DIR/../packaging/setup/start.sh" "$BASE_DIR/../../../../packaging/setup/start.sh"; do
    if [[ -f "$launch" ]]; then
        exec bash "$launch" "$@"
    fi
done
# Finder does not necessarily inherit the interactive shell's PATH.
for candidate in \
    "$BASE_DIR/../.venv/bin/python" \
    "${MAAT_APP_SUPPORT_DIR:-$HOME/Library/Application Support/MAAT-RPG}/mos-env/bin/python" \
    "${XDG_DATA_HOME:-$HOME/.local/share}/MAAT-RPG/mos-env/bin/python" \
    python3 python3.12 python3.11 \
    /opt/homebrew/bin/python3 /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3; do
    if "$candidate" -c 'import PySide6, colorama, yaml' >/dev/null 2>&1; then
        exec "$candidate" -m gui.desktop "$@"
    fi
done
printf '%s\n' 'MAAT GUI: Python mit PySide6, colorama und PyYAML fehlt. Bitte GUI-START.md lesen.' >&2
if command -v osascript >/dev/null 2>&1; then
    osascript -e 'display alert "MAAT RPG: GUI-Abhängigkeiten fehlen" message "Bitte installiere requirements-gui.txt wie in GUI-START.md beschrieben. Alternativ MAAT_GUI_PYTHON auf deinen Python-Interpreter setzen."'
fi
exit 1
