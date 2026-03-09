AMR Warehouse Simulation 
本项目是一个基于 ROS2 Jazzy 和 Gazebo Harmonic 的自主移动机器人（AMR）仿真系统，专注于窄道场景的视觉导航。
目前已实现完整的 感知 → 决策 → 控制闭环：
机器人通过摄像头识别红色障碍物，并根据障碍物距离实时调整运动状态（前进 / 转向 / 后退），实现自主绕障。


✅ 已完成功能（阶段一）

1. 仿真环境
窄道场景
worlds/narrow_aisle.world 包含两面墙壁和一个红色障碍物。
差速驱动机器人模型
models/my_robot.sdf 配备摄像头传感器，发布：
/model/my_robot/camera/image_raw
ROS-Gazebo 桥接
使用 ros_gz_bridge 将以下话题在 ROS2 与 Gazebo 之间双向转发：
图像
里程计
速度指令
一键启动仿真
launch/simulation.launch.py 启动：
Gazebo
机器人模型
ROS Bridge
RViz

2. 视觉感知节点 (detector_node.py)
功能：
订阅摄像头图像
使用 OpenCV + HSV 颜色空间检测红色障碍物
根据红色区域面积判断距离
发布三种状态：
状态	说明	面积阈值
CLEAR	无障碍物	< 3000
WARNING	发现障碍物	3000–12000
STOP	障碍物太近	> 12000
调试功能：
OpenCV 窗口显示识别框
实时显示当前状态
3. 智能决策节点 (agent_node.py)
订阅：
/obstacle_status
控制机器人速度：
/model/my_robot/cmd_vel
状态机逻辑
CLEAR
匀速前进
WARNING
减速
转向避障
STOP
后退
同时旋转
系统特点：
平滑速度插值（避免急转）
自动回正机制
适应窄道环境

4. 一键启动脚本 (scripts/run_sim.sh)
脚本自动执行：
编译 ROS2 工作空间
检测话题是否就绪
启动 Gazebo 仿真
启动感知节点
启动决策节点

特点：
自动检测 ROS2 话
并行启动节点
支持 Ctrl+C 优雅退出

5. 工程化结构
项目包含完整 ROS2 工程结构：
package.xml
setup.py
setup.cfg
参数文件 (config/)
文档 (docs/)
Git 忽略规则
Python 依赖 (requirements.txt)

📁 项目结构（关键部分）
amr_warehouse_sim/
│
├── launch/
│   ├── simulation.launch.py
│   └── start_all.launch.py
│
├── worlds/
│   └── narrow_aisle.world
│
├── models/
│   └── my_robot.sdf
│
├── amr_warehouse_sim/
│   ├── detector_node.py
│   └── agent_node.py
│
├── config/
│   ├── detector_params.yaml
│   └── agent_params.yaml
│
├── scripts/
│   ├── run_sim.sh
│   ├── setup.sh
│   └── stop_amr.sh
│
├── docker/
├── docs/
│
├── requirements.txt
└── README.md

🚀 快速开始
环境要求
Ubuntu 24.04
ROS2 Jazzy
Gazebo Harmonic
Python 3.10+
Python依赖：
OpenCV
NumPy

安装与运行
1 创建 ROS2 工作空间
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone <your-repo-url> amr_warehouse_sim
2 安装依赖（可选）
cd amr_warehouse_sim
chmod +x scripts/setup.sh
./scripts/setup.sh
3 编译工作空间
cd ~/ros2_ws
colcon build --packages-select amr_warehouse_sim
source install/setup.bash
4 一键启动演示
cd src/amr_warehouse_sim
./scripts/run_sim.sh

启动后：
Gazebo 打开窄道仿真
OpenCV 显示摄像头画面
终端输出状态切换
机器人自动前进并避障

手动启动（调试）
终端1：仿真
ros2 launch amr_warehouse_sim simulation.launch.py
终端2：感知
ros2 run amr_warehouse_sim detector_node
终端3：决策
ros2 run amr_warehouse_sim agent_node

📌 注意事项
话题名称
感知节点订阅：
/model/my_robot/camera/image_raw
控制节点发布：
/model/my_robot/cmd_vel
需与 bridge 配置一致。

Python 虚拟环境
如果使用虚拟环境：
~/ros2_venv
需在运行脚本前激活。
OpenCV GUI
cv2.imshow() 需要图形界面。
若在服务器运行，请注释相关代码。



🚧 阶段二规划
当前完成 阶段一：视觉避障闭环
计划扩展：
1 Nav2 集成
替换简单 Agent，实现：
全局路径规划
动态避障

2 完整仓库环境
新增：
worlds/warehouse_full.world
包含：
货架
立柱
多机器人

3 CAD 地图生成
开发：
cad_to_map.py
支持：
DXF → ROS Occupancy Grid

4 Docker 容器化
完善：
docker/
实现：
一键容器部署。

5 多机器人调度

在：
task_manager/
实现：
WMS任务分发
多机器人协作

📝 项目说明

本项目为 个人机器人软件工程作品，展示了完整的 ROS2 开发流程：

仿真环境搭建
视觉感知
状态机决策
机器人控制
工程化部署

所有代码已在：

Ubuntu 24.04
ROS2 Jazzy
Gazebo Harmonic
环境测试通过。
如有问题欢迎提交 GitHub Issues。

最后更新
2026-03-09
