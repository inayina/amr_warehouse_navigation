#!/bin/bash
echo "🔍 正在检查机器人节点与话题状态..."
echo "--- 活跃节点 ---"
docker exec -it amr_container bash -c "source /opt/ros/jazzy/setup.bash && ros2 node list"
echo "--- 核心话题 ---"
docker exec -it amr_container bash -c "source /opt/ros/jazzy/setup.bash && ros2 topic list | grep -E 'scan|cmd_vel|odom|tf'"
