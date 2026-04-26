# AMR / SLAM 项目设计说明

## 1. 文档定位

本文件是当前 AMR 仓库仿真项目的设计与当前稳定基线文档，负责说明：

- 当前系统链路
- 当前已完成状态
- 地图文件与 Nav2 入口
- 当前主线的设计边界

未来路线图请看 `docs/roadmap.md`，未来扩展架构方向请看 `docs/future_architecture.md`。

AI / Coding Agent 的协作约束、修改边界和禁止事项统一放在仓库根目录 `AGENTS.md`，本文件不重复维护这些规则。

文档路径：

- 工作空间路径：`~/ros2_ws/src/amr_warehouse_sim/docs/design.md`
- 仓库相对路径：`docs/design.md`
- README 引用路径：`[docs/design.md](docs/design.md)`

---

## 2. 当前阶段状态

当前项目已经完成 **V1：AMR 仿真建图最小闭环**，并进入 **V2：Nav2 导航与路径执行稳定阶段**。

### V1 已完成

- Gazebo 中可以正常显示机器人
- 机器人可以响应 `/cmd_vel`
- `/scan` 可以稳定发布
- `laser_filters` 可以输出 `/scan_filtered`
- `/odom` 和 TF 链路正确
- `slam_toolbox` 可以输出 `/map`
- 已保存一版仓库地图

### 当前重点

当前重点不是继续修改 SLAM 主链路，而是冻结一版可复现的 Nav2 稳定基线，为后续任务点和 WMS 接入提供前置能力：

1. 确认地图文件可被 Nav2 `map_server` 读取
2. 建立定位链路：`map -> odom -> base_link`
3. 接入 AMCL 或 Nav2 localization
4. 稳定 planner / controller 的点到点导航表现
5. 在稳定导航基础上再定义任务点和最小任务流

---

## 3. 当前系统链路

### 3.1 SLAM 建图链路

```text
Gazebo World
→ Robot Model
→ Lidar Plugin
→ Gazebo Topic
→ ros_gz_bridge
→ ROS 2 /scan
→ laser_filters
→ ROS 2 /scan_filtered
→ odom + TF
→ slam_toolbox
→ ROS 2 /map
→ 保存地图
```

### 3.2 Nav2 预期链路

```text
Saved Map
→ nav2_map_server
→ AMCL / localization
→ map -> odom -> base_link
→ Nav2 planner
→ Nav2 controller
→ /cmd_vel
→ Gazebo robot motion
```

### 3.3 关键文件

- 仓库世界：`worlds/warehouse_full.world`
- 机器人模型：`models/my_robot/model.sdf`
- RViz 可视模型：`models/my_robot_visual.urdf`
- LaserScan 滤波参数：`config/laser_filters.yaml`
- SLAM 参数：`config/slam_toolbox.yaml`
- 仿真启动：`launch/simulation.launch.py`
- 建图启动：`launch/slam.launch.py`
- TF 修正节点：`amr_warehouse_sim/odom_tf_node.py`
- SLAM RViz 配置：`rviz/slam.rviz`
- Nav2 RViz 配置：`rviz/nav2.rviz`
- Nav2 地图入口：`maps/warehouse.yaml`
- Nav2 启动入口：`launch/navigation.launch.py`
- Nav2 参数文件：`config/nav2_params.yaml`
- SLAM 原始保存配置：`maps/warehouse_slam.yaml`
- SLAM 地图图像：`maps/warehouse_slam.pgm`

---

## 4. 地图文件说明

当前保存的地图文件：

```text
maps/
├── warehouse.yaml
├── warehouse_slam.yaml
└── warehouse_slam.pgm
```

### 4.1 推荐入口

后续 Nav2 统一使用：

```text
maps/warehouse.yaml
```

`maps/warehouse.yaml` 是稳定入口，当前指向 `warehouse_slam.pgm`。

### 4.2 是否需要转换

当前不需要额外转换。

