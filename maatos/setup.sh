#!/usr/bin/env bash
set -euo pipefail
clear

# -------------------------------------------------
# Pfade
# -------------------------------------------------
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR" || exit 1

APP_SUPPORT_DIR="$HOME/Library/Application Support/MAAT-RPG"
ENV_DIR="$APP_SUPPORT_DIR/mos-env"
REQ_BASE="$BASE_DIR/requirements.base.txt"
REQ_INTEL="$BASE_DIR/requirements.intel.txt"
REQ_ARM="$BASE_DIR/requirements.arm.txt"

mkdir -p "$APP_SUPPORT_DIR" || exit 1

detect_language() {
python3 - <<'PY'
from pathlib import Path
import json
import locale
path = Path.home() / "Library" / "Application Support" / "MAAT-RPG" / "state" / "settings_state.json"
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

t "🌿 MAAT-RPG Setup" "🌿 MAAT-RPG Setup"
echo "-----------------"

# -------------------------------------------------
# Xcode Command Line Tools Check
# -------------------------------------------------
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

if ! clang --version >/dev/null 2>&1; then
    t "❌ clang ist nicht nutzbar." "❌ clang is not usable."
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

# -------------------------------------------------
# Python Check
# -------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
    t "❌ Python 3 nicht gefunden." "❌ Python 3 was not found."
    t "👉 Bitte installiere Python von:" "👉 Please install Python from:"
    echo "https://www.python.org/downloads/macos/"
    exit 1
fi

echo "🐍 Python: $(python3 --version)"

if [[ "$LANGUAGE" == "en" ]]; then
    PY_LANG="en"
else
    PY_LANG="de"
fi

t "🔎 Prüfe Python-Version…" "🔎 Checking Python version…"
PY_LANG="$PY_LANG" python3 - <<'EOF'
import sys
import os
major, minor = sys.version_info[:2]
lang = os.environ.get("PY_LANG", "de")
if (major, minor) < (3, 10):
    print("❌ Python 3.10 or newer is required." if lang == "en" else "❌ Python 3.10 oder neuer wird benötigt.")
    raise SystemExit(1)
print(f"✅ Python version ok: {major}.{minor}" if lang == "en" else f"✅ Python-Version ok: {major}.{minor}")
EOF

# -------------------------------------------------
# Architektur erkennen
# -------------------------------------------------
ARCH="$(uname -m)"
t "🧠 Architektur: $ARCH" "🧠 Architecture: $ARCH"

IS_ARM=false
if [[ "$ARCH" == "arm64" ]]; then
    IS_ARM=true
fi

# -------------------------------------------------
# Virtual Environment
# -------------------------------------------------
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

# -------------------------------------------------
# pip Update
# -------------------------------------------------
t "⬆️  Aktualisiere pip…" "⬆️  Updating pip…"
pip install --upgrade pip setuptools wheel || exit 1

# -------------------------------------------------
# Requirements prüfen
# -------------------------------------------------
if [ ! -f "$REQ_BASE" ]; then
    t "❌ requirements.base.txt nicht gefunden!" "❌ requirements.base.txt not found!"
    t "📍 Erwartet in:" "📍 Expected at:"
    echo "   $REQ_BASE"
    exit 1
fi

# -------------------------------------------------
# Intel / ARM getrennte Installation
# -------------------------------------------------
t "📚 Installiere Abhängigkeiten…" "📚 Installing dependencies…"

if [ "$IS_ARM" = false ]; then
    t "⚠️ Intel-Mac erkannt → ARM-Zusatzpakete werden übersprungen" "⚠️ Intel Mac detected → ARM-only packages will be skipped"
    pip install -r "$REQ_INTEL" || exit 1
else
    t "🍏 Apple Silicon erkannt → ARM-Paketliste wird verwendet" "🍏 Apple Silicon detected → ARM package set will be used"
    pip install -r "$REQ_ARM" || exit 1
fi

# -------------------------------------------------
# Kurztest
# -------------------------------------------------
 t "🧪 Prüfe Installation…" "🧪 Checking installation…"
PY_LANG="$PY_LANG" python3 - <<EOF
import os
try:
    import colorama
    import yaml
    print("✅ Base packages installed" if os.environ.get("PY_LANG") == "en" else "✅ Basis-Pakete installiert")
except ImportError:
    print("❌ Base packages are missing – installation is incomplete" if os.environ.get("PY_LANG") == "en" else "❌ Basis-Pakete fehlen – Installation unvollständig")
    raise SystemExit(1)
EOF

 t "🧠 Prüfe verfügbare Backends…" "🧠 Checking available backends…"
PY_LANG="$PY_LANG" python3 - <<'EOF'
import platform
import importlib.util
import os

arch = platform.machine()
checks = {
    "llama_cpp": importlib.util.find_spec("llama_cpp") is not None,
    "mlx_lm": importlib.util.find_spec("mlx_lm") is not None,
}
lang = os.environ.get("PY_LANG", "de")
print(f"   {'Architecture' if lang == 'en' else 'Architektur'}: {arch}")
print(f"   llama_cpp: {'ok' if checks['llama_cpp'] else ('missing' if lang == 'en' else 'fehlt')}")
if arch == "arm64":
    print(f"   mlx_lm: {'ok' if checks['mlx_lm'] else ('missing' if lang == 'en' else 'fehlt')}")

if not checks["llama_cpp"] and not (arch == "arm64" and checks["mlx_lm"]):
    if lang == "en":
        print("❌ No usable LLM backend was found.")
        print("   Installable backends for this build are: llama_cpp on all Macs, mlx_lm on Apple Silicon.")
    else:
        print("❌ Kein nutzbares LLM-Backend gefunden.")
        print("   Nutzbare Backends fuer diesen Build sind: llama_cpp auf allen Macs, mlx_lm auf Apple Silicon.")
    raise SystemExit(1)
EOF

# -------------------------------------------------
# Abschluss
# -------------------------------------------------
echo ""
t "✅ Installation abgeschlossen!" "✅ Installation complete!"
t "👉 MAAT-RPG startet jetzt…" "👉 MAAT-RPG is starting now…"
sleep 1

bash "$BASE_DIR/start.sh"
