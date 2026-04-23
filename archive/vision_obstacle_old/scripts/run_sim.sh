#!/bin/bash

# 获取当前脚本所在目录，并定位工作空间
WORKSPACE_DIR=$(cd "$(dirname "$0")/../../.." && pwd)

echo "--- 🤖 机器人自动驾驶系统：P14s 启动序列 ---"
echo "工作空间定位: $WORKSPACE_DIR"
cd "$WORKSPACE_DIR"

# 1. 定向编译
echo "[1/4] 正在编译 amr_warehouse_sim..."
# 加上 --event-handlers desktop_notification 可以在 P14s 右上角看到编译成功通知
colcon build --packages-select amr_warehouse_sim --symlink-install
if [ $? -ne 0 ]; then
    echo "❌ 编译失败，请检查代码！"
    exit 1
fi

# 核心：必须 source 系统和本地两个环境
source /opt/ros/jazzy/setup.bash  # 假设你用的是 Jazzy 或 Humble
source install/setup.bash

# 2. 启动仿真环境（后台运行）
echo "[2/4] 启动 Gazebo 仿真..."
# 使用 nohup 防止终端关闭导致仿真挂掉
ros2 launch amr_warehouse_sim simulation.launch.py &
SIM_PID=$!

echo "等待 ROS 2 话题激活 (Image & CmdVel)..."
# 循环检测两个关键话题，确保 Bridge 已经工作
until ros2 topic list | grep -q "/image_raw" && ros2 topic list | grep -q "/cmd_vel"; do
  echo -n "."
  sleep 1
done
echo " ✅ 检测到完整信号链路，继续启动！"

# 3. 启动感知节点（后台运行）
echo "[3/4] 启动视觉感知节点 (OpenCV)..."
ros2 run amr_warehouse_sim detection_node &
DET_PID=$!

# 4. 启动决策节点
echo "[4/4] 启动 Agent 决策节点..."
echo "💡 提示：小车现在应该开始自主绕障了。按 Ctrl+C 停止所有进程。"

# 增加退出保护：确保 Ctrl+C 时能杀掉所有后台子进程
trap "echo '正在清理后台进程...'; kill $SIM_PID $DET_PID 2>/dev/null; pkill -f 'gz sim'; exit" INT TERM EXIT

ros2 run amr_warehouse_sim agent_node