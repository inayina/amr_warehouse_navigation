# V2.2 固定任务点与重复导航测试报告

日期：`2026-05-13`

本文件用于记录 V2.2 阶段的固定任务点集合、`/initialpose` 注入、Nav2 lifecycle 状态、`map -> odom`、`/cmd_vel`、目标到达情况，以及 `3~5` 轮重复导航验证结果。

说明：

- `docs/reports/test_report_2026_05_12.md` 作为 V2.1 baseline test report 保留，本文件不改写其主体内容。
- 本文件只记录 V2.2 的固定任务点与重复导航验证。
- 未实际执行、未实际观察到，或尚未完成 `3~5` 轮复测的项目统一标记为 `TBD`。

## 1. 测试目标

- 固定当前 V2.2 阶段可复用的任务点输入。
- 记录 `start_zone` 初始位姿注入是否可重复执行。
- 记录 Nav2 lifecycle、`map -> odom`、`/cmd_vel`、goal 到达情况。
- 为后续任务层提供一份不混入伪造结果的重复导航验证记录。

## 2. 测试环境

| 项目 | 内容 |
| --- | --- |
| 仓库 | `amr_warehouse_navigation` |
| ROS 2 包名 | `amr_warehouse_sim` |
| 当前阶段 | `V2.2 固定任务点与重复导航验证` |
| 主线启动文件 | `launch/navigation.launch.py` |
| 主线参数文件 | `config/nav2_params.yaml` |
| 地图入口 | `maps/warehouse.yaml` |
| 任务点配置 | `config/task_points.yaml` |
| 初始位姿入口 | `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone` |
| 测试日期 | `2026-05-13` |
| 今日实际启动命令 | `ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false` |
| 测试人员 | `Codex（命令行复测）` |
| 关联基线报告 | [docs/reports/test_report_2026_05_12.md](./test_report_2026_05_12.md) |

## 3. 固定任务点集合

当前仓库中已经固定了 V2.2 主线任务点名称。`start_zone` 仍是已确认的初始位姿点；`station_a`、`station_b`、`shelf_1`、`shelf_2` 原本是无坐标业务点，本轮已最小写入 `docs/task_points_coordinate_plan.md` 提出的 candidate coordinates，仅用于首次真实 Nav2 验证，不代表最终业务点位定版。

| Point ID | 用途 | Frame | X | Y | Yaw | 来源 | 当前状态 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `start_zone` | initial pose | `map` | `0.0` | `0.0` | `0.0 rad` | `config/task_points.yaml` | `坐标已确认` | 对应机器人出生点和起始区域中心 |
| `station_a` | fixed goal | `map` | `-5.3` | `-5.8` | `3.14 rad` | `config/task_points.yaml` | `candidate coordinates 已写入` | 来源为 `docs/task_points_coordinate_plan.md`，仅用于首次真实验证，非最终业务定版 |
| `station_b` | fixed goal | `map` | `5.0` | `-4.8` | `0.0 rad` | `config/task_points.yaml` | `candidate coordinates 已写入` | 来源为 `docs/task_points_coordinate_plan.md`，仅用于首次真实验证，非最终业务定版 |
| `shelf_1` | fixed goal | `map` | `-2.75` | `2.5` | `0.0 rad` | `config/task_points.yaml` | `candidate coordinates 已写入` | 来源为 `docs/task_points_coordinate_plan.md`，仅用于首次真实验证，非最终业务定版 |
| `shelf_2` | fixed goal | `map` | `2.75` | `2.5` | `3.14 rad` | `config/task_points.yaml` | `candidate coordinates 已写入` | 来源为 `docs/task_points_coordinate_plan.md`，仅用于首次真实验证，非最终业务定版 |

## 4. Initial Pose 注入记录

| 项目 | 预期 | V2.1 baseline 参考 | 2026-05-13 实际结果 | 状态 |
| --- | --- | --- | --- | --- |
| `publish_initial_pose --preset start_zone` | 能向 `/initialpose` 发布有效初始位姿 | `2026-05-12` 已确认该命令可找到订阅者并连续发布 `10` 条消息 | 多轮 headless 复测中都能找到 `1` 个 `/initialpose` 订阅者，并连续发布 `10` 条初始位姿；命令输出了每一条 `x=0.000, y=0.000, yaw=0.000 rad, frame=map` 的发布记录 | `通过` |
| 注入时机 | 在 Nav2 启动早期执行，支撑后续 lifecycle 拉起 | `2026-05-12` 已确认“启动早期注入”有效，“激活失败后补发”不能自动补齐 lifecycle | 第 1 轮中未在启动早期注入，等 `planner_server` 激活失败后再补发初始位姿，`map -> odom` 可恢复，但 `planner_server` 与 `bt_navigator` 仍分别保持 `inactive [2]`。第 2 轮干净重启后，在启动约 `12` 秒执行 `publish_initial_pose --preset start_zone`，`map_server`、`amcl`、`planner_server`、`controller_server`、`bt_navigator` 全部进入 `active [3]`，`/navigate_to_pose` 有 `1` 个 action server | `通过（需启动早期注入）` |

