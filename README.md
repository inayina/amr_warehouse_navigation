# AMR Warehouse Simulation

基于 ROS 2 Jazzy 和 Gazebo Harmonic 的 AMR 仓库建图与导航仿真项目。

当前 **V1：AMR 仿真建图最小闭环** 已完成，当前主线已经进入并稳定在 **V2：Nav2 导航与路径执行**。

最后更新：2026-04-26

## 当前功能

- Gazebo 仓库世界：`worlds/warehouse_full.world`
- 差速 AMR 模型：`models/my_robot/model.sdf`
- RViz 可视化模型：`models/my_robot_visual.urdf`
- ROS-Gazebo bridge：`/cmd_vel`、`/odom`、`/scan`、`/clock`
- LaserScan 滤波：`laser_filters` 将 `/scan` 处理为 `/scan_filtered`
- TF 修正节点：`odom_tf_node`
- SLAM Toolbox 在线建图，订阅 `/scan_filtered`，`slam.launch.py` 会自动 configure / activate
- Nav2 导航入口：`navigation.launch.py` 使用 `maps/warehouse.yaml` 和 `config/nav2_params.yaml`
- RViz 配置：`rviz/slam.rviz` 用于建图，`rviz/nav2.rviz` 用于导航
- 已保存地图：`maps/warehouse.yaml`、`maps/warehouse_slam.pgm`
- 当前阶段：以 `navigation.launch.py` + `config/nav2_params.yaml` 作为 V2 稳定基线；下一步是在此基础上整理任务点与 WMS 前置条件

## 环境要求

- Ubuntu 24.04
- ROS 2 Jazzy
- Gazebo Harmonic
- `ros-jazzy-ros-gz`
- `ros-jazzy-laser-filters`
- `ros-jazzy-slam-toolbox`
- `ros-jazzy-robot-state-publisher`
- `ros-jazzy-rviz2`
- `ros-jazzy-teleop-twist-keyboard`
- `ros-jazzy-tf2-tools`
- V2 Nav2 需要：`ros-jazzy-navigation2`、`ros-jazzy-nav2-bringup`
- 一键脚本依赖：`tmux`

## 编译

推荐从工作空间根目录编译：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select amr_warehouse_sim
source install/setup.bash
```

机器人现在直接写入 `worlds/warehouse_full.world`，Gazebo 打开世界时就会加载 `my_robot`。

默认出生点：

```text
x = 0.0, y = 0.0, z = 0.0
```

如果需要修改出生点，改 `worlds/warehouse_full.world` 中 `model://my_robot` 的 `<pose>`。

## 测试

仓库现在提供了一个正式的 `test/` 目录，并按更贴近机器人项目实践的层次组织：

- `test/data/`：地图、YAML、Nav2 参数等静态配置回归
- `test/functional/`：launch 和功能入口 smoke test
- `test/integration/`：当前已包含导航链路契约测试，后续继续扩展到 topic、TF、lifecycle 链路验证
- `test/scenarios/`：当前已包含短距离导航和重启后 relocalization 的场景 spec，后续继续扩展到端到端回归

快速运行：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
pytest test -q
```

如果想按 ROS 2 工作空间方式执行：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon test --packages-select amr_warehouse_sim
colcon test-result --verbose
```

当前已经落地的是：

- `data`：地图和 Nav2 参数回归
- `functional`：主 launch smoke test
- `integration`：V2 导航链路契约测试
- `scenarios`：短距离导航和重启后 relocalization 场景 spec

`test/README.md` 里也写了后续如何继续扩展到 `launch_testing`、runtime integration 和真机回归测试。

如果想分阶段恢复拦车，不要直接改当前稳定基线 `config/nav2_params.yaml`。仓库另外提供了一份阶段 1 候选参数：

```text
config/nav2_params_collision_monitor_stage1.yaml
```

这份配置会先启用一个前向 `stop` polygon 和 `/scan_filtered` 检测，适合在仿真里做第一轮误拦车验证；默认主线仍保持关闭拦车项的稳定基线。

## 文档

