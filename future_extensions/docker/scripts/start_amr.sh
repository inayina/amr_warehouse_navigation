#!/bin/bash
echo "🚀 正在启动 AMR 仓库仿真系统..."
# 1. 开启显示授权
xhost +local:docker > /dev/null
# 2. 启动容器
cd ~/Amr_warehouse_sim && docker compose up -d
# 3. 在容器内启动 ROS 2 Launch
echo "⏳ 等待环境初始化..."
sleep 2
docker exec -it amr_container bash -c "source /opt/ros/jazzy/setup.bash && ros2 launch /ros2_ws/src/amr_sim/launch/bringup.launch.py"
