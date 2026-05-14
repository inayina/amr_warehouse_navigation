# Fixed Task Points

## 1. Purpose

本文件说明当前主线固定任务点入口及其最新状态。

- 主线配置文件：`config/task_points.yaml`
- 当前阶段：`V2.2 固定任务点与重复导航验证`
- 目标：为重复导航验证和最小 Mock WMS 数据层提供统一的 `map` frame 输入
- 边界：当前只维护点位配置、验证记录和数据层消费边界，不把任务执行器或 `/cmd_vel` 控制接回主线

## 2. Coordinate Frame And Roles

所有主线点位统一使用：

- `frame_id: map`

当前角色划分：

- `start_zone`
  只作为主线 initial pose 入口，对齐 `publish_initial_pose --preset start_zone`
- `station_a`、`station_b`、`shelf_1`、`shelf_2`
  当前主线 candidate business points
- `candidate_dock_a`
  历史候选点，保留在主线配置中继续作为补充验证输入

当前约束：

- 不在 `odom` 或 `base_link` 下保存任务点
- initial pose 和 navigation goal 都以 `map` frame 为准
- `start_zone` 不作为当前 Mock WMS 任务目标

## 3. Current Mainline Points

截至 `2026-05-13`，`config/task_points.yaml` 中的主线点位如下。

| Name | Frame | X | Y | Yaw | Current Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `start_zone` | `map` | `0.0` | `0.0` | `0.0` | `confirmed initial pose` | 当前唯一主线 initial pose preset |
| `station_a` | `map` | `-5.3` | `-5.8` | `3.14` | `candidate business point` | 来自 `docs/task_points_coordinate_plan.md` |
| `station_b` | `map` | `5.0` | `-4.8` | `0.0` | `candidate business point` | 来自 `docs/task_points_coordinate_plan.md` |
| `shelf_1` | `map` | `-2.75` | `2.5` | `0.0` | `candidate business point` | 来自 `docs/task_points_coordinate_plan.md` |
| `shelf_2` | `map` | `2.75` | `2.5` | `3.14` | `candidate business point` | 来自 `docs/task_points_coordinate_plan.md` |
| `candidate_dock_a` | `map` | `0.0` | `-3.8` | `-1.57` | `historical candidate` | 来源于 `future_extensions/wms_integration/config/waypoints.json` |

补充说明：

- `station_a`、`station_b`、`shelf_1`、`shelf_2` 已不是 `TBD`，但仍应标记为 candidate coordinates
- 这些坐标已经进入主线配置，不代表它们已经达到长期稳定或最终业务定版

## 4. Validation Status

当前与这些点位直接相关的真实记录如下：

- [docs/reports/repeat_navigation_test_report_2026_05_13.md](./reports/repeat_navigation_test_report_2026_05_13.md)
  记录了 V2.2 阶段的 fixed-goal 尝试、`SUCCEEDED / SKIPPED` 结果和 startup 条件
- [docs/logs/nav2_startup_stability_notes.md](./logs/nav2_startup_stability_notes.md)
  单独整理了 fresh-session 下 lifecycle / action readiness 的波动现象
- [docs/logs/nav2_startup_stability_log_2026_05_13.md](./logs/nav2_startup_stability_log_2026_05_13.md)
  记录了诊断轮次、READY / NOT_READY 和 diagnostic goal probe 结果
- [docs/wms/reports/wms_task_points_readiness_report_2026_05_13.md](./wms/reports/wms_task_points_readiness_report_2026_05_13.md)
  记录了四个 business points 至少一次真实 `SUCCEEDED` 的 WMS readiness 复测

截至 `2026-05-13` 的点位验证结论可简化为：

| Point | Real Navigation Evidence | Current Interpretation |
| --- | --- | --- |
| `start_zone` | 多轮 successful initial pose injection | 主线 initial pose 入口已固定 |
| `station_a` | 至少 1 次真实 `SUCCEEDED` | 可进入 Mock WMS 数据层，但仍是 candidate coordinate |
| `station_b` | 至少 1 次真实 `SUCCEEDED`，也出现过 `SKIPPED` | 可进入 Mock WMS 数据层，但 startup stability 仍需继续观察 |
| `shelf_1` | 至少 1 次真实 `SUCCEEDED`，也出现过 `ABORTED` | 可进入 Mock WMS 数据层，但不应宣称长期稳定 |
| `shelf_2` | 至少 2 次真实 `SUCCEEDED`，也出现过 `ABORTED` | 当前证据最强的 business point 之一，但仍建议继续复跑 |
| `candidate_dock_a` | 多次真实 `SUCCEEDED` | 适合作为补充验证点，不等同于最终业务点 |

## 5. How To Update Coordinates

如果后续要微调坐标，推荐继续用最小改动方式处理：

1. 启动主线导航：
   `ros2 launch amr_warehouse_sim navigation.launch.py`
2. 确认 `/map`、`/scan_filtered`、`odom -> base_link` 正常。
3. 注入初始位姿：
   `ros2 run amr_warehouse_sim publish_initial_pose --preset start_zone --wait-for-subscribers 30`
4. 在另一个终端监听：
   `ros2 topic echo /goal_pose --once`
5. 在 RViz 中用 `Nav2 Goal` 点击一个新的候选位置。
6. 从 `/goal_pose` 抄录 `frame_id`、`x`、`y`，并根据朝向回填 `yaw`。
7. 只修改 `config/task_points.yaml` 对应点位，并把真实结果写回新的日期化测试报告。

当前不建议：

- 同时改 `navigation.launch.py`、`config/nav2_params.yaml`、地图和任务点坐标
- 把 `future_extensions/` 的旧 waypoint 文件重新接回主线作为直接入口

## 6. Relationship With Repeat Navigation

当前 V2.2 阶段这些点位的用途固定为：

- `start_zone`
  作为统一 initial pose 入口
- `station_a`、`station_b`、`shelf_1`、`shelf_2`
  作为主线固定 goal 候选
- `candidate_dock_a`
  作为补充验证 / 过渡候选点

记录方式：

- 模板：`docs/templates/repeat_navigation_test_report.md`
- 当前主线真实报告：`docs/reports/repeat_navigation_test_report_2026_05_13.md`

当前建议：

- 继续把 `SUCCEEDED`、`ABORTED`、`SKIPPED` 都如实保留
- 不要把“已经写入配置”直接等同于“长期稳定可用”
- 不要把 historical candidate 与主线 business points 混写成同一类结论

## 7. Relationship With Mock WMS

当前最小 Mock WMS 的边界如下：

- 只消费 `config/task_points.yaml`
- 只创建和读取 pending task
- 只保存 `map` frame goal 和任务状态
- 不直接驱动 Nav2
- 不直接控制 `/cmd_vel`

当前已经允许进入数据层的主线目标：

- `candidate_dock_a` / `dock_a`
- `station_a`
- `station_b`
- `shelf_1`
- `shelf_2`

当前仍然不进入数据层的点位：

- `start_zone`

对应设计说明见 [docs/designs/mock_wms_design.md](./designs/mock_wms_design.md)。
