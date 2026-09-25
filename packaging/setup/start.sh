#!/usr/bin/env bash
set -euo pipefail
MAAT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MAAT_OS="$(uname -s)"
case "$MAAT_OS" in
    Darwin)
        if [[ "$(/usr/sbin/sysctl -n hw.optional.arm64 2>/dev/null || true)" == 1 && "$(uname -m)" != arm64 ]]; then
            exec /usr/bin/arch -arm64 /bin/bash "$0" "$@"
        fi
        MAAT_ENV="$MAAT_ROOT/.venv" ;;
    Linux) MAAT_ENV="${MAAT_GUI_DATA_ROOT:-${XDG_DATA_HOME:-$HOME/.local/share}/MAAT-RPG}/linux-env" ;;
    *) printf '%s\n' 'macOS/Linux only.' >&2; exit 1 ;;
esac
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
unset PYTHONHOME PYTHONPATH
if [[ -n "${MAAT_GUI_PYTHON:-}" ]]; then
    exec "$MAAT_GUI_PYTHON" "$MAAT_ROOT/packaging/setup/launch.py" "$@"
fi
if [[ ! -x "$MAAT_ENV/bin/python" ]] || ! "$MAAT_ENV/bin/python" -c 'import platform,sys
import PySide6,colorama,yaml,requests,numpy,jinja2,llama_cpp
normalize=lambda s:s.lower().replace("aarch64","arm64").replace("amd64","x86_64")
sys.exit(not ((3,10)<=sys.version_info[:2]<(3,14) and normalize(platform.machine())==normalize(sys.argv[1]) and llama_cpp.__version__=="0.3.34"))' "$(uname -m)" >/dev/null 2>&1; then
    printf '%s\n' 'Erster Start: Einrichtung nötig / First launch: setup required.'
    bash "$MAAT_ROOT/setup.sh" --no-start
fi
exec "$MAAT_ENV/bin/python" "$MAAT_ROOT/packaging/setup/launch.py" "$@"
