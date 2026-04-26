#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${MODE:-dry-run}"

python3 "$SCRIPT_DIR/mock_wms_runner.py" --mode "$MODE" "$@"
