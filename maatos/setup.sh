#!/usr/bin/env bash
set -euo pipefail
clear

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR" || exit 1

detect_app_support_dir() {
BASE_DIR_ENV="$BASE_DIR" python3 - <<'PY'
import os
import sys

base_dir = os.environ["BASE_DIR_ENV"]
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from shared.core.maat_paths import get_app_support_dir

print(get_app_support_dir())
PY
}

APP_SUPPORT_DIR="${MAAT_APP_SUPPORT_DIR:-$(detect_app_support_dir)}"
export MAAT_APP_SUPPORT_DIR="$APP_SUPPORT_DIR"
export MAAT_DATA_DIR="$APP_SUPPORT_DIR/data"
export MAAT_MODELS_DIR="$APP_SUPPORT_DIR/models"
export MAAT_LOGS_DIR="$APP_SUPPORT_DIR/logs"
export MAAT_CACHE_DIR="$APP_SUPPORT_DIR/cache"
export MAAT_SAVES_DIR="$APP_SUPPORT_DIR/saves"

ENV_DIR="$APP_SUPPORT_DIR/mos-env"
REQ_BASE="$BASE_DIR/requirements.base.txt"
REQ_LINUX="$BASE_DIR/requirements.linux.txt"

mkdir -p "$APP_SUPPORT_DIR" || exit 1

detect_language() {
APP_SUPPORT_DIR_ENV="$APP_SUPPORT_DIR" python3 - <<'PY'
from pathlib import Path
import json
import locale
import os

path = Path(os.environ["APP_SUPPORT_DIR_ENV"]) / "state" / "settings_state.json"
try:
    data = json.loads(path.read_text(encoding="utf-8"))
    lang = data.get("language", "de")
    print("en" if lang == "en" else "de")
except Exception:
    loc = (locale.getdefaultlocale()[0] or "").lower()
    print("en" if loc.startswith("en") else "de")
PY
}

LANGUAGE="$(detect_language)"

t() {
    local de="$1"
    local en="$2"
    if [[ "$LANGUAGE" == "en" ]]; then
        printf '%s\n' "$en"
    else
        printf '%s\n' "$de"
    fi
}

OS_NAME="$(uname -s)"
ARCH="$(uname -m)"

t "🌿 MAAT-RPG Setup" "🌿 MAAT-RPG Setup"
echo "-----------------"
t "📁 App-Support: $APP_SUPPORT_DIR" "📁 App support: $APP_SUPPORT_DIR"
t "🧠 Architektur: $ARCH" "🧠 Architecture: $ARCH"
t "🖥️ Betriebssystem: $OS_NAME" "🖥️ Operating system: $OS_NAME"

check_macos_toolchain() {
    t "🔍 Prüfe Xcode Command Line Tools..." "🔍 Checking Xcode Command Line Tools..."

    if ! xcode-select -p >/dev/null 2>&1; then
        t "⚠️ Xcode Command Line Tools fehlen." "⚠️ Xcode Command Line Tools are missing."
        t "👉 Installation wird gestartet..." "👉 Starting installation..."
        xcode-select --install
        t "❗ Bitte Installation abschließen und danach Setup erneut starten." "❗ Please finish the installation and run setup again afterwards."
        exit 1
    fi

    if ! command -v clang >/dev/null 2>&1; then
        t "❌ clang Compiler fehlt!" "❌ clang compiler is missing!"
        t "👉 Bitte Xcode Command Line Tools installieren:" "👉 Please install Xcode Command Line Tools:"
        echo "   xcode-select --install"
        exit 1
    fi

    echo 'int main(){return 0;}' > /tmp/maat_test.c
    if ! clang /tmp/maat_test.c -o /tmp/maat_test_bin >/dev/null 2>&1; then
        t "❌ Compiler-Test fehlgeschlagen." "❌ Compiler test failed."
        t "👉 Bitte Xcode Command Line Tools prüfen oder neu installieren:" "👉 Please check or reinstall Xcode Command Line Tools:"
        echo "   xcode-select --install"
        rm -f /tmp/maat_test.c /tmp/maat_test_bin
        exit 1
    fi
    rm -f /tmp/maat_test.c /tmp/maat_test_bin

    t "✅ Xcode Tools bereit" "✅ Xcode tools ready"
}