`maps/warehouse.yaml` 和 `maps/warehouse_slam.yaml` 已经是 Nav2 `map_server` 可读取的 YAML + PGM 格式：

```yaml
image: warehouse_slam.pgm
mode: trinary
resolution: 0.050
origin: [-8.008, -8.174, 0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.196
```

### 4.3 地图使用原则

- `warehouse_slam.yaml`：保留 SLAM 保存时生成的原始文件
- `warehouse.yaml`：作为后续 Nav2、README、launch 的稳定地图入口
- `warehouse_slam.pgm`：地图图像，不手动编辑，除非重新保存地图

---

## 5. 当前已完成状态

已确认内容：

- 机器人由 `worlds/warehouse_full.world` 直接 include `model://my_robot`
- `/cmd_vel` 可控制机器人运动
- `/scan`、`/scan_filtered`、`/odom`、TF 和 `/map` 已打通
- `slam.launch.py` 会自动 configure / activate `slam_toolbox`
- RViz 可以显示 `/map`、`/scan_filtered`、`/odom`、TF 和 RobotModel
- `maps/warehouse.yaml` 已可作为 Nav2 地图入口
- `navigation.launch.py` 已可稳定启动 Nav2 主线
- 经过多次短距离 goal 测试，当前 Nav2 参数已形成一版稳定基线
- 当前路径稳定化主要依赖：更小的 progress checker 阈值、footprint 代价评估、收敛后的 inflation、A* 全局规划

当前注意事项：

- SLAM 建图链路可以保留为 V1 演示入口
- Nav2 阶段不要继续大改 SLAM 链路
- Nav2 已从 `future_extensions/navigation` 提升到当前主线入口
- 旧 SLAM-Nav2 试验文件已移入 `archive/nav2_legacy/`
- 如果重新建图，只更新 `warehouse_slam.*`，再确认 `warehouse.yaml` 指向正确图像
- 当前稳定基线为了先收敛导航，临时关闭了 `collision_monitor` 的 `scan` 和 `FootprintApproach` 拦车项；后续进入任务层或真机前需要重新评估安全策略

---

## 6. Nav2 前置检查

进入 Nav2 前，先确认以下条件：

1. 地图文件可读取：`maps/warehouse.yaml`
2. 仿真可启动：`ros2 launch amr_warehouse_sim simulation.launch.py`
3. `/scan` 和 `/odom` 正常
4. TF 有 `odom -> base_link -> my_robot/lidar_link/lidar`
5. Nav2 localization 启动后能提供 `map -> odom`

建议先单独测试地图服务器和 localization，命令要显式带上当前主线参数文件：

```bash
ros2 launch nav2_bringup localization_launch.py \
  map:=$HOME/ros2_ws/src/amr_warehouse_sim/maps/warehouse.yaml \
  params_file:=$HOME/ros2_ws/src/amr_warehouse_sim/config/nav2_params.yaml \
  use_sim_time:=true
```

启动后重点检查：

```bash
ros2 lifecycle get /map_server
ros2 topic echo /map --once
ros2 run tf2_ros tf2_echo map odom
```

如果 `map -> odom` 不存在，优先检查 AMCL 是否已收到 initial pose、`/scan` 是否正常、TF 是否连通。

### 6.1 Nav2 最小验证流程

推荐先做一个短距离 smoke test，再继续调参数：

1. 启动 `ros2 launch amr_warehouse_sim navigation.launch.py`
2. 确认 `/map` 正常发布，`/scan_filtered` 正常
3. 确认 lifecycle nodes 至少包含 `map_server`、`amcl`、`planner_server`、`controller_server`、`bt_navigator`，并进入 `active`
4. 在 RViz 中用 `2D Pose Estimate` 设置初始位姿
5. 发送 1~2 m 的短距离 `Nav2 Goal`
6. 观察机器人是否输出 `/cmd_vel` 并完成短距离移动

当前建议的通过标准：