## 5. 启动前检查与运行时前提

| 检查项 | 预期结果 | V2.1 baseline 参考 | 2026-05-13 实际结果 | 状态 |
| --- | --- | --- | --- | --- |
| `/map` | 正常发布 | `2026-05-12` 已通过 | 第 2 轮 headless 复测中成功收到 `OccupancyGrid`；`resolution: 0.05`，`width: 321`，`height: 322`，`origin: (-8.008, -8.174, 0.0)`；`ros2 topic info /map` 显示 `Publisher count: 1`、`Subscription count: 2` | `通过` |
| `/scan_filtered` | 正常发布 | `2026-05-12` 已通过 | 成功收到滤波后的 `LaserScan`；`frame_id: my_robot/lidar_link/lidar`，量测值与 5-12 baseline 一致处于有效范围 | `通过` |
| `map_server` | `active [3]` | `2026-05-12` 已通过 | 第 2 轮启动早期注入初始位姿后为 `active [3]` | `通过` |
| `amcl` | `active [3]` | `2026-05-12` 已通过 | 第 2 轮启动早期注入初始位姿后为 `active [3]` | `通过` |
| `planner_server` | `active [3]` | `2026-05-12` 已确认需依赖启动早期 initial pose 注入 | 第 1 轮晚注入时为 `inactive [2]`；第 2 轮启动早期注入后为 `active [3]` | `通过（需启动早期注入）` |
| `controller_server` | `active [3]` | `2026-05-12` 已通过 | 第 1 轮和第 2 轮均为 `active [3]` | `通过` |
| `bt_navigator` | `active [3]` | `2026-05-12` 已确认需依赖启动早期 initial pose 注入 | 第 1 轮晚注入时为 `inactive [2]`；第 2 轮启动早期注入后为 `active [3]` | `通过（需启动早期注入）` |
| `map -> odom` | TF 连通 | `2026-05-12` 已确认需依赖启动早期 initial pose 注入 | 第 1 轮补发初始位姿后可输出稳定变换，平移约 `[0.010, 0.021, 0.000]`，偏航约 `0.356` 度。第 2 轮启动早期注入后同样可稳定输出，平移约 `[0.009, 0.021, 0.000]`，偏航约 `0.295` 度 | `通过（需初始位姿步骤）` |
| `odom -> base_link` | TF 连通 | `2026-05-12` 基线主链默认依赖该 TF | 第 2 轮中 `tf2_echo odom base_link` 可输出稳定变换，平移近似 `[0.000, 0.000, 0.000]`，偏航近似 `0.000` 度 | `通过` |
| `/cmd_vel` | 发出有效速度命令 | `2026-05-12` 基线报告未覆盖固定 goal 重复导航 | 第 2 轮在发送历史候选 `dock_a` goal 后，成功捕获首条 `/cmd_vel`，线速度 `x=-0.0721`，角速度 `z=-0.0633` | `通过（探索性 goal）` |
| `/navigate_to_pose` | action server 可用 | `2026-05-12` 基线报告未单独记录 | 第 1 轮晚注入后 `Action servers: 0`；第 2 轮启动早期注入后 `Action servers: 1`，server 为 `/bt_navigator` | `通过（需启动早期注入）` |

## 6. 固定 Goal 集合

本节记录当前已经写入主线 `config/task_points.yaml` 的可执行目标点集合。`station_a`、`station_b`、`shelf_1`、`shelf_2` 在本轮之前是无坐标业务点；当前坐标来自 `docs/task_points_coordinate_plan.md` 的 candidate coordinates，只用于首次真实验证。

