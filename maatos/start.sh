#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_SUPPORT_DIR="$HOME/Library/Application Support/MAAT-RPG"
ENV_DIR="$APP_SUPPORT_DIR/mos-env"
STATE_DIR="$APP_SUPPORT_DIR/state"
SETTINGS_FILE="$STATE_DIR/settings_state.json"

mkdir -p "$APP_SUPPORT_DIR"

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

t "🌿 MAAT-RPG wird gestartet …" "🌿 MAAT-RPG is starting …"

if [ ! -d "$ENV_DIR" ]; then
    t "⚠️ Keine Installation gefunden." "⚠️ No installation was found."
    if [[ "$LANGUAGE" == "en" ]]; then
        read -r -p "Install the game now? [y/n]: " a
    else
        read -r -p "Spiel jetzt installieren? [j/n] (Install now? [y/n]): " a
    fi
    a="$(printf '%s' "$a" | tr '[:upper:]' '[:lower:]')"
    if [[ "$a" != "j" && "$a" != "y" ]]; then
        exit 0
    fi
    bash "$BASE_DIR/setup.sh" || exit 1
fi

if [ ! -f "$ENV_DIR/bin/activate" ]; then
    t "❌ Environment ist unvollständig oder beschädigt:" "❌ The environment is incomplete or damaged:"
    echo "   $ENV_DIR"
    t "👉 Bitte setup.sh erneut ausführen." "👉 Please run setup.sh again."
    exit 1
fi

source "$ENV_DIR/bin/activate" || exit 1
cd "$BASE_DIR" || exit 1

t "🧪 Starte Systemdiagnose…" "🧪 Starting system diagnostics…"
PY_LANG="$LANGUAGE" python3 - <<'EOF'
import importlib.util
import os
import platform
import sys

arch = platform.machine()
lang = os.environ.get("PY_LANG", "de")

def label(de, en):
    return en if lang == "en" else de

print(f"   Python: {sys.version.split()[0]}")
print(f"   {label('Architektur', 'Architecture')}: {arch}")

required = {
    "colorama": importlib.util.find_spec("colorama") is not None,
    "yaml": importlib.util.find_spec("yaml") is not None,
}
for name, ok in required.items():
    print(f"   {name}: {'ok' if ok else label('fehlt', 'missing')}")
    if not ok:
        raise SystemExit(1)

llama_ok = importlib.util.find_spec("llama_cpp") is not None
mlx_ok = importlib.util.find_spec("mlx_lm") is not None
print(f"   llama_cpp: {'ok' if llama_ok else label('fehlt', 'missing')}")
if arch == "arm64":
    print(f"   mlx_lm: {'ok' if mlx_ok else label('fehlt', 'missing')}")

if not llama_ok and not (arch == "arm64" and mlx_ok):
    print(label("❌ Kein nutzbares LLM-Backend gefunden.", "❌ No usable LLM backend was found."))
    raise SystemExit(1)

app_support = os.path.expanduser("~/Library/Application Support/MAAT-RPG")
models_dir = os.path.join(app_support, "models")
if not os.path.isdir(models_dir):
    print(label(f"⚠️ Modellordner fehlt noch: {models_dir}", f"⚠️ Models folder is still missing: {models_dir}"))
else:
    print(label(f"   Modelle: {models_dir}", f"   Models: {models_dir}"))
EOF

python3 maatki.py
