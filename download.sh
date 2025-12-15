#!/usr/bin/env bash
clear

# -------------------------------------------------
# Relativer Zielpfad (Ordner des Scripts)
# -------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$SCRIPT_DIR/MAAT-RPG"

URL="https://maat-research.com/data/downloads/MAAT-RPG.zip"

echo "🌿 MAAT-RPG Downloader"
echo "---------------------"
echo "Zielordner:"
echo "$TARGET"
echo ""

mkdir -p "$TARGET"
cd "$TARGET" || exit 1

echo "⬇️ Lade MAAT-RPG..."
curl -L "$URL" -o MAAT-RPG.zip

echo ""
echo "📦 Entpacke..."
unzip -o MAAT-RPG.zip

echo ""
echo "🧹 Aufräumen..."
rm MAAT-RPG.zip

echo ""
echo "✅ Fertig!"
echo "👉 MAAT-RPG.app liegt jetzt in:"
echo "$TARGET"
echo ""
read -p "Enter zum Beenden…"