| Goal ID | 类别 | Frame | X | Y | Yaw | 定义来源 | 当前状态 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `station_a` | `station` | `map` | `-5.3` | `-5.8` | `3.14` | `config/task_points.yaml` | `candidate coordinates 已写入` | 来自 `docs/task_points_coordinate_plan.md`，本轮仅做首次真实验证，非最终业务点位 |
| `station_b` | `station` | `map` | `5.0` | `-4.8` | `0.0` | `config/task_points.yaml` | `candidate coordinates 已写入` | 来自 `docs/task_points_coordinate_plan.md`，本轮仅做首次真实验证，非最终业务点位 |
| `shelf_1` | `shelf` | `map` | `-2.75` | `2.5` | `0.0` | `config/task_points.yaml` | `candidate coordinates 已写入` | 来自 `docs/task_points_coordinate_plan.md`，本轮仅做首次真实验证，非最终业务点位 |
| `shelf_2` | `shelf` | `map` | `2.75` | `2.5` | `3.14` | `config/task_points.yaml` | `candidate coordinates 已写入` | 来自 `docs/task_points_coordinate_plan.md`，本轮仅做首次真实验证，非最终业务点位 |
| `candidate_dock_a` | `historical candidate` | `map` | `0.0` | `-3.8` | `-1.57 rad` | `config/task_points.yaml` | `已写入主线配置，仍属候选点` | 来源是 `future_extensions/wms_integration/config/waypoints.json` 中的历史候选点，本轮仅作为探索性 headless goal 使用 |

说明：

- 本轮除了延续历史候选 `candidate_dock_a` 的记录，也首次对 `station_a`、`station_b`、`shelf_1`、`shelf_2` 的 candidate coordinates 做了独立 fresh session 真实验证。
- 这些 station / shelf 坐标目前仍然只是 candidate coordinates；即使某一点本轮成功，也不等于最终业务点位已经定版。

## 7. Candidate Goal Validation

本节记录历史候选点 `candidate_dock_a` 的当前验证结果。它仍然不是正式 station / shelf 点位，但今天已经积累了多轮真实 headless 导航证据。

| Item | Value |
| --- | --- |
| Goal ID | `candidate_dock_a` |
| Frame | `map` |
| X | `0.0` |
| Y | `-3.8` |
| Yaw | `-1.57` |
| Source | `future_extensions/wms_integration/config/waypoints.json` historical candidate point |
| Successful goal runs observed | `RUN-02`、`RUN-03`、`RUN-05` |
| `/cmd_vel` captured | `yes` |
| `navigate_to_pose` result | `SUCCEEDED` |
| Status | `3` 次真实 goal 成功；但 `RUN-04` 暴露了 lifecycle 波动，因此当前更适合作为“第一个正式固定点候选”，而不是写成全局稳定性已完全收口 |

## 8. 重复导航轮次记录