- 设计说明：[docs/design.md](docs/design.md)
- 未来架构方向：[docs/future_architecture.md](docs/future_architecture.md)
- 项目路线图：[docs/roadmap.md](docs/roadmap.md)
- 排障记录：[docs/troubleshooting.md](docs/troubleshooting.md)
- 中英文简历要点：[docs/resume-bullets.md](docs/resume-bullets.md)
- 测试报告模板：[docs/test-report-template.md](docs/test-report-template.md)
- `collision_monitor` stage1 实验记录：[docs/collision_monitor_stage1_test_report.md](docs/collision_monitor_stage1_test_report.md)

## 推荐启动：V2 Nav2 稳定基线

当前默认主线入口是：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch amr_warehouse_sim navigation.launch.py
```

这个 launch 会启动：

- Gazebo 仓库世界和 `my_robot`
- ROS-Gazebo bridge
- `laser_filters`，输出 `/scan_filtered`
- `robot_state_publisher`
- Nav2 bringup，读取 `maps/warehouse.yaml` 和 `config/nav2_params.yaml`
- `rviz/nav2.rviz`

启动后按这个顺序做：

1. 等 `map_server`、`amcl`、`planner_server`、`controller_server`、`bt_navigator` 进入 `active`
2. 在 RViz 中点击 `2D Pose Estimate` 设置初始位姿
3. 发送 1~2 m 的短距离 `Nav2 Goal`
4. 观察 `/cmd_vel`、local/global costmap 和机器人运动

当前仓库已经完成多次短距离 goal 稳定测试，当前 `navigation.launch.py` + `config/nav2_params.yaml` 可视为一版可复现的 Nav2 稳定基线。后续如果要接 WMS，应优先复用这版导航参数，不要一开始就同时改导航和任务层。

## Nav2 最小验证

主 launch 启动后，建议至少检查一次：

```bash
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
ros2 lifecycle get /planner_server
ros2 lifecycle get /controller_server
ros2 lifecycle get /bt_navigator
ros2 topic echo /map --once
ros2 topic echo /scan_filtered --once
ros2 run tf2_ros tf2_echo map odom
```

当前建议的通过标准：

- `/map` 正常发布
- `map -> odom -> base_link` TF 连通
- RViz 中 RobotModel、LaserScan、Map、Costmap 显示一致
- 短距离 goal 发出后机器人能稳定输出 `/cmd_vel` 并完成移动

建议至少做以下重复验证后，再认为当前导航可作为后续功能的基础：

- 多次 1~2 m 短距离点到点 goal 能重复成功
- 通道内路径不过度切角，不明显贴墙或贴货架
- recovery 不频繁触发，`Failed to make progress` 不再是常见现象
- 重新启动 `navigation.launch.py` 后仍能复现相同结果

## 一键脚本

Nav2 主线：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
./scripts/run_navigation.sh
```

SLAM 建图：

```bash
cd ~/ros2_ws/src/amr_warehouse_sim
./scripts/run_slam.sh
```

`run_navigation.sh` 会编译包、启动 `navigation.launch.py`，并打开 TF / lifecycle / topic 检查窗口。

如果缺少 `tmux`，请先安装后再使用一键脚本；否则建议直接按 README 中的原始 `ros2 launch ...` 命令启动。

## 地图与 localization 预检

当前 Nav2 推荐地图入口：

```text
maps/warehouse.yaml
```

该文件已经是 Nav2 `map_server` 可读取的 YAML + PGM 格式，当前指向：

```text
maps/warehouse_slam.pgm
```

地图文件说明：

- `maps/warehouse.yaml`：后续 Nav2 统一使用的稳定入口
- `maps/warehouse_slam.yaml`：SLAM 保存时生成的原始 YAML
- `maps/warehouse_slam.pgm`：SLAM 保存时生成的地图图像

先单独测试 Nav2 localization，命令要显式带当前主线参数文件：

```bash
ros2 launch nav2_bringup localization_launch.py \
  map:=$HOME/ros2_ws/src/amr_warehouse_sim/maps/warehouse.yaml \
  params_file:=$HOME/ros2_ws/src/amr_warehouse_sim/config/nav2_params.yaml \
  use_sim_time:=true
```

检查：

```bash
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
ros2 topic echo /map --once
ros2 run tf2_ros tf2_echo map odom
```

