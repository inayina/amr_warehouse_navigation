#!/bin/bash
set -e

echo "安装系统依赖（ROS2 Jazzy + Gazebo Harmonic）..."
sudo apt update
sudo apt install -y ros-jazzy-desktop ros-jazzy-ros-gz ros-jazzy-rviz2 \
                    ros-jazzy-joint-state-publisher ros-jazzy-xacro \
                    python3-pip wget

echo "安装 Python 依赖（使用清华源）..."
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "下载 YOLOv8n 模型..."
mkdir -p models
if [ ! -f models/yolov8n.pt ]; then
    wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -O models/yolov8n.pt
fi

echo "✅ 安装完成！请运行 scripts/run_simulation.sh 启动仿真。"