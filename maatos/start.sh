#!/usr/bin/env bash

echo "🌿 MAAT-RPG wird gestartet …"

if [ ! -d "mos-env" ]; then
    echo "⚠️ Keine Installation gefunden."
    read -p "Spiel jetzt installieren? [j/n]: " a
    if [[ "$a" != "j" ]]; then
        exit 0
    fi
    bash setup.sh
fi

source mos-env/bin/activate
python3 maatki.py