如果只想启动 Gazebo、机器人和 bridge，不启动 SLAM / Nav2 / RViz：

```bash
ros2 launch amr_warehouse_sim simulation.launch.py
```

## SLAM 建图入口（V1）

如果要回到 V1 建图链路：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch amr_warehouse_sim slam.launch.py
```

保存地图：

```bash
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap "{name: {data: '$HOME/ros2_ws/src/amr_warehouse_sim/maps/warehouse_slam'}}"
```

## 运动测试

启动后另开一个终端：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

也可以直接发一次速度指令：

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.0}}"
```

注意：不要长期保留 `ros2 topic pub -r ... /cmd_vel`，它会持续抢占键盘控制。测试完要 `Ctrl+C` 停掉。

## 建图建议

如果地图很乱，先不要扫全仓库。推荐从小范围闭环开始：

1. 干净重启仿真，让机器人回到原点。
2. 原地慢速转一圈，让雷达先看到周围。
3. 低速前进约 1m，再慢速转向。
4. 沿墙或货架边走，和障碍物保持约 0.5m 距离。
5. 尽量走小闭环，回到起点附近后再扩展范围。
6. 避免高速直冲、贴墙行驶、频繁乱转。

建议速度范围：

```text
linear x: 0.08 ~ 0.15 m/s
angular z: 0.25 ~ 0.45 rad/s
```

## V1 验证顺序

按 [docs/design.md](docs/design.md) 的 V1 排障顺序检查：

1. Gazebo 实体树中存在 `my_robot`。
2. Gazebo 画面中能看到机器人和红黄可视标记。
3. 发布 `/cmd_vel` 后机器人能运动。
4. `/scan` 存在并持续输出。
5. `/scan_filtered` 存在并持续输出。
6. TF 能连通 `odom -> base_link -> my_robot/lidar_link/lidar`。
7. `slam_toolbox` 订阅 `/scan_filtered` 并输出 `/map`，RViz 中地图随运动更新。

常用命令：

```bash
ros2 topic list | grep -E '^/scan$|^/scan_filtered$|cmd_vel|odom|tf|map'
ros2 topic echo /scan --once
ros2 topic echo /scan_filtered --once
ros2 topic echo /odom --once
ros2 lifecycle get /slam_toolbox
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo base_link my_robot/lidar_link/lidar
```

保存 TF 图：

```bash
ros2 run tf2_tools view_frames
```

## 关键 Nav2 参数

| 项目 | 当前主线配置 |
| --- | --- |
| 地图入口 | `maps/warehouse.yaml` |
| localization 激光输入 | `/scan_filtered` |
| 关键 TF | `map -> odom -> base_link -> my_robot/lidar_link/lidar` |
| 机器人 footprint | `[[0.28, 0.21], [0.28, -0.21], [-0.28, -0.21], [-0.28, 0.21]]` |
| 局部控制器 | `nav2_mppi_controller::MPPIController` |
| 全局规划器 | `nav2_navfn_planner::NavfnPlanner`（A*） |
| progress checker | `required_movement_radius: 0.10` |
| costmap inflation | local / global 均为 `0.40` |
| footprint 代价评估 | `consider_footprint: true` |
| collision monitor | 当前稳定基线中关闭 scan / FootprintApproach 拦车项 |
| 仿真时间 | `use_sim_time: true` |

## 面向机器人测试的补充说明

### 当前假设

- 机器人是差速底盘，控制话题为 `/cmd_vel`
- 真机可稳定提供 `/odom`、`/tf`、`/tf_static`
- 激光雷达原始输入为 `/scan`，经过滤波后供 Nav2 使用 `/scan_filtered`
- 雷达安装位姿与仿真接近：相对 `base_link` 约 `x=0.20, y=0.0, z=0.32`
- 当前地图和真机环境布局基本一致
- 真机测试时需要切换 `use_sim_time:=false`

### 已知限制