- `map -> odom -> base_link` TF 连通
- 机器人可在货架通道内完成短距离点到点导航
- 局部代价地图不明显切入货架或墙体
- RViz 中 RobotModel、LaserScan、Map、Costmap 显示一致
- 重启 Nav2 后仍能复现相同结果

### 6.2 当前关键 Nav2 参数

当前主线中影响测试结论的关键参数如下：

- 地图入口：`maps/warehouse.yaml`
- 激光输入：AMCL 和 costmap 统一使用 `/scan_filtered`
- 坐标系：`map -> odom -> base_link -> my_robot/lidar_link/lidar`
- 机器人 footprint：`0.56 m x 0.42 m`，在 `config/nav2_params.yaml` 中按矩形 footprint 配置
- 局部控制器：`nav2_mppi_controller::MPPIController`
- 全局规划器：`nav2_navfn_planner::NavfnPlanner`，当前启用 A*
- progress checker：`required_movement_radius: 0.10`
- footprint 代价评估：`CostCritic.consider_footprint: true`
- costmap inflation：local / global 均为 `0.40`
- collision monitor：当前稳定基线中关闭 `scan` 和 `FootprintApproach` 拦车项

### 6.3 面向机器人测试的当前假设

当前仓库仿真配置默认满足以下假设：

- 机器人是差速底盘，控制接口为 `/cmd_vel`
- 里程计来源可稳定提供 `/odom`
- 激光雷达提供 `/scan`，经过 `laser_filters` 后得到 `/scan_filtered`
- 雷达安装位姿与当前仿真接近：相对 `base_link` 约为 `x=0.20, y=0.0, z=0.32`
- 真机测试时需要关闭 `use_sim_time`
- 真机地图与当前仿真地图障碍布局需要基本一致，否则 AMCL 和 planner 结论不可靠

### 6.4 当前已知限制

当前版本仍有以下限制，文档和展示时应明确说明：

- 仅验证单车导航，不包含多车协同
- 当前地图和验证流程偏静态环境，未系统验证动态障碍
- 货架环境较对称，定位质量对 initial pose 和 odom 质量敏感
- footprint 来源于仿真模型尺寸，真机上仍应以实测外廓重新确认
- 当前稳定基线优先保证导航复现性，未把 `collision_monitor` 作为最终安全策略收口
- recovery、waypoint、docking 等扩展能力尚未做真机验证

### 6.5 接 WMS 前的前置条件

当前建议的顺序不是直接开发 WMS，而是先满足以下前提：

1. 固定当前 Nav2 稳定参数，不再与任务层并行改动
2. 选取一组固定任务点，验证多次重复导航成功
3. 明确任务系统只下发 map 坐标点，不直接控制 `/cmd_vel`
4. 明确安全方案：重新标定并恢复 `collision_monitor`，或用外部安全链替代
5. 再补状态机最小闭环：`待执行 -> 导航中 -> 到达 -> 失败`

---

## 7. V1 完成标准

当前 V1 可视为完成，完成项如下：

- Gazebo 中可看到机器人
- 机器人可响应 `/cmd_vel`
- `/scan` 稳定输出
- `/scan_filtered` 存在并供 SLAM 使用
- TF 正常连通 `odom -> base_link -> my_robot/lidar_link/lidar`
- `slam_toolbox` 能正常输出 `/map`
- 已保存可展示地图：`maps/warehouse.yaml`
- README、设计文档、排障文档已整理

---

## 8. Roadmap

### V1：建图最小闭环（已完成）

目标：完成可展示、可复现的 AMR 仓库 SLAM 建图项目。

完成项：

- Gazebo 仓库世界稳定启动
- AMR 模型可见、可动
- `/scan`、`/scan_filtered`、`/odom`、TF、`/map` 全链路打通
- 使用 `laser_filters` 改善 LaserScan 输入
- 保存一版可展示地图
- 整理 README、设计文档和排障记录

输出物：

- 建图启动：`launch/slam.launch.py`
- 地图入口：`maps/warehouse.yaml`
- 地图图像：`maps/warehouse_slam.pgm`
- 排障文档：`docs/troubleshooting.md`

