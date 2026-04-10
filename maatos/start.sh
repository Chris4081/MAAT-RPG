#!/usr/bin/env bash
set -euo pipefail

echo "🌿 MAAT-RPG wird gestartet …"

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_SUPPORT_DIR="$HOME/Library/Application Support/MAAT-RPG"
ENV_DIR="$APP_SUPPORT_DIR/mos-env"

mkdir -p "$APP_SUPPORT_DIR"

if [ ! -d "$ENV_DIR" ]; then
    echo "⚠️ Keine Installation gefunden."
    read -p "Spiel jetzt installieren? [j/n]: " a
    if [[ "$a" != "j" && "$a" != "J" ]]; then
        exit 0
    fi
    bash "$BASE_DIR/setup.sh" || exit 1
fi

if [ ! -f "$ENV_DIR/bin/activate" ]; then
    echo "❌ Environment ist unvollständig oder beschädigt:"
    echo "   $ENV_DIR"
    echo "👉 Bitte setup.sh erneut ausführen."
    exit 1
fi

source "$ENV_DIR/bin/activate" || exit 1
cd "$BASE_DIR" || exit 1

echo "🧪 Starte Systemdiagnose…"
python3 - <<'EOF'
import importlib.util
import os
import platform
import sys

arch = platform.machine()
print(f"   Python: {sys.version.split()[0]}")
print(f"   Architektur: {arch}")

required = {
    "colorama": importlib.util.find_spec("colorama") is not None,
    "yaml": importlib.util.find_spec("yaml") is not None,
}
for name, ok in required.items():
    print(f"   {name}: {'ok' if ok else 'fehlt'}")
    if not ok:
        raise SystemExit(1)

llama_ok = importlib.util.find_spec("llama_cpp") is not None
mlx_ok = importlib.util.find_spec("mlx_lm") is not None
print(f"   llama_cpp: {'ok' if llama_ok else 'fehlt'}")
if arch == "arm64":
    print(f"   mlx_lm: {'ok' if mlx_ok else 'fehlt'}")

if not llama_ok and not (arch == "arm64" and mlx_ok):
    print("❌ Kein nutzbares LLM-Backend gefunden.")
    raise SystemExit(1)

app_support = os.path.expanduser("~/Library/Application Support/MAAT-RPG")
models_dir = os.path.join(app_support, "models")
if not os.path.isdir(models_dir):
    print(f"⚠️ Modellordner fehlt noch: {models_dir}")
else:
    print(f"   Modelle: {models_dir}")
EOF

python3 maatki.py
