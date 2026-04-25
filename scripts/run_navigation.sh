#!/bin/bash

set -euo pipefail

# =========================
# AMR Nav2 一键启动脚本
# 适用于 ROS2 Jazzy
# =========================

# ---------- 配置 ----------
WORKSPACE=~/ros2_ws
PKG_NAME="amr_warehouse_sim"
LAUNCH_FILE="${LAUNCH_FILE:-navigation.launch.py}"

SESSION="nav2"

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "缺少依赖命令: $1"
        exit 1
    fi
}

# ---------- 0 加载 ROS2 ----------
echo "加载 ROS2 Jazzy 环境..."

if [ ! -f /opt/ros/jazzy/setup.bash ]; then
    echo "未找到 /opt/ros/jazzy/setup.bash，请先安装 ROS 2 Jazzy。"
    exit 1
fi

source /opt/ros/jazzy/setup.bash

require_cmd colcon
require_cmd tmux

if [ ! -d "$WORKSPACE/src/$PKG_NAME" ]; then
    echo "未找到工作空间包目录: $WORKSPACE/src/$PKG_NAME"
    exit 1
fi

# ---------- 1 清理旧 tmux ----------
tmux kill-session -t "$SESSION" 2>/dev/null || true

# ---------- 2 清理旧进程 ----------
echo "清理旧进程..."

pkill -f "gz sim"
pkill -f "ros2 launch amr_warehouse_sim"
pkill -f ros_gz_sim
pkill -f "ros2 topic pub.*cmd_vel"
pkill -f slam_toolbox
pkill -f rviz2
pkill -f parameter_bridge
pkill -f scan_to_scan_filter_chain
pkill -f odom_tf_node
pkill -f robot_state_publisher
pkill -f static_transform_publisher
pkill -f teleop_twist_keyboard
pkill -f map_server
pkill -f amcl
pkill -f controller_server
pkill -f planner_server
pkill -f smoother_server
pkill -f behavior_server
pkill -f bt_navigator
pkill -f waypoint_follower
pkill -f velocity_smoother
pkill -f lifecycle_manager

sleep 2

# ---------- 3 编译工程 ----------
cd "$WORKSPACE"

echo "编译软件包: $PKG_NAME"

colcon build --symlink-install --packages-select "$PKG_NAME"

# ---------- 4 source workspace ----------
source install/setup.bash

# ---------- 5 创建 tmux session ----------
tmux new-session -d -s $SESSION

# ---------- 窗口1 主 Launch ----------
tmux rename-window -t $SESSION:0 'Main_Launch'

tmux send-keys -t $SESSION:0 \
"source /opt/ros/jazzy/setup.bash && source $WORKSPACE/install/setup.bash && ros2 launch $PKG_NAME $LAUNCH_FILE" C-m

# ---------- 窗口2 TF监控 ----------
tmux new-window -t $SESSION:1 -n 'TF_Monitor'

tmux send-keys -t $SESSION:1 \
"source /opt/ros/jazzy/setup.bash && source $WORKSPACE/install/setup.bash && sleep 8 && ros2 run tf2_ros tf2_monitor" C-m

# ---------- 窗口3 Nav2状态 ----------
tmux new-window -t $SESSION:2 -n 'Nav2_Status'

tmux send-keys -t $SESSION:2 \
"source /opt/ros/jazzy/setup.bash && source $WORKSPACE/install/setup.bash && sleep 10 && watch -n 2 'ros2 lifecycle get /map_server; ros2 lifecycle get /amcl; ros2 lifecycle get /controller_server; ros2 lifecycle get /planner_server'" C-m

# ---------- 窗口4 topic监控 ----------
tmux new-window -t $SESSION:3 -n 'Topic_Check'

tmux send-keys -t $SESSION:3 \
"source /opt/ros/jazzy/setup.bash && source $WORKSPACE/install/setup.bash && watch -n 2 ros2 topic list" C-m

# ---------- 窗口5 TF树 ----------
tmux new-window -t $SESSION:4 -n 'TF_Tree'

tmux send-keys -t $SESSION:4 \
"source /opt/ros/jazzy/setup.bash && source $WORKSPACE/install/setup.bash && sleep 12 && ros2 run tf2_tools view_frames" C-m

# ---------- 6 ROS2环境检测 ----------
tmux new-window -t $SESSION:5 -n 'ROS2_Doctor'

tmux send-keys -t $SESSION:5 \
"source /opt/ros/jazzy/setup.bash && source $WORKSPACE/install/setup.bash && sleep 5 && ros2 doctor" C-m

# ---------- 7 进入 tmux ----------
echo ""
echo "=============================="
echo " AMR Nav2 启动完成"
echo "=============================="
echo ""
echo "tmux 窗口:"
echo "0 Main_Launch"
echo "1 TF_Monitor"
echo "2 Nav2_Status"
echo "3 Topic_Check"
echo "4 TF_Tree"
echo "5 ROS2_Doctor"
echo ""
echo "快捷键:"
echo "Ctrl+b 0~5 切换窗口"
echo "Ctrl+b d   退出tmux但程序继续运行"
echo ""

tmux attach-session -t $SESSION
