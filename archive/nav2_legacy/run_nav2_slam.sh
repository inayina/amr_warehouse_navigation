#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export LAUNCH_FILE="nav2_slam.launch.py"

exec "$SCRIPT_DIR/run_slam.sh"