check_linux_toolchain() {
    t "🔍 Prüfe Linux-Build-Umgebung..." "🔍 Checking Linux build environment..."

    if ! command -v gcc >/dev/null 2>&1 && ! command -v clang >/dev/null 2>&1; then
        t "❌ Weder gcc noch clang wurden gefunden." "❌ Neither gcc nor clang was found."
        t "👉 Installiere z. B.: build-essential oder clang" "👉 Install for example: build-essential or clang"
        exit 1
    fi

    if ! command -v cmake >/dev/null 2>&1; then
        t "❌ cmake fehlt." "❌ cmake is missing."
        t "👉 Bitte cmake installieren, sonst baut llama-cpp-python nicht stabil." "👉 Please install cmake, otherwise llama-cpp-python will not build reliably."
        exit 1
    fi

    if ! command -v make >/dev/null 2>&1; then
        t "❌ make fehlt." "❌ make is missing."
        t "👉 Bitte build-essential / make installieren." "👉 Please install build-essential / make."
        exit 1
    fi

    if ! command -v ffplay >/dev/null 2>&1 && ! command -v mpg123 >/dev/null 2>&1 && ! command -v aplay >/dev/null 2>&1; then
        t "⚠️ Kein Linux-Audio-Backend gefunden. Musik bleibt ohne ffplay, mpg123 oder aplay stumm." "⚠️ No Linux audio backend found. Music will stay silent without ffplay, mpg123 or aplay."
        t "👉 Empfehlung: ffmpeg (ffplay) oder mpg123 installieren." "👉 Recommendation: install ffmpeg (ffplay) or mpg123."
    fi

    if ! command -v spd-say >/dev/null 2>&1 && ! command -v espeak-ng >/dev/null 2>&1 && ! command -v espeak >/dev/null 2>&1; then
        t "⚠️ Kein Linux-TTS-Backend gefunden. /say bleibt ohne spd-say, espeak-ng oder espeak stumm." "⚠️ No Linux TTS backend found. /say will stay silent without spd-say, espeak-ng, or espeak."
        t "👉 Empfehlung: speech-dispatcher oder espeak-ng installieren." "👉 Recommendation: install speech-dispatcher or espeak-ng."
    fi

    t "✅ Linux-Build-Umgebung bereit" "✅ Linux build environment ready"
}

if ! command -v python3 >/dev/null 2>&1; then
    t "❌ Python 3 nicht gefunden." "❌ Python 3 was not found."
    exit 1
fi

echo "🐍 Python: $(python3 --version)"

t "🔎 Prüfe Python-Version…" "🔎 Checking Python version…"
PY_LANG="$LANGUAGE" python3 - <<'PY'
import os
import sys

major, minor = sys.version_info[:2]
lang = os.environ.get("PY_LANG", "de")
if (major, minor) < (3, 10):
    print("❌ Python 3.10 or newer is required." if lang == "en" else "❌ Python 3.10 oder neuer wird benötigt.")
    raise SystemExit(1)
print(f"✅ Python version ok: {major}.{minor}" if lang == "en" else f"✅ Python-Version ok: {major}.{minor}")
PY

case "$OS_NAME" in
    Darwin)
        check_macos_toolchain
        REQ_FILE="$REQ_BASE"
        ;;
    Linux)
        check_linux_toolchain
        REQ_FILE="$REQ_LINUX"
        ;;
    *)
        t "❌ Dieses Setup unterstützt aktuell nur macOS und Linux." "❌ This setup currently supports only macOS and Linux."
        exit 1
        ;;
esac

