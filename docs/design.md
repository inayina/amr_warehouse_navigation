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
- README 引用路径：`docs/design.md`

---

## 2. 当前阶段状态

当前项目已经完成 **V1：AMR 仿真建图最小闭环**，当前主线处于 **V2：Nav2 导航与路径执行**，并继续推进 **V2.2：固定任务点与重复导航验证**。在此基础上，当前主线也已经补上 **V3.2：Mock WMS executor over HTTP** 的最小闭环：HTTP API 已覆盖 create/query/status-writeback，HTTP executor dry-run 可做本地模拟，`--execute` 可在 HTTP 边界内接回 Nav2 execute。

### V1 已完成

- Gazebo 中可以正常显示机器人
- 机器人可以响应 `/cmd_vel`
- `/scan` 可以稳定发布
- `laser_filters` 可以输出 `/scan_filtered`
- `/odom` 和 TF 链路正确
- `slam_toolbox` 可以输出 `/map`
- 已保存一版仓库地图

### 当前重点

当前重点不是继续修改 SLAM 主链路，而是保持 Nav2 稳定基线不被破坏，并把 headless 启动、固定任务点和最小任务执行链说明收口：

1. 保持 `maps/warehouse.yaml`、`launch/navigation.launch.py`、`config/nav2_params.yaml` 作为稳定入口
2. 标准化 initial pose handling，明确 `publish_initial_pose --preset start_zone` 的使用时机
3. 维护 `config/task_points.yaml` 作为主线固定任务点输入
4. 继续积累 fixed-goal 重复导航证据，并记录 startup stability 波动
5. 让最小 Mock WMS 任务链只消费固定点位，不反向改 Nav2 主线

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
- 初始位姿工具：`amr_warehouse_sim/initial_pose_publisher.py`
- SLAM RViz 配置：`rviz/slam.rviz`
- Nav2 RViz 配置：`rviz/nav2.rviz`
- Nav2 地图入口：`maps/warehouse.yaml`
- Nav2 启动入口：`launch/navigation.launch.py`
- Nav2 参数文件：`config/nav2_params.yaml`
- 固定任务点入口：`config/task_points.yaml`
- 最小 Mock WMS 数据层脚本：`scripts/init_mock_wms_db.py`、`scripts/create_mock_task.py`、`scripts/list_mock_tasks.py`
- 最小 Mock WMS HTTP API：`scripts/mock_wms_api.py`、`amr_warehouse_sim/mock_wms_api.py`
- 最小 Mock WMS 执行入口：`scripts/run_mock_wms_executor.py`、`amr_warehouse_sim/mock_wms_task_runner.py`
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
- `publish_initial_pose --preset start_zone` 已成为主线 initial pose 工具入口
- `config/task_points.yaml` 已固定 `start_zone`、station / shelf candidate points 和 `candidate_dock_a`
- 最小 Mock WMS SQLite 数据层、CLI、executor 与顺序 runner 已建立，已形成受 ready gate 保护的主线最小任务执行验证入口
- 最小 Mock WMS HTTP API 已建立，当前已覆盖 `health`、任务创建/查询、最小状态回写；HTTP executor dry-run 会本地模拟，`--execute` 会在 ready gate 满足后通过 Nav2 发送 goal，但这仍不是完整 WMS 调度服务
- 当前路径稳定化主要依赖：更小的 progress checker 阈值、footprint 代价评估、收敛后的 inflation、A* 全局规划

当前注意事项：

- SLAM 建图链路可以保留为 V1 演示入口
- Nav2 阶段不要继续大改 SLAM 链路
- Nav2 已从 `future_extensions/navigation` 提升到当前主线入口
- 旧 SLAM-Nav2 试验文件已移入 `archive/nav2_legacy/`
- 如果重新建图，只更新 `warehouse_slam.*`，再确认 `warehouse.yaml` 指向正确图像
- 当前稳定基线为了先收敛导航，临时关闭了 `collision_monitor` 的 `scan` 和 `FootprintApproach` 拦车项；后续进入任务层或真机前需要重新评估安全策略