### V1.5：工程化整理（当前补充）

目标：让 V1 项目更容易复现、演示和衔接 V2。

工作项：

- 固定 Nav2 地图入口为 `maps/warehouse.yaml`
- README 中补充地图文件和 Nav2 前置命令
- AGENTS 中明确 V1 稳定、V2 可在明确请求下推进
- 清理旧入口、旧文档引用和临时文件

输出物：

- 稳定演示流程
- 清晰项目结构
- 面试讲解提纲

### V2：Nav2 导航与路径执行（当前阶段，稳定基线已完成）

目标：在已有地图基础上，让机器人具备稳定、可复现的点到点导航能力，并作为上层任务系统前置条件。

推荐顺序：

1. 使用 `launch/navigation.launch.py` 启动仿真和 Nav2
2. 使用 `config/nav2_params.yaml` 作为 Nav2 参数入口
3. 启动 `map_server` 读取 `maps/warehouse.yaml`
4. 启动 AMCL 并确认 `map -> odom`
5. 启动 planner / controller / behavior tree
6. RViz 设置 initial pose
7. 发送 2D Nav Goal 验证导航

当前已达到的基础验收标准：

- `/map` 来自已保存地图
- TF 连通 `map -> odom -> base_link`
- Nav2 lifecycle nodes 为 active
- RViz 中可以设置初始位姿和目标点
- 机器人能在仓库地图中完成短距离点到点移动

下一步不再直接扩展 WMS，而是先补：

- 固定任务点集合
- 重复测试记录
- 安全策略收口
- 任务状态流接口

### V3：任务系统与上层调度

目标：从单车导航扩展到任务驱动的仓储 AMR 原型。

候选工作项：

- 简化 WMS 任务接口
- 任务下发与状态回传
- 货架点位 / 工位点位管理
- 多任务队列
- 简单任务执行状态机

### V4：部署与扩展能力

目标：提高项目复现性和扩展性。

候选工作项：

- Docker 或 Dev Container 环境封装
- 多机器人仿真
- CAD / 平面图辅助建图或路径点生成
- 可视化前端面板
- 日志记录与回放

---

## 9. 今日记录

### 2026-04-24

- 今日目标：打通 V1 建图链路，并确认小车可见、可动、可输出地图。
- 实际完成：机器人由 world 直接加载；`/scan`、`/odom`、TF、`/map` 已打通；`slam_toolbox` 改为 launch 自动激活；RViz odometry 话题改为 `/odom`。
- 发现问题：旧 `ros2 topic pub -r ... /cmd_vel` 会抢占键盘控制；旧 launch 和旧 TF 进程会污染当前主线；地图质量仍受驾驶路线影响。
- 明日第一步：干净启动后，只做小范围慢速闭环建图，确认局部地图稳定后再扩展到仓库通道。

### 2026-04-25

- 今日目标：在 V1 已打通基础上，增加滤波或参数优化，解决地图不清晰问题。
- 实际完成：使用 `laser_filters` 生成 `/scan_filtered`，并让 `slam_toolbox` 订阅滤波后的 LaserScan。
- 地图结果：已保存 `maps/warehouse_slam.yaml` 和 `maps/warehouse_slam.pgm`。
- 文档整理：将 `maps/warehouse.yaml` 作为后续 Nav2 的稳定地图入口。
- Nav2 结果：完成多次短距离 goal 测试，当前已形成一版可复现的 Nav2 稳定基线。
- 当前基线：收敛 progress checker、footprint 代价评估、inflation 和 A* 全局规划；为稳定化验证，暂时关闭 `collision_monitor` 拦车项。
- 下一步：定义固定任务点并整理最小任务流，再评估 WMS 接入。
- 迁移记录：Nav2 当前入口已从 `future_extensions/navigation` 提升到 `launch/navigation.launch.py`、`config/nav2_params.yaml` 和 `scripts/run_navigation.sh`；旧试验文件归档到 `archive/nav2_legacy/`。
