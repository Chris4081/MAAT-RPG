#!/usr/bin/env bash
# One entry point for the source folder and the original app-bundle layout.
set -euo pipefail
MAAT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MAAT_OS="$(uname -s)"
MAAT_ARCH="$(uname -m)"
MAAT_READ_ONLY=0
MAAT_SKIP_SYSTEM=0
for arg in "$@"; do
    case "$arg" in
        --help|-h)
            printf '%s\n' 'MAAT RPG · Automatisches Setup / Automatic setup' \
                'bash setup.sh [--no-start] [--skip-system-deps] [--rebuild-backend]' \
                '              [--no-shortcut] [--no-wiki] [--plan | --system-deps]' \
                'Standard: Voraussetzungen installieren, GUI einrichten und starten.' \
                'Default: install prerequisites, set up the GUI and start the game.' \
                '--plan / --system-deps: nur anzeigen / display only; no downloads or changes.'
            exit 0 ;;
        --plan|--system-deps) MAAT_READ_ONLY=1 ;;
        --skip-system-deps) MAAT_SKIP_SYSTEM=1 ;;
        --no-start|--rebuild-backend|--no-shortcut|--no-wiki) ;;
        *) printf 'Unbekannte Option / Unknown option: %s\n' "$arg" >&2; exit 2 ;;
    esac
done
case "$MAAT_OS" in
    Darwin)
        MAAT_MAC_VERSION="$(/usr/bin/sw_vers -productVersion)"
        IFS=. read -r MAAT_MAC_MAJOR MAAT_MAC_MINOR _ <<< "$MAAT_MAC_VERSION"
        if (( MAAT_MAC_MAJOR < 13 || (MAAT_MAC_MAJOR == 13 && MAAT_MAC_MINOR < 3) )); then
            printf '%s\n' 'macOS 13.3 oder neuer benötigt / macOS 13.3 or newer required.' >&2
            exit 1
        fi
        # A Finder terminal running under Rosetta must not create an Intel venv on ARM.
        if [[ "$(/usr/sbin/sysctl -n hw.optional.arm64 2>/dev/null || true)" == 1 ]]; then
            MAAT_ARCH=arm64
            if [[ "$(uname -m)" != arm64 ]]; then
                exec /usr/bin/arch -arm64 /bin/bash "$0" "$@"
            fi
        fi ;;
    Linux) ;;
    *) printf '%s\n' 'Dieses Setup unterstützt macOS und Linux / This setup supports macOS and Linux.' >&2; exit 1 ;;
esac
case "$MAAT_ARCH" in
    arm64|aarch64|x86_64|amd64) ;;
    *) printf '%s\n' '64-Bit Intel/AMD oder ARM benötigt / 64-bit Intel/AMD or ARM required.' >&2; exit 1 ;;
esac
if [[ "$MAAT_READ_ONLY" == 0 && "$(id -u)" == 0 ]]; then
    printf '%s\n' 'Ohne sudo starten; nur Systempakete fragen nach dem Passwort.' \
        'Run without sudo; only system packages request administrator privileges.' >&2
    exit 1
fi
export PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
unset PYTHONHOME PYTHONPATH