### 5.1 测试工程化基线

当前测试工程化基线已经补齐，自动化入口与运行时复测入口分工如下：

- 当前包是 `ament_python`，不是 `ament_cmake`
- `pytest test -q` 与 `colcon test --packages-select amr_warehouse_sim` 已接入同一批自动化 `pytest` 测试
- 当前通过 `setup.py` 中的 `tests_require=['pytest']` 和 `package.xml` 中的 `pytest` 测试依赖，让 `colcon test` 默认调用 `python3 -m pytest`
- 以 `2026-05-14` 的最新本地校验为准，从项目根目录执行 `make test` 的结果为：`63 passed`
- 当前自动化覆盖范围包括：map 文件检查、Nav2 配置检查、固定任务点配置检查、launch smoke test、initial pose publisher、navigation pipeline contract、mock WMS contract、mock WMS SQLite data layer
- 当前自动化覆盖范围还包括：Mock WMS HTTP API 的 `health / create / list / get` 集成契约
- `test/scenarios/` 中的场景文档仍然是手工 / spec 流程，不纳入当前自动化执行
- 默认 `colcon test-result --verbose` 可能汇总整个工作区已有测试结果；如果只查看本包结果，应使用 `colcon test-result --verbose --test-result-base build/amr_warehouse_sim`

补充说明：

- `docs/reports/test_report_2026_05_12.md` 记录的是 `2026-05-12` 当日的真实结果，当时自动化规模还小于当前版本
- 因此，当前主线说明应以“最新本地校验结果”表达现状，历史测试报告仍保留原始记录，不回写改数

### 5.2 固定任务点与最小任务执行链

截至 `2026-05-14`，当前主线关于 fixed points、最小任务执行链和最小 HTTP API 的状态如下：

- `start_zone` 是当前唯一主线 initial pose preset
- `station_a`、`station_b`、`shelf_1`、`shelf_2` 已写入 `config/task_points.yaml`
- `candidate_dock_a` 保留为历史候选点，用于补充导航验证
- `docs/reports/repeat_navigation_test_report_2026_05_13.md` 已记录 V2.2 固定任务点与重复导航结果
- `docs/logs/nav2_startup_stability_notes.md` 与 `docs/logs/nav2_startup_stability_log_2026_05_13.md` 已单独拆出 fresh-session 启动稳定性现象
- `docs/wms/reports/wms_task_points_readiness_report_2026_05_13.md` 已记录 station / shelf 点位进入 Mock WMS 数据层前的真实导航验证结果
- `docs/wms/reports/mock_wms_executor_execute_validation_2026_05_13.md` 已记录 fresh session 内 ready gate / discovery 波动对单次 execute 的影响
- `docs/wms/reports/mock_wms_task_runner_live_validation_2026_05_13.md` 已记录 `mock_wms_task_runner` 的 dry-run、单条 execute 和 `station_a -> station_b` 顺序 execute 真实 `SUCCEEDED` 结果
- `docs/wms/reports/mock_wms_http_api_validation_2026_05_14.md` 已记录最小 HTTP API 的 `uvicorn + curl` 真实验证结果
- 当前 Mock WMS 已形成 SQLite + CLI + executor / task_runner + HTTP create/query 的最小闭环，但这仍不是完整 WMS / 多机器人调度系统，也不声明端到端任务执行已经完全稳定

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
2. 确认 `/map` 正常发布，`/scan_filtered` 正常，且 `odom -> base_link` TF 可用
3. 注入初始位姿：
   手动方式是在 RViz 中使用 `2D Pose Estimate`
   自动方式是执行 `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone`
4. 初始位姿应在 `/map`、`/scan_filtered`、`odom -> base_link` 可用后注入
5. 注入后再检查 `map -> odom` 是否建立，以及 `map_server`、`amcl`、`planner_server`、`controller_server`、`bt_navigator` 是否进入 `active`
6. 发送 1~2 m 的短距离 `Nav2 Goal`
7. 观察机器人是否输出 `/cmd_vel` 并完成短距离移动