| Run ID | Start Pose | Goal ID | Goal Pose | Initial Pose 注入 | Lifecycle Active | `map -> odom` | `/cmd_vel` 观测 | Goal 到达 | 结果 | 证据 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `RUN-01` | `start_zone` | `未发送正式 goal` | `N/A` | 第 1 轮未在启动早期注入；待 `planner_server` 激活失败后补发 `start_zone` | `否` | `是（补发后恢复）` | `否` | `N/A` | `未形成正式导航轮次` | `planner_server inactive [2]`、`bt_navigator inactive [2]`、`/navigate_to_pose` server `0` | 这一轮只证明“晚注入可以恢复 TF，但不会自动补齐 navigation lifecycle” |
| `RUN-02` | `start_zone` | `candidate_dock_a` | `map: x=0.0, y=-3.8, yaw=-1.57` | 第 2 轮启动约 `12` 秒执行 `publish_initial_pose --preset start_zone` | `是` | `是` | `是` | `是` | `探索性通过` | `Goal accepted`、`Goal finished with status: SUCCEEDED`、首条 `/cmd_vel` 已捕获 | 使用历史候选 `dock_a` 坐标，不计作正式 V2.2 station/shelf 点位回填完成 |
| `RUN-03` | `start_zone` | `candidate_dock_a` | `map: x=0.0, y=-3.8, yaw=-1.57` | 启动约 `12` 秒执行 `publish_initial_pose --preset start_zone --wait-for-subscribers 30` | `是` | `是` | `是` | `是` | `通过` | 5 个 lifecycle 节点均为 `active [3]`；`Goal finished with status: SUCCEEDED`；首条 `/cmd_vel` 已捕获 | 本轮总耗时约 `89s`，goal 导航时间约 `10.559s` |
| `RUN-04` | `start_zone` | `candidate_dock_a` | `map: x=0.0, y=-3.8, yaw=-1.57` | 启动约 `12` 秒执行 `publish_initial_pose --preset start_zone --wait-for-subscribers 30` | `否` | `是` | `否` | `否` | `跳过` | `map_server`、`amcl` 为 `active [3]`，但 `planner_server`、`controller_server`、`bt_navigator` 停在 `inactive [2]`；`/navigate_to_pose` server `1` | 本轮未伪造 goal 结果；由于 lifecycle 未全部激活，按流程跳过发 goal，总耗时约 `211s` |
| `RUN-05` | `start_zone` | `candidate_dock_a` | `map: x=0.0, y=-3.8, yaw=-1.57` | 启动约 `12` 秒执行 `publish_initial_pose --preset start_zone --wait-for-subscribers 30` | `是` | `是` | `是` | `是` | `通过` | 5 个 lifecycle 节点均为 `active [3]`；`Goal finished with status: SUCCEEDED`；首条 `/cmd_vel` 已捕获 | 本轮总耗时约 `79s`，goal 导航时间约 `10.559s` |
| `RUN-06` | `start_zone` 近邻（`bt_navigator` 记录起点约 `x=0.01, y=0.02`） | `buffer_1` | `map: x=2.4, y=-3.8, yaw=0.0` | 本轮干净启动后，待 `/initialpose` 订阅者就绪并在启动约 `26` 秒执行 `publish_initial_pose --preset start_zone --wait-for-subscribers 30` | `是` | `是` | `是` | `是` | `通过（历史候选补测）` | 5 个 lifecycle 节点均为 `active [3]`；`/navigate_to_pose` 启动前为 `1` 个 server；`Goal finished with status: SUCCEEDED`；首条 `/cmd_vel` 为 `linear.x=0.01998`、`angular.z=-0.51845` | 点位来源仍是 `future_extensions/wms_integration/config/waypoints.json` 历史候选坐标，本轮只补真实导航覆盖，不把它写回当前主线固定点集合 |
| `RUN-07` | `start_zone` | `staging_1` | `map: x=4.6, y=-3.8, yaw=0.0` | 干净重启后，待 `/initialpose` 订阅者就绪并在启动约 `27` 秒执行 `publish_initial_pose --preset start_zone --wait-for-subscribers 30` | `否` | `是` | `否` | `否` | `跳过` | `ros2 node list` 可见整套 Nav2 节点；`/map_server active [3]`、`/controller_server active [3]`、`/bt_navigator active [3]`；但 `ros2 lifecycle get /amcl`、`ros2 lifecycle get /planner_server` 返回 `Node not found`，`ros2 action info /navigate_to_pose` 返回 `Action servers: 0` | 本轮为 `staging_1` 的独立 fresh session；由于 lifecycle 未形成完整 `5/5 active` 且 action server 不可用，按规则未发 goal |
| `RUN-08` | `start_zone` | `inspection_point` | `map: x=5.0, y=-1.2, yaw=3.14` | 干净重启后，待 `/initialpose` 订阅者就绪并在启动约 `26` 秒执行 `publish_initial_pose --preset start_zone --wait-for-subscribers 30` | `否` | `是` | `否` | `否` | `跳过` | `ros2 node list` 可见整套 Nav2 节点；`/map_server`、`/amcl`、`/planner_server`、`/controller_server` 均可查到 `active [3]`；`ros2 action info /navigate_to_pose` 返回 `Action servers: 1`；但 `ros2 lifecycle get /bt_navigator` 两次复核都返回 `Node not found` | 本轮为 `inspection_point` 的独立 fresh session；虽然 TF 和 action server 已恢复，但 lifecycle 仍未满足“全部 active”的发 goal 前提，因此按规则跳过 |
| `RUN-09` | `start_zone` | `station_b` | `map: x=5.0, y=-4.8, yaw=0.0` | 干净重启后，待 `/initialpose` 订阅者就绪并执行 `publish_initial_pose --preset start_zone --wait-for-subscribers 30` | `否` | `是` | `否` | `否` | `跳过` | `ros2 lifecycle get /map_server`、`/amcl`、`/planner_server`、`/controller_server` 均为 `active [3]`；`ros2 lifecycle get /bt_navigator` 两次复核都返回 `Node not found`；`ros2 action info /navigate_to_pose` 两次复核都返回 `Action servers: 0` | 原本无坐标业务点，本轮首次按 candidate coordinates 做独立 fresh session 真实验证；因 lifecycle 不完整且 action server 不可用，未发 goal |
| `RUN-10` | `start_zone` | `station_a` | `map: x=-5.3, y=-5.8, yaw=3.14` | 干净重启后，待 `/initialpose` 订阅者就绪并执行 `publish_initial_pose --preset start_zone --wait-for-subscribers 30` | `否` | `是` | `否` | `否` | `跳过` | `map -> odom` 可用；`ros2 node list` 可见 `/planner_server` 与 `/bt_navigator`，但对应 lifecycle 查询均返回 `Node not found`；`ros2 action info /navigate_to_pose` 返回 `Action servers: 0` | 原本无坐标业务点，本轮首次按 candidate coordinates 做独立 fresh session 真实验证；因 lifecycle 查询不完整且 action server 不可用，未发 goal |
| `RUN-11` | `start_zone` | `shelf_1` | `map: x=-2.75, y=2.5, yaw=0.0` | 干净重启后，待 `/initialpose` 订阅者就绪并执行 `publish_initial_pose --preset start_zone --wait-for-subscribers 30` | `否` | `是` | `否` | `否` | `跳过` | `/amcl`、`/planner_server`、`/controller_server`、`/bt_navigator` 为 `active [3]`，但 `ros2 lifecycle get /map_server` 返回 `Node not found`；`ros2 action info /navigate_to_pose` 返回 `Action clients: 1 (/docking_server)`、`Action servers: 0` | 原本无坐标业务点，本轮首次按 candidate coordinates 做独立 fresh session 真实验证；因 lifecycle 不完整且 action server 不可用，未发 goal |
| `RUN-12` | `start_zone` | `shelf_2` | `map: x=2.75, y=2.5, yaw=3.14` | 干净重启后，待 `/initialpose` 订阅者就绪并执行 `publish_initial_pose --preset start_zone --wait-for-subscribers 30` | `是` | `是` | `未单独记录` | `是` | `通过（candidate 首测）` | 5 个关键 lifecycle 节点均为 `active [3]`；`map -> odom` 可用；`ros2 action info /navigate_to_pose` 首次检查为 `Action servers: 0`，短暂复核后恢复为 `1`，server 为 `/bt_navigator`；`Goal accepted`，最终 `Goal finished with status: SUCCEEDED` | 原本无坐标业务点，本轮首次按 candidate coordinates 做独立 fresh session 真实验证；虽然最终成功，但导航约 `66s` 且出现 `5` 次 recoveries，仍建议后续小幅微调坐标 |

