#!/bin/bash
# 模拟向机器人发送一个导航目标点
echo "📦 正在向 AMR 发送新任务..."
docker exec -it amr_container bash -c "source /opt/ros/jazzy/setup.bash && ros2 topic pub --once /goal_pose geometry_msgs/msg/PoseStamped '{header: {frame_id: \"map\"}, pose: {position: {x: 2.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}'"