补充说明：

- 对于无界面 / 无人值守复测，若未注入 initial pose，`map -> odom` 不一定建立，`planner_server` / `bt_navigator` 也可能停在 `inactive`
- 因此，不注入 initial pose 的 headless 测试结果，不能直接判定为“导航功能失败”
- 当前更准确的工程化要求是：把 initial pose handling 纳入标准验证流程，并控制注入时机
- 对于 fresh session / headless 复测，当前更推荐使用 `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30`

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
- 当前 headless / automated runtime validation 依赖标准化的 initial pose 注入；如果未注入 initial pose，AMCL 不一定建立 `map -> odom`，`planner_server` / `bt_navigator` 可能保持 `inactive`

### 6.5 接 WMS 前的前置条件

当前建议的顺序不是直接开发 WMS，而是先满足以下前提：

1. 固定当前 Nav2 稳定参数，不再与任务层并行改动
2. 固定 initial pose 注入策略，明确何时使用 RViz `2D Pose Estimate`，何时使用 `publish_initial_pose --preset start_zone`
3. 固定一组任务点集合，至少包括 `start_zone`、station points、shelf points 等稳定 map frame 点位
4. 使用固定 initial pose 和固定 goal，继续积累 `3~5` 轮以上的重复导航记录，并区分 `SUCCEEDED`、`ABORTED`、`SKIPPED`
5. 明确任务系统只负责创建任务并下发 map frame 目标点，不直接控制 `/cmd_vel`，也不修改 Nav2 参数
6. 明确安全方案：重新标定并恢复 `collision_monitor`，或用外部安全链替代
7. 状态机先做最小闭环：`pending -> running -> succeeded / failed`

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
6. 在 RViz 或命令行注入 initial pose
7. 发送 2D Nav Goal 验证导航

当前已达到的基础验收标准：

- `/map` 来自已保存地图
- TF 连通 `map -> odom -> base_link`
- Nav2 lifecycle nodes 为 active
- RViz 或 `publish_initial_pose` 均可设置初始位姿
- 机器人能在仓库地图中完成短距离点到点移动

下一步不再直接扩展 WMS，而是先补：

- 固定任务点集合
- 重复测试记录
- 安全策略收口
- 任务状态流接口

### V2.1：测试与运行时基线收口

目标：先把自动化测试入口和运行时导航验证流程收口成统一基线。

工作项：

- `colcon test` 正常发现并执行现有 `pytest`
- 将 initial pose publisher 纳入导航验证流程
- 形成 baseline test report
- 明确 manual validation 与 automated validation 的边界

输出物：

- `pytest` / `colcon test` 双入口自动化回归
- `docs/reports/test_report_2026_05_12.md`
- 标准化的 initial pose handling 说明

### V2.2：固定任务点与重复导航验证

目标：在当前稳定 Nav2 基线上，先固定 map frame 输入点位并积累重复导航记录。

当前主线文件：

- `config/task_points.yaml`
- `docs/fixed_task_points.md`
- `docs/templates/repeat_navigation_test_report.md`

工作项：

- 维护固定任务点集合
- 继续为 station / shelf 点位积累更稳定的重复导航证据
- 使用 initial pose + fixed goals 做 `3~5` 轮以上重复导航
- 记录成功率、失败原因、`/cmd_vel`、TF、lifecycle 状态
- 为 V3 Mock WMS 提供稳定的 map frame 任务点输入

当前策略说明：

- `config/task_points.yaml` 已经是主线固定点入口，但 business points 仍应标记为 candidate coordinates
- `candidate_dock_a` 这类历史候选点可以继续作为补充验证输入，但不能直接等同于“正式固定点长期稳定”
- V3 当前已经接入最小 SQLite 数据层、受 ready gate 保护的 executor / task_runner，以及只负责 task create/query 的最小 HTTP API；更完整的调度闭环仍暂缓到后续阶段