### 8.1 补测开始前的点位扫描

基于补测开始前的 `config/task_points.yaml` 与本报告既有运行记录，本轮开始前的点位状态如下：

- 已测点：`candidate_dock_a`、`buffer_1`、`staging_1`、`inspection_point`；其中 `candidate_dock_a`、`buffer_1` 已有真实 `SUCCEEDED`，`staging_1`、`inspection_point` 已有独立 fresh session 的真实 `SKIPPED`
- 未测点：`station_a`、`station_b`、`shelf_1`、`shelf_2`（当时仍是无坐标业务点，尚未形成可执行 goal）

### 8.2 本轮点位覆盖补测记录

本节按“point name、goal x/y/yaw、lifecycle、TF、action、结果和原因”记录 2026-05-13 同日续测结果。`station_a`、`station_b`、`shelf_1`、`shelf_2` 原本是无坐标业务点，本轮首次使用 `docs/task_points_coordinate_plan.md` 的 candidate coordinates 进行真实验证；结果全部来自真实运行，不代表最终业务点位已定版。

| Point Name | Goal X / Y / Yaw | 来源 | Lifecycle | TF | Action | 结果 | 原因 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `station_a` | `-5.3 / -5.8 / 3.14` | `config/task_points.yaml` candidate from `docs/task_points_coordinate_plan.md` | `不完整；ros2 node list` 可见 `/planner_server` 与 `/bt_navigator`，但 lifecycle 查询返回 `Node not found` | `map -> odom` 可用；采样平移约 `[0.003, 0.023, 0.000]`，偏航约 `0.491` 度 | `/navigate_to_pose` 返回 `Action servers: 0` | `SKIPPED` | 原本无坐标业务点，本轮首次 candidate 首测；前置条件不满足，未强行发 goal |
| `station_b` | `5.0 / -4.8 / 0.0` | `config/task_points.yaml` candidate from `docs/task_points_coordinate_plan.md` | `/map_server`、`/amcl`、`/planner_server`、`/controller_server` 为 `active [3]`，但 `/bt_navigator` 两次复核都返回 `Node not found` | `map -> odom` 可用；采样平移约 `[0.017, 0.017, 0.000]`，偏航约 `0.089` 度 | `/navigate_to_pose` 两次复核都返回 `Action servers: 0` | `SKIPPED` | 原本无坐标业务点，本轮首次 candidate 首测；前置条件不满足，未强行发 goal |
| `shelf_1` | `-2.75 / 2.5 / 0.0` | `config/task_points.yaml` candidate from `docs/task_points_coordinate_plan.md` | `/amcl`、`/planner_server`、`/controller_server`、`/bt_navigator` 为 `active [3]`，但 `/map_server` 返回 `Node not found` | `map -> odom` 可用；采样平移约 `[0.008, 0.023, 0.000]`，偏航约 `0.190` 度 | `/navigate_to_pose` 返回 `Action clients: 1 (/docking_server)`、`Action servers: 0` | `SKIPPED` | 原本无坐标业务点，本轮首次 candidate 首测；前置条件不满足，未强行发 goal |
| `shelf_2` | `2.75 / 2.5 / 3.14` | `config/task_points.yaml` candidate from `docs/task_points_coordinate_plan.md` | 发送前 5 个关键 lifecycle 节点均为 `active [3]` | `map -> odom` 可用；采样平移约 `[0.000, 0.030, 0.000]`，偏航约 `0.199` 度 | `/navigate_to_pose` 首次检查 `Action servers: 0`，短暂复核后恢复为 `1`，server 为 `/bt_navigator`；goal accepted，最终 `SUCCEEDED` | `SUCCEEDED` | 原本无坐标业务点，本轮首次 candidate 首测真实通过；但总导航时间约 `66s`、出现 `5` 次 recoveries，建议后续微调坐标 |
| `buffer_1` | `2.4 / -3.8 / 0.0` | `future_extensions/wms_integration/config/waypoints.json` | 发送前 5 个关键 lifecycle 节点均为 `active [3]` | `map -> odom` 可用；采样平移约 `[0.012, 0.023, 0.000]`，偏航约 `0.095` 度 | `/navigate_to_pose` 发送前 `Action servers: 1`，goal accepted，结果 `SUCCEEDED` | `SUCCEEDED` | 真实 headless 补测通过；首条 `/cmd_vel` 为 `linear.x=0.01998`、`angular.z=-0.51845` |
| `staging_1` | `4.6 / -3.8 / 0.0` | `future_extensions/wms_integration/config/waypoints.json` | 独立 fresh session 中 `ros2 node list` 可见整套 Nav2 节点；`/map_server active [3]`、`/controller_server active [3]`、`/bt_navigator active [3]`，但 `ros2 lifecycle get /amcl` 与 `ros2 lifecycle get /planner_server` 仍返回 `Node not found` | `map -> odom` 可用；采样平移约 `[0.004, 0.023, 0.000]`，偏航约 `0.327` 度 | `ros2 action info /navigate_to_pose` 返回 `Action servers: 0`；`ros2 action list -t` 虽可见 `/navigate_to_pose` 条目，但不足以替代可用 server | `SKIPPED` | 已为该点单独开 fresh session 复测；但前置条件仍不满足，未强行发 goal |
| `inspection_point` | `5.0 / -1.2 / 3.14` | `future_extensions/wms_integration/config/waypoints.json` | 独立 fresh session 中 `ros2 node list` 可见整套 Nav2 节点；`/map_server`、`/amcl`、`/planner_server`、`/controller_server` 可查到 `active [3]`，但 `ros2 lifecycle get /bt_navigator` 两次复核都返回 `Node not found` | `map -> odom` 可用；采样平移约 `[0.005, 0.026, 0.000]`，偏航约 `0.475` 度 | `ros2 action info /navigate_to_pose` 返回 `Action servers: 1`、server 为 `/bt_navigator` | `SKIPPED` | 已为该点单独开 fresh session 复测；由于 lifecycle 未形成完整 `5/5 active`，即使 action server 可见也未强行发 goal |