if [ ! -d "$ENV_DIR" ]; then
    t "📦 Erstelle virtuelles Environment…" "📦 Creating virtual environment…"
    t "📍 Ziel: $ENV_DIR" "📍 Target: $ENV_DIR"
    python3 -m venv "$ENV_DIR" || exit 1
fi

if [ ! -f "$ENV_DIR/bin/activate" ]; then
    t "❌ Environment konnte nicht korrekt erstellt werden:" "❌ Environment could not be created correctly:"
    echo "   $ENV_DIR"
    exit 1
fi

t "🔌 Aktiviere Environment…" "🔌 Activating environment…"
source "$ENV_DIR/bin/activate" || exit 1

t "⬆️  Aktualisiere pip…" "⬆️  Updating pip…"
pip install --upgrade pip setuptools wheel || exit 1

if [ ! -f "$REQ_FILE" ]; then
    t "❌ Requirements-Datei nicht gefunden!" "❌ Requirements file not found!"
    echo "   $REQ_FILE"
    exit 1
fi

t "📚 Installiere Abhängigkeiten…" "📚 Installing dependencies…"
pip install -r "$REQ_FILE" || exit 1

if [[ "$OS_NAME" == "Darwin" && "$ARCH" == "arm64" ]]; then
    t "🍏 Optional: pruefe mlx_lm fuer Apple Silicon…" "🍏 Optional: checking mlx_lm for Apple Silicon…"
    if pip install mlx_lm; then
        t "✅ mlx_lm installiert." "✅ mlx_lm installed."
    else
        t "⚠️ mlx_lm konnte nicht installiert werden. MAAT-RPG faellt auf llama.cpp zurueck." "⚠️ mlx_lm could not be installed. MAAT-RPG will fall back to llama.cpp."
    fi
fi

t "🧠 Optional: pruefe FAISS-Support…" "🧠 Optional: checking FAISS support…"
if pip install faiss-cpu==1.13.2; then
    t "✅ FAISS installiert." "✅ FAISS installed."
else
    t "⚠️ FAISS konnte nicht installiert werden. Memory v5/v6 nutzt den NumPy-Fallback." "⚠️ FAISS could not be installed. Memory v5/v6 will use the NumPy fallback."
fi

t "🧪 Prüfe Installation…" "🧪 Checking installation…"
PY_LANG="$LANGUAGE" PY_OS="$OS_NAME" python3 - <<'PY'
import importlib.util
import os
import platform

lang = os.environ.get("PY_LANG", "de")
os_name = os.environ.get("PY_OS", "")
arch = platform.machine()

def label(de, en):
    return en if lang == "en" else de

required = {
    "colorama": importlib.util.find_spec("colorama") is not None,
    "yaml": importlib.util.find_spec("yaml") is not None,
    "requests": importlib.util.find_spec("requests") is not None,
}

for name, ok in required.items():
    print(f"   {name}: {'ok' if ok else label('fehlt', 'missing')}")
    if not ok:
        raise SystemExit(1)

llama_ok = importlib.util.find_spec("llama_cpp") is not None
mlx_ok = importlib.util.find_spec("mlx_lm") is not None
print(f"   {label('Architektur', 'Architecture')}: {arch}")
print(f"   llama_cpp: {'ok' if llama_ok else label('fehlt', 'missing')}")
if os_name == "Darwin" and arch == "arm64":
    print(f"   mlx_lm: {'ok' if mlx_ok else label('optional fehlt', 'optional missing')}")

if not llama_ok and not (os_name == "Darwin" and arch == "arm64" and mlx_ok):
    print(label("❌ Kein nutzbares LLM-Backend gefunden.", "❌ No usable LLM backend was found."))
    raise SystemExit(1)
PY

echo ""
t "✅ Installation abgeschlossen!" "✅ Installation complete!"
t "👉 MAAT-RPG startet jetzt…" "👉 MAAT-RPG is starting now…"
sleep 1

bash "$BASE_DIR/start.sh"
