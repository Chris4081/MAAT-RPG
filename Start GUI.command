#!/usr/bin/env bash
set -euo pipefail
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
exec bash "$BASE_DIR/packaging/setup/start.sh" "$@"