## 9. 汇总指标

| 指标 | 数值 | 说明 |
| --- | --- | --- |
| 已固定 initial pose 点位数 | `1` | 当前仅 `start_zone` 作为主线 initial pose 入口 |
| 已命名 goal 点位数 | `5` | `station_a`、`station_b`、`shelf_1`、`shelf_2`，以及 historical candidate `candidate_dock_a` 已写入 `config/task_points.yaml` |
| 已写入可执行 goal 坐标数 | `5` | 其中 `station_a`、`station_b`、`shelf_1`、`shelf_2` 为 `docs/task_points_coordinate_plan.md` candidate coordinates；`candidate_dock_a` 为 historical candidate |
| 已记录运行轮次 | `12` | `RUN-01` 到 `RUN-12` 都已有真实记录 |
| 已真实发送 goal 轮次 | `5` | `RUN-02`、`RUN-03`、`RUN-05`、`RUN-06`、`RUN-12` 均真实发送了 goal |
| 成功到达轮次 | `5` | 五次真实 goal 均返回 `SUCCEEDED` |
| 首次 `/cmd_vel` 出现时间 | `TBD` | 已确认存在首条 `/cmd_vel`，但本轮未对所有 session 单独记录严格时延 |
| 生命周期全 active 轮次 | `5` | `RUN-02`、`RUN-03`、`RUN-05`、`RUN-06`、`RUN-12` 中 5 个关键 lifecycle 节点全部 `active [3]` |
| lifecycle 未全激活或无法完整确认轮次 | `7` | `RUN-01`、`RUN-04`、`RUN-07`、`RUN-08`、`RUN-09`、`RUN-10`、`RUN-11` 都未满足“全部 active”前提 |
| `map -> odom` 连通轮次 | `12` | `RUN-01` 到 `RUN-12` 均观察到了 `map -> odom`，其中部分轮次依赖初始位姿注入后恢复 |
| 本轮 candidate business point 成功点 | `1` | `shelf_2` 首次真实验证返回 `SUCCEEDED` |
| 本轮 candidate business point 跳过点 | `3` | `station_a`、`station_b`、`shelf_1` 均因前置条件不足真实 `SKIPPED` |
| 本轮目标集合剩余未测点 | `0` | `station_a`、`station_b`、`shelf_1`、`shelf_2` 都已完成独立 fresh session 尝试 |

