#!/bin/bash
cd "$(dirname "$0")"

# in /tools
cd ..

echo "🔍 MAAT PluginValidator startet…"
echo ""

python3 tools/validate_plugins.py

echo ""
echo "✨ Scan abgeschlossen."
read -n 1 -s -r -p "Zum Schließen eine Taste drücken…"