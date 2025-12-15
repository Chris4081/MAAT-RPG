#!/usr/bin/env bash
clear

echo "🌿 MAAT-RPG Setup"
echo "-----------------"

# -------------------------------------------------
# Pfade
# -------------------------------------------------
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR" || exit 1

ENV_DIR="mos-env"
REQ_FILE="requirements.txt"

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
    python3 -m venv "$ENV_DIR" || exit 1
fi

echo "🔌 Aktiviere Environment…"
source "$ENV_DIR/bin/activate" || exit 1

# -------------------------------------------------
# pip Update
# -------------------------------------------------
echo "⬆️  Aktualisiere pip…"
pip install --upgrade pip setuptools wheel

# -------------------------------------------------
# Requirements prüfen
# -------------------------------------------------
if [ ! -f "$REQ_FILE" ]; then
    echo "❌ requirements.txt nicht gefunden!"
    echo "📍 Erwartet in: $BASE_DIR"
    exit 1
fi

# -------------------------------------------------
# Intel / ARM getrennte Installation
# -------------------------------------------------
echo "📚 Installiere Abhängigkeiten…"

if [ "$IS_ARM" = false ]; then
    echo "⚠️ Intel-Mac erkannt → mlx wird übersprungen"
    grep -v "mlx" "$REQ_FILE" > /tmp/requirements_no_mlx.txt
    pip install -r /tmp/requirements_no_mlx.txt || exit 1
else
    echo "🍏 Apple Silicon erkannt → mlx wird installiert"
    pip install -r "$REQ_FILE" || exit 1
fi

# -------------------------------------------------
# Abschluss
# -------------------------------------------------
echo ""
echo "✅ Installation abgeschlossen!"
echo "👉 MAAT-RPG startet jetzt…"
sleep 1

bash start.sh