python_ok() {
    "$1" -c 'import platform,struct,sys,sysconfig,venv
expected=sys.argv[1].replace("aarch64","arm64").replace("amd64","x86_64")
actual=platform.machine().lower().replace("aarch64","arm64").replace("amd64","x86_64")
sys.exit(not ((3,10)<=sys.version_info[:2]<(3,14) and struct.calcsize("P")==8 and actual==expected and not sysconfig.get_config_var("Py_GIL_DISABLED")))' "$MAAT_ARCH" >/dev/null 2>&1
}
choose_python() {
    local candidate
    if [[ -n "${MAAT_SETUP_PYTHON:-}" ]]; then
        if python_ok "$MAAT_SETUP_PYTHON"; then printf '%s\n' "$MAAT_SETUP_PYTHON"; return 0; fi
        printf '%s\n' 'MAAT_SETUP_PYTHON: Python 3.10–3.13 in nativer Architektur benötigt / native architecture required.' >&2
        return 2
    fi
    for candidate in "$MAAT_ROOT/.venv/bin/python" python3.12 python3.11 python3.13 python3.10 python3 \
        /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12 \
        /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 \
        /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 \
        /Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11; do
        if python_ok "$candidate"; then printf '%s\n' "$candidate"; return 0; fi
    done
    return 1
}
MAAT_PYTHON="$(choose_python)" || {
    code=$?
    if [[ "$code" == 2 ]]; then exit 1; fi
    MAAT_PYTHON=""
}
if [[ -z "$MAAT_PYTHON" ]]; then
    if [[ "$MAAT_READ_ONLY" == 1 ]]; then
        printf '%s\n' "System: $MAAT_OS / $MAAT_ARCH" \
            'Python fehlt: wird beim Setup installiert / Missing Python will be installed by setup.' \
            'macOS: signiertes Python.org-Paket; Linux: Paketverwaltung der Distribution.' \
            'Danach / Then: GUI, natives GGUF-Backend, optional Offline-Wiki, Spielstart.'
        exit 0
    fi
    if [[ "$MAAT_SKIP_SYSTEM" == 1 ]]; then
        printf '%s\n' 'Python 3.10–3.13 fehlt / missing. Set MAAT_SETUP_PYTHON or run without --skip-system-deps.' >&2
        exit 1
    fi
    printf '%s\n' 'Python wird eingerichtet / Installing Python …'
    if [[ "$MAAT_OS" == Darwin ]]; then
        # Official PSF universal installer. Hash: Python.org release page (2026-08-05).
        MAAT_DOWNLOAD="$(mktemp -d "${TMPDIR:-/tmp}/maat-python.XXXXXX")"
        trap 'rm -f "$MAAT_DOWNLOAD/python.pkg"; rmdir "$MAAT_DOWNLOAD" 2>/dev/null || true' EXIT
        /usr/bin/curl --fail --location --proto '=https' --tlsv1.2 --retry 3 \
            https://www.python.org/ftp/python/3.13.15/python-3.13.15-macos11.pkg \
            --output "$MAAT_DOWNLOAD/python.pkg"
        MAAT_HASH="$(/usr/bin/shasum -a 256 "$MAAT_DOWNLOAD/python.pkg")"
        [[ "${MAAT_HASH%% *}" == 3b7eaf7f29825f796e8267024435540ddf1f17fc9a97ad58095daa7a75bfdcd3 ]] || {
            printf '%s\n' 'Python-Download beschädigt / Python download checksum mismatch.' >&2; exit 1;
        }
        /usr/sbin/pkgutil --check-signature "$MAAT_DOWNLOAD/python.pkg"
        /usr/sbin/spctl --assess --type install "$MAAT_DOWNLOAD/python.pkg"
        sudo /usr/sbin/installer -pkg "$MAAT_DOWNLOAD/python.pkg" -target /
    elif command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-venv python3-dev
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y python3 python3-pip python3-devel
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -S --needed --noconfirm python python-pip
    elif command -v zypper >/dev/null 2>&1; then
        sudo zypper --non-interactive install python312 python312-pip python312-devel
    else
        printf '%s\n' 'Bitte natives Python 3.10–3.13 installieren / Please install native Python 3.10–3.13.' >&2
        exit 1
    fi
    MAAT_PYTHON="$(choose_python)" || {
        printf '%s\n' 'Kein unterstütztes Python gefunden / No supported Python found. See SETUP.md.' >&2; exit 1;
    }
fi
if [[ "$MAAT_OS" == Darwin && -f /etc/ssl/cert.pem ]]; then
    # Python.org framework installations may not yet have run Install Certificates.command.
    export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/cert.pem}"
    export PIP_CERT="${PIP_CERT:-/etc/ssl/cert.pem}"
fi
# Do not exec here: the temporary-download cleanup trap must still run.
"$MAAT_PYTHON" "$MAAT_ROOT/packaging/setup/install.py" "$@"
