#!/usr/bin/env bash
set -uo pipefail
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
bash "$BASE_DIR/setup.sh" "$@"
code=$?
if [[ "$code" != 0 && -t 0 ]]; then
    printf '\n%s\n' 'Setup nicht abgeschlossen / Setup incomplete. See the message above.'
    read -r -p 'Enter zum Schließen / Press Enter to close … ' || true
fi
exit "$code"