- 当前只验证单车导航
- 当前验证重点是静态地图和短距离 goal，不是完整任务系统
- 货架环境较对称，AMCL 对 initial pose 和 odom 质量比较敏感
- footprint 已按仿真模型外廓收敛，但真机仍应按实测尺寸复核
- 当前稳定基线为了先收敛导航，已关闭 `collision_monitor` 的 `scan` 和 `FootprintApproach` 拦车项；接 WMS 或真机前需要重新标定并恢复安全策略
- 如果要试开拦车，建议先从 `config/nav2_params_collision_monitor_stage1.yaml` 开始，而不是直接改当前稳定基线
- recovery、waypoint、docking 等扩展能力尚未做真机验证

### 接 WMS 前置条件

- 保留当前稳定版 `config/nav2_params.yaml` 作为导航基线
- 先定义一组固定任务点，并验证每个点位都能重复导航成功
- 明确任务层只下发 map 坐标点，不直接干预底层 `cmd_vel`
- 补上安全策略：重新评估 `collision_monitor`、或采用外部安全链，而不是在当前关闭状态下直接进入任务调度
- 再设计最小任务流：`待执行 -> 导航中 -> 到达 -> 失败`

### 建议准备的测试交付物

- 依赖版本：Ubuntu、ROS 2、Gazebo、Nav2 版本
- 启动命令：`navigation.launch.py` 和必要的预检命令
- 地图文件：`maps/warehouse.yaml`、`maps/warehouse_slam.pgm`
- `config/nav2_params.yaml` 当前测试版本
- RViz 截图：Map、LaserScan、Costmap、ParticleCloud、RobotModel
- TF 树图：`ros2 run tf2_tools view_frames`
- 一段 1~2 m 短距离导航视频或录屏

## 项目结构

```text
amr_warehouse_sim/
├── amr_warehouse_sim/
│   ├── __init__.py
│   └── odom_tf_node.py
├── config/
│   ├── laser_filters.yaml
│   ├── nav2_params.yaml
│   └── slam_toolbox.yaml
├── launch/
│   ├── navigation.launch.py
│   ├── simulation.launch.py
│   └── slam.launch.py
├── models/
│   ├── my_robot/
│   │   ├── model.config
│   │   └── model.sdf
│   └── my_robot_visual.urdf
├── worlds/
│   └── warehouse_full.world
├── rviz/
│   ├── nav2.rviz
│   └── slam.rviz
├── maps/
│   ├── warehouse.yaml
│   ├── warehouse_slam.yaml
│   └── warehouse_slam.pgm
├── scripts/
│   ├── run_navigation.sh
│   ├── run_slam.sh
│   └── setup.sh
├── test/
│   ├── data/
│   ├── functional/
│   ├── integration/
│   └── scenarios/
├── docs/
│   ├── design.md
│   ├── future_architecture.md
│   ├── resume-bullets.md
│   ├── roadmap.md
│   ├── test-report-template.md
│   └── troubleshooting.md
├── archive/
├── future_extensions/
│   ├── docker/
│   └── wms_integration/
├── AGENTS.md
└── README.md
```

说明：`build/`、`install/`、`log/` 是 `colcon` 生成目录，不属于源码结构。

## 归档说明

- `archive/`：历史试验与旧调试资料。
- `future_extensions/`：后续扩展与实验目录，不参与当前 V1 / V2 主线启动。
- `archive/nav2_legacy/`：旧 SLAM-Nav2 试验文件，已不作为当前 V2 入口。
- `future_extensions/wms_integration/`：测试用途的轻量 mock WMS 最小骨架，用于任务流演示与场景验证。
- 当前主线不从 `archive/` 或 `future_extensions/` 中加载任何代码。

## 清理重启

如果 Gazebo / RViz / bridge 状态混乱，可以先清理：

```bash
pkill -f "gz sim"
pkill -f "ros2 launch amr_warehouse_sim"
pkill -f "ros2 topic pub.*cmd_vel"
pkill -f slam_toolbox
pkill -f rviz2
pkill -f parameter_bridge
pkill -f scan_to_scan_filter_chain
pkill -f odom_tf_node
pkill -f robot_state_publisher
pkill -f static_transform_publisher
pkill -f teleop_twist_keyboard
pkill -f smoother_server
```

然后重新启动当前 Nav2 主线：

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch amr_warehouse_sim navigation.launch.py
```

如果要回到 V1 建图链路，再改为：

```bash
ros2 launch amr_warehouse_sim slam.launch.py
```