## 10. 当前结论

- `docs/reports/test_report_2026_05_12.md` 继续作为 V2.1 baseline report 保留。
- 当前 V2.2 报告已经明确：主线已固定 `start_zone`、`station_a`、`station_b`、`shelf_1`、`shelf_2` 这些点位名称；其中 `station_a`、`station_b`、`shelf_1`、`shelf_2` 原本是无坐标业务点。
- 本轮未修改 `navigation.launch.py`、`config/nav2_params.yaml`、地图、world 或 robot model，只把 `docs/task_points_coordinate_plan.md` 中的 candidate coordinates 最小写入 `config/task_points.yaml`，并对这 4 个点分别开 fresh session 做首次真实验证。
- 这些结果都来自真实运行，但只代表 candidate coordinates 的首次验证结果，不代表最终仓库业务点位已经定版。
- 今日第 1 轮 headless 复测再次确认：如果没有在启动早期注入初始位姿，`planner_server` 会因缺少 `map` 侧变换而停在 `inactive [2]`；此时即使随后补发 `/initialpose`，`map -> odom` 可以恢复，但 `planner_server` 和 `bt_navigator` 不会自动补齐。
- 今日第 2 轮干净重启后，启动约 `12` 秒执行 `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone`，5 个关键 lifecycle 节点均进入 `active [3]`，`/navigate_to_pose` 有 `1` 个 server，`map -> odom` 稳定可用。
- 在上述前提下，围绕历史候选 `candidate_dock_a` 已累计获得 `3` 次真实 goal 成功：`RUN-02`、`RUN-03`、`RUN-05` 均捕获到了 `/cmd_vel`，且 `navigate_to_pose` 返回 `SUCCEEDED`。
- 同日续测中，历史候选 `buffer_1` 也完成了 1 次真实 headless goal 成功：`RUN-06` 在发送前 lifecycle 全 `active [3]`、`map -> odom` 可用、`/navigate_to_pose` 有 `1` 个 server，最终返回 `SUCCEEDED`。
- 但 `RUN-04` 说明 headless 启动链路仍存在波动：即使按“启动约 `12` 秒后注入 `start_zone`”执行，`map -> odom` 和 action server 已经可用，`planner_server`、`controller_server`、`bt_navigator` 仍可能停在 `inactive [2]`，因此这一轮必须如实记为“跳过”，不能伪装成失败或成功 goal。
- `RUN-09 station_b`：initial pose 已发布，`map -> odom` 可用，但 `/bt_navigator` lifecycle 两次复核都返回 `Node not found`，`/navigate_to_pose` 两次复核都为 `Action servers: 0`，因此按规则 `SKIPPED`。
- `RUN-10 station_a`：initial pose 已发布，`map -> odom` 可用，但 `/planner_server` 与 `/bt_navigator` lifecycle 查询返回 `Node not found`，`/navigate_to_pose` 为 `Action servers: 0`，因此按规则 `SKIPPED`。
- `RUN-11 shelf_1`：initial pose 已发布，`map -> odom` 可用，但 `/map_server` lifecycle 返回 `Node not found`，`/navigate_to_pose` 只有 client 没有 server，因此按规则 `SKIPPED`。
- `RUN-12 shelf_2`：initial pose、完整 lifecycle、`map -> odom` 最终都满足；`/navigate_to_pose` 在短暂复核后恢复为 `1` 个 server，goal accepted，最终 `SUCCEEDED`。
- `shelf_2` 虽然成功，但导航总时长约 `66s`，过程中出现 `5` 次 recoveries，说明这组 candidate coordinates 可用但仍建议后续小幅微调。
- 为了把“上一轮 `RUN-06` 后的状态抖动”与点位本身区分开，今天又为 `staging_1` 和 `inspection_point` 各自开了一轮独立 fresh session。
- `RUN-07` 中，`staging_1` 的会话里 `map -> odom` 已恢复，`ros2 node list` 也能看到整套 Nav2 节点，但 lifecycle CLI 仍未形成完整 `5/5 active`，同时 `ros2 action info /navigate_to_pose` 返回 `Action servers: 0`，因此按约束跳过。
- `RUN-08` 中，`inspection_point` 的会话里 `map -> odom` 稳定、`/navigate_to_pose` 也恢复到 `1` 个 server，但 `ros2 lifecycle get /bt_navigator` 连续两次都返回 `Node not found`；由于生命周期仍不完整，这一轮也必须如实记为“跳过”。
- 因此，到 2026-05-13 收工时，本轮目标集合 `station_a`、`station_b`、`shelf_1`、`shelf_2` 已全部完成“至少一次独立 fresh session 真实尝试”；其中 `shelf_2` 成功，`station_a`、`station_b`、`shelf_1` 因前置条件不满足被真实跳过，不存在伪造结果。

