#!/bin/bash
set -e

echo "安装系统依赖（ROS2 Jazzy + Gazebo Harmonic）..."
sudo apt update
sudo apt install -y ros-jazzy-desktop ros-jazzy-ros-gz ros-jazzy-rviz2 \
                    ros-jazzy-slam-toolbox ros-jazzy-robot-state-publisher \
                    ros-jazzy-tf2-tools ros-jazzy-teleop-twist-keyboard \
                    python3-pip

echo "安装 Python 依赖（使用清华源）..."
if [ -s requirements.txt ]; then
    pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
fi

echo "✅ 安装完成！请运行 scripts/run_slam.sh 启动 V1 SLAM 主线。"
