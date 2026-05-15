#!/usr/bin/env bash
set -euo pipefail

source /opt/ros/${ROS_DISTRO:-jazzy}/setup.bash

cd /workspaces/ros2_ws
colcon build --symlink-install --packages-select amr_warehouse_sim