## 11. 下一步填报建议

1. 如果后续继续推进主线 business point，只调整 `config/task_points.yaml` 中的 candidate coordinates；保持 `navigation.launch.py`、`config/nav2_params.yaml`、地图、world、robot model 不变。
2. 对 `station_a`、`station_b`、`shelf_1`，下一轮先等 fresh session 中 lifecycle 完整 `5/5 active` 且 `/navigate_to_pose` 明确有 `1` 个 server，再决定是否发 goal；当前阻塞点首先是 bringup / action 可用性，而不是坐标优劣。
3. 对 `shelf_2`，建议后续做小幅坐标微调并复跑，因为它虽然 `SUCCEEDED`，但耗时偏长且 recoveries 较多。
4. 继续把“历史候选点补测”和“主线 station / shelf candidate 首测”分开记录，避免把 `future_extensions/` 点位与主线业务点位混写。

## 12. 本轮执行命令与结果汇总

本轮未新增独立日志文件；以下为本报告内汇总。

### 12.1 本轮执行命令

1. `ros2 daemon stop`
2. `ps -ef | rg 'navigation.launch.py|gazebo|gz sim|bt_navigator|planner_server|controller_server|amcl'`
3. `ros2 launch amr_warehouse_sim navigation.launch.py use_gz_gui:=false use_rviz:=false`
4. `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30`
5. `ros2 node list`
6. `ros2 lifecycle get /map_server`
7. `ros2 lifecycle get /amcl`
8. `ros2 lifecycle get /planner_server`
9. `ros2 lifecycle get /controller_server`
10. `ros2 lifecycle get /bt_navigator`
11. `timeout 4s ros2 run tf2_ros tf2_echo map odom`
12. `ros2 action info /navigate_to_pose`
13. `ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose ... --feedback`（仅 `shelf_2` 满足前置条件后实际执行）

### 12.2 成功点

- `shelf_2`：candidate coordinates 首次真实验证 `SUCCEEDED`；但导航约 `66s`、`5` 次 recoveries，建议后续微调坐标

### 12.3 失败点

- `无`

### 12.4 跳过点

- `station_b`：`map -> odom` 可用，但 `/bt_navigator` lifecycle 两次复核 `Node not found`，且 `/navigate_to_pose` 为 `Action servers: 0`
- `station_a`：`map -> odom` 可用，但 `/planner_server`、`/bt_navigator` lifecycle 查询不完整，且 `/navigate_to_pose` 为 `Action servers: 0`
- `shelf_1`：`map -> odom` 可用，但 `/map_server` lifecycle 返回 `Node not found`，且 `/navigate_to_pose` 为 `Action servers: 0`

### 12.5 剩余未测点

- 本轮目标集合 `station_a`、`station_b`、`shelf_1`、`shelf_2`：`无`
- 仍待后续拿到成功 goal 结果的主线 candidate business points：`station_a`、`station_b`、`shelf_1`

### 12.6 是否建议后续微调坐标

- `shelf_2`：`建议`。已真实 `SUCCEEDED`，但耗时偏长且 recoveries 偏多。
- `station_a`、`station_b`、`shelf_1`：`暂不以调坐标为首要动作`。当前更大的阻塞是 lifecycle / action server 前置条件未稳定满足。

## 13. WMS 接入准备补测

同日后续補測詳見 [docs/wms/reports/wms_task_points_readiness_report_2026_05_13.md](../wms/reports/wms_task_points_readiness_report_2026_05_13.md)。

本次补测使用更长的 lifecycle 确认窗口，并坚持 fresh session + `start_zone` 初始位姿 + 完整前置条件后才发送 goal。`station_a`、`station_b`、`shelf_1`、`shelf_2` 均已拿到至少一次真实 `SUCCEEDED`，并完成 Mock WMS pending task 创建验证。

补测中仍观察到真实波动：`station_b` 有一次因前置条件不足 `SKIPPED`，`shelf_1` 和 `shelf_2` 各有一次在完整前置条件下返回 `ABORTED`。因此这些点当前可用于 Mock WMS 数据层和后续 task executor 接入实验，但仍应标记为 candidate coordinates，不声明最终业务点位已定版。
