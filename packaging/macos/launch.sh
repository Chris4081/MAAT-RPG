#!/bin/bash
# Standalone release launcher. Development starters remain unchanged.
set -eu
CONTENTS="$(cd "$(dirname "$0")/.." && pwd)"
RESOURCES="$CONTENTS/Resources"
GAME_ROOT="$RESOURCES/maatos"
if [ "$(/usr/bin/uname -m)" = 'arm64' ] || [ "$(/usr/sbin/sysctl -n hw.optional.arm64 2>/dev/null || true)" = '1' ]; then
    MAAT_ARCH=arm64
else
    MAAT_ARCH=x86_64
fi
if [ "${1:-}" = '--self-test' ] && [ -n "${MAAT_TEST_ARCH:-}" ]; then
    case "$MAAT_TEST_ARCH" in arm64|x86_64) MAAT_ARCH="$MAAT_TEST_ARCH" ;; *) exit 2 ;; esac
fi
PYTHON="$RESOURCES/runtimes/$MAAT_ARCH/bin/python3.11"
if [ "${1:-}" = '--runtime-info' ]; then
    printf 'MAAT RPG · %s\n%s\n' "$MAAT_ARCH" "$PYTHON"
    exit 0
fi
if [ ! -x "$PYTHON" ]; then
    /usr/bin/osascript -e 'display alert "MAAT RPG" message "Die Spielinstallation ist unvollständig. Bitte das MAAT-RPG-Setup erneut installieren. / The installation is incomplete. Please run MAAT-RPG Setup again."'
    exit 1
fi
unset PYTHONHOME
export PYTHONPATH="$GAME_ROOT:$RESOURCES/runtimes/common"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export PATH="/usr/bin:/bin:/usr/sbin:/sbin"
cd "$GAME_ROOT"
if [ "${1:-}" = '--self-test' ]; then
    shift
    exec "$PYTHON" "$RESOURCES/smoke_test.py" "$@"
fi
LOG_DIR="$HOME/Library/Logs/MAAT-RPG"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/start-$(date +%Y%m%d-%H%M%S).log"
if "$PYTHON" -m gui.desktop "$@" >"$LOG_FILE" 2>&1; then
    exit 0
else
    RESULT=$?
    /usr/bin/osascript - "$LOG_FILE" <<'APPLESCRIPT'
on run argv
    display alert "MAAT RPG konnte nicht starten / could not start" message ("Bitte das Spiel erneut öffnen. Das Diagnoseprotokoll liegt hier: / Please try again. Diagnostic log:\n\n" & item 1 of argv)
end run
APPLESCRIPT
    exit "$RESULT"
fi
