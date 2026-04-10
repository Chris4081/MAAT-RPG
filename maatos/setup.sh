#!/usr/bin/env bash
set -euo pipefail
clear

echo "🌿 MAAT-RPG Setup"
echo "-----------------"

# -------------------------------------------------
# Pfade
# -------------------------------------------------
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR" || exit 1

APP_SUPPORT_DIR="$HOME/Library/Application Support/MAAT-RPG"
ENV_DIR="$APP_SUPPORT_DIR/mos-env"
REQ_FILE="$BASE_DIR/requirements.txt"

mkdir -p "$APP_SUPPORT_DIR" || exit 1

# -------------------------------------------------
# Xcode Command Line Tools Check
# -------------------------------------------------
echo "🔍 Prüfe Xcode Command Line Tools..."

if ! xcode-select -p >/dev/null 2>&1; then
    echo "⚠️ Xcode Command Line Tools fehlen."
    echo "👉 Installation wird gestartet..."
    xcode-select --install
    echo "❗ Bitte Installation abschließen und danach Setup erneut starten."
    exit 1
fi

if ! command -v clang >/dev/null 2>&1; then
    echo "❌ clang Compiler fehlt!"
    echo "👉 Bitte Xcode Command Line Tools installieren:"
    echo "   xcode-select --install"
    exit 1
fi

if ! clang --version >/dev/null 2>&1; then
    echo "❌ clang ist nicht nutzbar."
    exit 1
fi

echo 'int main(){return 0;}' > /tmp/maat_test.c
if ! clang /tmp/maat_test.c -o /tmp/maat_test_bin >/dev/null 2>&1; then
    echo "❌ Compiler-Test fehlgeschlagen."
    echo "👉 Bitte Xcode Command Line Tools prüfen oder neu installieren:"
    echo "   xcode-select --install"
    rm -f /tmp/maat_test.c /tmp/maat_test_bin
    exit 1
fi
rm -f /tmp/maat_test.c /tmp/maat_test_bin

echo "✅ Xcode Tools bereit"

# -------------------------------------------------
# Python Check
# -------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python 3 nicht gefunden."
    echo "👉 Bitte installiere Python von:"
    echo "https://www.python.org/downloads/macos/"
    exit 1
fi

echo "🐍 Python: $(python3 --version)"

echo "🔎 Prüfe Python-Version…"
python3 - <<'EOF'
import sys
major, minor = sys.version_info[:2]
if (major, minor) < (3, 10):
    print("❌ Python 3.10 oder neuer wird benötigt.")
    raise SystemExit(1)
print(f"✅ Python-Version ok: {major}.{minor}")
EOF

# -------------------------------------------------
# Architektur erkennen
# -------------------------------------------------
ARCH="$(uname -m)"
echo "🧠 Architektur: $ARCH"

IS_ARM=false
if [[ "$ARCH" == "arm64" ]]; then
    IS_ARM=true
fi

# -------------------------------------------------
# Virtual Environment
# -------------------------------------------------
if [ ! -d "$ENV_DIR" ]; then
    echo "📦 Erstelle virtuelles Environment…"
    echo "📍 Ziel: $ENV_DIR"
    python3 -m venv "$ENV_DIR" || exit 1
fi

if [ ! -f "$ENV_DIR/bin/activate" ]; then
    echo "❌ Environment konnte nicht korrekt erstellt werden:"
    echo "   $ENV_DIR"
    exit 1
fi

echo "🔌 Aktiviere Environment…"
source "$ENV_DIR/bin/activate" || exit 1

# -------------------------------------------------
# pip Update
# -------------------------------------------------
echo "⬆️  Aktualisiere pip…"
pip install --upgrade pip setuptools wheel || exit 1

# -------------------------------------------------
# Requirements prüfen
# -------------------------------------------------
if [ ! -f "$REQ_FILE" ]; then
    echo "❌ requirements.txt nicht gefunden!"
    echo "📍 Erwartet in: $REQ_FILE"
    exit 1
fi

# -------------------------------------------------
# Intel / ARM getrennte Installation
# -------------------------------------------------
echo "📚 Installiere Abhängigkeiten…"

if [ "$IS_ARM" = false ]; then
    echo "⚠️ Intel-Mac erkannt → mlx wird übersprungen"
    TMP_REQ="/tmp/requirements_no_mlx.txt"
    grep -vi "mlx" "$REQ_FILE" > "$TMP_REQ"
    pip install -r "$TMP_REQ" || exit 1
else
    echo "🍏 Apple Silicon erkannt → mlx wird installiert"
    pip install -r "$REQ_FILE" || exit 1
fi

# -------------------------------------------------
# Kurztest
# -------------------------------------------------
echo "🧪 Prüfe Installation…"
python3 - <<EOF
try:
    import colorama
    import yaml
    print("✅ Basis-Pakete installiert")
except ImportError:
    print("❌ Basis-Pakete fehlen – Installation unvollständig")
    raise SystemExit(1)
EOF

echo "🧠 Prüfe verfügbare Backends…"
python3 - <<'EOF'
import platform
import importlib.util

arch = platform.machine()
checks = {
    "llama_cpp": importlib.util.find_spec("llama_cpp") is not None,
    "mlx_lm": importlib.util.find_spec("mlx_lm") is not None,
}
print(f"   Architektur: {arch}")
print(f"   llama_cpp: {'ok' if checks['llama_cpp'] else 'fehlt'}")
if arch == "arm64":
    print(f"   mlx_lm: {'ok' if checks['mlx_lm'] else 'fehlt'}")

if not checks["llama_cpp"] and not (arch == "arm64" and checks["mlx_lm"]):
    print("❌ Kein nutzbares LLM-Backend gefunden.")
    raise SystemExit(1)
EOF

# -------------------------------------------------
# Abschluss
# -------------------------------------------------
echo ""
echo "✅ Installation abgeschlossen!"
echo "👉 MAAT-RPG startet jetzt…"
sleep 1

bash "$BASE_DIR/start.sh"