输出物：

- `config/task_points.yaml`
- `docs/fixed_task_points.md`
- `docs/templates/repeat_navigation_test_report.md`
- 可供 V3 Mock WMS 消费的稳定 map frame 目标点集合

### V3：任务系统与上层调度

目标：在 V2.1 和 V2.2 完成后，再进入任务层与上层调度验证。

候选工作项：

- SQLite / Mock WMS 任务层当前已经包含最小 HTTP API，但它只负责创建/查询，不接入 Nav2 execute
- 前提是 V2.1 和 V2.2 已完成
- V3 任务系统只消费固定 map frame 目标点并更新任务状态

V3 当前已落地的最小范围：

- V3.0：SQLite 任务数据层与 CLI `init/create/list` 已落地
- V3.1：最小 ROS 2 task executor 与顺序 runner 已落地，并作为当前主线轻量任务执行验证入口
- 当前只消费 `config/task_points.yaml`，并已允许 `candidate_dock_a` / `dock_a`、`station_a`、`station_b`、`shelf_1`、`shelf_2`
- Mock WMS 只存储 `map` frame goal 和任务状态，在 ready gate 满足后通过 Nav2 action 下发 goal，不直接控制 `/cmd_vel`
- V3.3 live 验证已确认：dry-run 不发送 goal；`station_a` 单条 execute 与 `station_a -> station_b` 顺序 execute 都拿到真实 `SUCCEEDED`
- 因 fresh-session 下 lifecycle / discovery 仍有偶发波动，当前不声明完整 WMS 调度或端到端任务执行已经完全稳定

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

### 2026-05-12

- 恢复旅行后进行 V2 导航基线复测。
- `pytest` / `colcon test` 集成已修复；当日自动化结果为 `16` 个测试全部通过。
- 本轮确认：在缺少 initial pose 的 headless 复测中，`/map` 与 `/scan_filtered` 可正常发布，但 `map -> odom` 不一定建立。
- 本轮进一步确认：执行 `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone` 后，`map_server`、`amcl`、`planner_server`、`controller_server`、`bt_navigator` 均可进入 `active`，且 `tf2_echo map odom` 可输出有效变换。
- 当前结论不是继续“修导航功能”，而是要先标准化 initial pose handling、固定任务点并完成重复导航测试；更完整 WMS 调度仍暂缓到后续阶段。

### 2026-05-13

- 当前主线文档已统一到 fixed task points、repeat navigation、startup stability 和最小 Mock WMS 任务执行链的最新状态。
- 最新本地自动化校验结果为 `pytest test -q -> 44 passed in 0.58s`。
- `config/task_points.yaml`、`publish_initial_pose` 和最小 Mock WMS 数据层 / executor / task runner 说明已经补齐到 README / design / roadmap 主线文档。
- 当前对外口径应表述为：Nav2 稳定基线已经建立，fixed task points 和最小任务执行链已经落地，但 fresh-session startup stability 仍在继续观察，更完整 WMS 调度仍未进入当前主线。

### 2026-05-14

- 当前主线已经补上最小 Mock WMS HTTP API，范围包括 `GET /health`、`POST /tasks`、`GET /tasks`、`GET /tasks/{task_id}`、`PATCH /tasks/{task_id}/status`。
- 当前 `mock_wms_executor --api-base-url ...` 已能通过 HTTP 拉取最早一条 `pending` task；dry-run 会本地模拟并回写 `running -> succeeded`，`--execute` 会在 ready gate 满足后通过 Nav2 发送 goal，并继续通过 HTTP 回写 `running -> succeeded / failed`。
- 这层 HTTP API 当前负责暴露 SQLite Mock WMS 数据层与最小状态回写边界，但仍不引入 Web 后台、MQTT、WebSocket 或多机器人调度。
- 最新本地自动化校验结果为：从项目根目录执行 `make test`，得到 `63 passed`。
