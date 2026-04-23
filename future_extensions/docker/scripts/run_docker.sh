#!/bin/bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
colcon build --packages-select amr_warehouse_sim
source install/setup.bash
ros2 launch amr_warehouse_sim start_all.launch.py